from __future__ import annotations

import asyncio
import base64
import io
import os
import re
import wave
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Literal
from uuid import uuid4

import edge_tts
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

try:
    from tencentcloud.common import credential
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.tts.v20190823 import models, tts_client

    TENCENT_SDK_IMPORT_ERROR: Exception | None = None
except ImportError as exc:  # pragma: no cover
    credential = None
    TencentCloudSDKException = Exception
    ClientProfile = None
    models = None
    tts_client = None
    TENCENT_SDK_IMPORT_ERROR = exc


PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)
SCRIPT_LINE_RE = re.compile(r"^\s*([^:：]{1,32})\s*[:：]\s*(.+?)\s*$")
SUPPORTED_ENGINES = {"edge", "tencent"}
SUPPORTED_TENCENT_VOICE_MODES = {"female", "male", "duet"}


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_env_files() -> None:
    if load_dotenv is None:
        return

    candidates = (
        Path.cwd() / ".env",
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    )
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen or not resolved.exists():
            continue
        load_dotenv(resolved, override=False)
        seen.add(resolved)


def _clear_proxy_env() -> None:
    # Optional isolation mode. Disabled by default so edge-tts can use the
    # user's normal proxy environment when needed.
    for key in PROXY_ENV_KEYS:
        os.environ.pop(key, None)


def _apply_proxy_overrides() -> None:
    http_proxy = os.getenv("TTS_HTTP_PROXY", "").strip()
    https_proxy = os.getenv("TTS_HTTPS_PROXY", "").strip()
    all_proxy = os.getenv("TTS_ALL_PROXY", "").strip()

    if http_proxy:
        os.environ["HTTP_PROXY"] = http_proxy
        os.environ["http_proxy"] = http_proxy
    if https_proxy:
        os.environ["HTTPS_PROXY"] = https_proxy
        os.environ["https_proxy"] = https_proxy
    if all_proxy:
        os.environ["ALL_PROXY"] = all_proxy
        os.environ["all_proxy"] = all_proxy


_load_env_files()
TTS_DISABLE_PROXY = _env_flag("TTS_DISABLE_PROXY", False)
if TTS_DISABLE_PROXY:
    _clear_proxy_env()
else:
    _apply_proxy_overrides()

EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "zh-CN-XiaoxiaoNeural")
TTS_OUTPUT_DIR = Path(os.getenv("TTS_OUTPUT_DIR", "./data/outputs")).resolve()
TTS_MAX_CONCURRENT_JOBS = max(int(os.getenv("TTS_MAX_CONCURRENT_JOBS", "1")), 1)
TTS_MIN_WAV_DURATION_SECONDS = float(os.getenv("TTS_MIN_WAV_DURATION_SECONDS", "0.5"))

PODCAST_HOST_A_NAME = os.getenv("PODCAST_HOST_A_NAME", "主持人A").strip() or "主持人A"
PODCAST_HOST_B_NAME = os.getenv("PODCAST_HOST_B_NAME", "主持人B").strip() or "主持人B"
TENCENT_PODCAST_APP_ID = os.getenv("TENCENT_PODCAST_APP_ID", "").strip()
TENCENT_PODCAST_SECRET_ID = os.getenv("TENCENT_PODCAST_SECRET_ID", "").strip()
TENCENT_PODCAST_SECRET_KEY = os.getenv("TENCENT_PODCAST_SECRET_KEY", "").strip()
TENCENT_PODCAST_VOICE_A = int(os.getenv("TENCENT_PODCAST_VOICE_A", "602005") or "602005")
TENCENT_PODCAST_VOICE_B = int(os.getenv("TENCENT_PODCAST_VOICE_B", "602004") or "602004")
TENCENT_PODCAST_SAMPLE_RATE = int(os.getenv("TENCENT_PODCAST_SAMPLE_RATE", "24000") or "24000")
TENCENT_PODCAST_SPEED = float(os.getenv("TENCENT_PODCAST_SPEED", "1.05") or "1.05")
TENCENT_PODCAST_SPEED_A = float(os.getenv("TENCENT_PODCAST_SPEED_A", str(TENCENT_PODCAST_SPEED)) or TENCENT_PODCAST_SPEED)
TENCENT_PODCAST_SPEED_B = float(os.getenv("TENCENT_PODCAST_SPEED_B", str(TENCENT_PODCAST_SPEED)) or TENCENT_PODCAST_SPEED)
TENCENT_PODCAST_VOLUME = float(os.getenv("TENCENT_PODCAST_VOLUME", "0") or "0")
TENCENT_PODCAST_VERIFY_SSL = _env_flag("TENCENT_PODCAST_VERIFY_SSL", True)
TENCENT_PODCAST_EMOTION_CATEGORY = os.getenv("TENCENT_PODCAST_EMOTION_CATEGORY", "story").strip() or "story"
TENCENT_PODCAST_EMOTION_INTENSITY = int(os.getenv("TENCENT_PODCAST_EMOTION_INTENSITY", "120") or "120")

TTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="FocusLedger TTS Worker", version="0.5.0")

executor = ThreadPoolExecutor(max_workers=TTS_MAX_CONCURRENT_JOBS, thread_name_prefix="tts-job")
jobs_lock = Lock()
job_futures: dict[str, Future] = {}
jobs: dict[str, "JobState"] = {}


class SynthesizeRequest(BaseModel):
    text: str
    format: str = Field(default="mp3")
    filename_prefix: str = Field(default="podcast")
    engine: Literal["edge", "tencent"] = Field(default="edge")
    voice: str | None = None
    voice_mode: Literal["female", "male", "duet"] | None = None
    rate: str = Field(default="-8%")
    extra_payload: dict[str, object] = Field(default_factory=dict)
    # kept for compatibility but ignored
    chunk_length: int | None = None
    reference_id: str | None = None


class SynthesizeResponse(BaseModel):
    output_path: str
    content_type: str | None = None
    bytes_written: int


class SynthesizeJobCreateResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"]


class JobState(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    created_at: str
    updated_at: str
    request: SynthesizeRequest
    output_path: str | None = None
    content_type: str | None = None
    bytes_written: int | None = None
    error: str | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_prefix(value: str) -> str:
    cleaned = "".join(ch for ch in value.strip() if ch.isalnum() or ch in {"-", "_"})
    return cleaned or "podcast"


def _get_wav_duration_seconds(content: bytes) -> float:
    with wave.open(io.BytesIO(content), "rb") as wav_file:
        return wav_file.getnframes() / max(wav_file.getframerate(), 1)


def _write_output(content: bytes, *, prefix: str, extension: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{_sanitize_prefix(prefix)}-{timestamp}-{uuid4().hex[:8]}{extension}"
    output_path = TTS_OUTPUT_DIR / filename
    output_path.write_bytes(content)
    return output_path


def _chunk_text(text: str, limit: int = 120) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    sentences = [part.strip() for part in re.split(r"(?<=[。！？!?；;])", normalized) if part.strip()]
    chunks: list[str] = []
    current = ""

    for sentence in sentences or [normalized]:
        parts = [sentence]
        if len(sentence) > limit:
            parts = [piece.strip() for piece in re.split(r"(?<=[，,])", sentence) if piece.strip()]
        for part in parts:
            candidate = f"{current}{part}"
            if current and len(candidate) > limit:
                chunks.append(current)
                current = part
            else:
                current = candidate

    if current:
        chunks.append(current)
    return chunks


def _append_wav(base_audio: bytes, addition: bytes) -> bytes:
    if not base_audio:
        return addition

    output = io.BytesIO()
    with wave.open(io.BytesIO(base_audio), "rb") as base_wav, wave.open(io.BytesIO(addition), "rb") as add_wav:
        if (
            base_wav.getnchannels() != add_wav.getnchannels()
            or base_wav.getsampwidth() != add_wav.getsampwidth()
            or base_wav.getframerate() != add_wav.getframerate()
        ):
            raise RuntimeError("Tencent TTS returned audio with mismatched wav params")

        with wave.open(output, "wb") as merged:
            merged.setnchannels(base_wav.getnchannels())
            merged.setsampwidth(base_wav.getsampwidth())
            merged.setframerate(base_wav.getframerate())
            merged.writeframes(base_wav.readframes(base_wav.getnframes()))
            merged.writeframes(add_wav.readframes(add_wav.getnframes()))

    return output.getvalue()


def _build_silence_wav(*, sample_rate: int, duration_ms: int) -> bytes:
    frame_count = max(1, int(sample_rate * duration_ms / 1000))
    silence = b"\x00\x00" * frame_count
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(silence)
    return output.getvalue()


def _iter_script_lines(script_text: str) -> list[tuple[str | None, str]]:
    entries: list[tuple[str | None, str]] = []
    for line in script_text.splitlines():
        raw = line.strip()
        if not raw:
            continue
        match = SCRIPT_LINE_RE.match(raw)
        if match:
            entries.append((match.group(1).strip(), match.group(2).strip()))
        else:
            entries.append((None, raw))
    return entries


def _parse_single_voice_segments(script_text: str, *, speaker: str) -> list[dict[str, object]]:
    parts = [text for _, text in _iter_script_lines(script_text) if text]
    flattened = " ".join(parts).strip()
    if not flattened:
        return []
    return [
        {
            "speaker": speaker,
            "speaker_name": speaker,
            "text": flattened,
            "pause_ms": 420,
        }
    ]


def _parse_duet_segments(script_text: str) -> list[dict[str, object]]:
    segments: list[dict[str, object]] = []
    unknown_speakers: dict[str, str] = {}
    fallback_order = ["A", "B"]

    for speaker_name, text in _iter_script_lines(script_text):
        if not text:
            continue

        speaker = "A"
        if speaker_name:
            normalized_name = speaker_name.strip().casefold()
            if normalized_name in {"a", PODCAST_HOST_A_NAME.casefold()}:
                speaker = "A"
            elif normalized_name in {"b", PODCAST_HOST_B_NAME.casefold()}:
                speaker = "B"
            else:
                speaker = unknown_speakers.setdefault(
                    normalized_name,
                    fallback_order[min(len(unknown_speakers), len(fallback_order) - 1)],
                )

        segments.append(
            {
                "speaker": speaker,
                "speaker_name": speaker_name or speaker,
                "text": text,
                "pause_ms": 380 if speaker == "A" else 460,
            }
        )

    return segments


async def _synthesize_with_edge_tts(text: str, voice: str, rate: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    mp3_buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_buffer.write(chunk["data"])
    audio_bytes = mp3_buffer.getvalue()
    if not audio_bytes:
        raise RuntimeError("edge-tts returned empty audio; check the text input")
    return audio_bytes


def _build_tencent_client() -> "tts_client.TtsClient":
    if TENCENT_SDK_IMPORT_ERROR is not None or credential is None or ClientProfile is None or tts_client is None:
        raise RuntimeError(f"Tencent SDK is not installed: {TENCENT_SDK_IMPORT_ERROR}")
    if not TENCENT_PODCAST_APP_ID or not TENCENT_PODCAST_SECRET_ID or not TENCENT_PODCAST_SECRET_KEY:
        raise RuntimeError(
            "Tencent TTS credentials are missing. Please configure "
            "TENCENT_PODCAST_APP_ID / TENCENT_PODCAST_SECRET_ID / TENCENT_PODCAST_SECRET_KEY."
        )

    cred = credential.Credential(TENCENT_PODCAST_SECRET_ID, TENCENT_PODCAST_SECRET_KEY)
    profile = ClientProfile()
    profile.httpProfile.certification = None if TENCENT_PODCAST_VERIFY_SSL else False
    return tts_client.TtsClient(cred, "", profile)


def _synthesize_tencent_chunk(
    client: "tts_client.TtsClient",
    *,
    text: str,
    voice_type: int,
    speed: float,
) -> tuple[bytes, str]:
    if models is None:
        raise RuntimeError("Tencent SDK models are unavailable")

    req = models.TextToVoiceRequest()
    req.Text = text
    req.SessionId = uuid4().hex
    req.VoiceType = voice_type
    req.Codec = "wav"
    req.SampleRate = TENCENT_PODCAST_SAMPLE_RATE
    req.Speed = speed
    req.Volume = TENCENT_PODCAST_VOLUME
    req.EmotionCategory = TENCENT_PODCAST_EMOTION_CATEGORY
    req.EmotionIntensity = TENCENT_PODCAST_EMOTION_INTENSITY

    try:
        resp = client.TextToVoice(req)
    except TencentCloudSDKException as exc:  # pragma: no cover
        raise RuntimeError(str(exc)) from exc

    try:
        audio_bytes = base64.b64decode(resp.Audio)
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Tencent TTS returned an unreadable audio payload") from exc

    return audio_bytes, resp.RequestId


def _synthesize_with_tencent_tts(text: str, voice_mode: str) -> bytes:
    normalized_mode = (voice_mode or "duet").strip().lower()
    if normalized_mode not in SUPPORTED_TENCENT_VOICE_MODES:
        raise RuntimeError(f"unsupported Tencent voice mode: {voice_mode}")

    if normalized_mode == "duet":
        segments = _parse_duet_segments(text)
    else:
        segments = _parse_single_voice_segments(
            text,
            speaker="A" if normalized_mode == "female" else "B",
        )

    if not segments:
        raise RuntimeError("podcast script is empty, cannot synthesize audio")

    client = _build_tencent_client()
    merged_audio = b""

    for segment in segments:
        speaker = str(segment["speaker"])
        voice_type = TENCENT_PODCAST_VOICE_A if speaker == "A" else TENCENT_PODCAST_VOICE_B
        speed = TENCENT_PODCAST_SPEED_A if speaker == "A" else TENCENT_PODCAST_SPEED_B
        for chunk in _chunk_text(str(segment["text"])):
            chunk_audio, _request_id = _synthesize_tencent_chunk(
                client,
                text=chunk,
                voice_type=voice_type,
                speed=speed,
            )
            merged_audio = _append_wav(merged_audio, chunk_audio)

        pause_ms = max(0, int(segment.get("pause_ms") or 0))
        if pause_ms:
            merged_audio = _append_wav(
                merged_audio,
                _build_silence_wav(sample_rate=TENCENT_PODCAST_SAMPLE_RATE, duration_ms=pause_ms),
            )

    if not merged_audio:
        raise RuntimeError("Tencent TTS did not return usable audio")

    if _get_wav_duration_seconds(merged_audio) < TTS_MIN_WAV_DURATION_SECONDS:
        raise RuntimeError("Tencent TTS returned audio that is unexpectedly short")

    return merged_audio


def _run_synthesis(payload: SynthesizeRequest) -> SynthesizeResponse:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    engine = (payload.engine or "edge").strip().lower()
    if engine not in SUPPORTED_ENGINES:
        raise HTTPException(status_code=400, detail=f"unsupported tts engine: {payload.engine}")

    if engine == "edge":
        voice = payload.voice or EDGE_TTS_VOICE
        rate = payload.rate or "-8%"
        try:
            audio_bytes = asyncio.run(_synthesize_with_edge_tts(text, voice, rate))
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"edge-tts synthesis failed: {exc}") from exc

        output_path = _write_output(audio_bytes, prefix=payload.filename_prefix, extension=".mp3")
        return SynthesizeResponse(
            output_path=str(output_path),
            content_type="audio/mpeg",
            bytes_written=output_path.stat().st_size,
        )

    voice_mode = payload.voice_mode or (payload.voice if payload.voice in SUPPORTED_TENCENT_VOICE_MODES else None) or "duet"
    tencent_text = str(payload.extra_payload.get("dialogue_text") or text).strip()
    try:
        audio_bytes = _synthesize_with_tencent_tts(tencent_text, voice_mode)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"tencent-tts synthesis failed: {exc}") from exc

    output_path = _write_output(audio_bytes, prefix=payload.filename_prefix, extension=".wav")
    return SynthesizeResponse(
        output_path=str(output_path),
        content_type="audio/wav",
        bytes_written=output_path.stat().st_size,
    )


def _update_job(job_id: str, **fields: object) -> None:
    with jobs_lock:
        job = jobs[job_id]
        jobs[job_id] = job.model_copy(
            update={
                **fields,
                "updated_at": _utc_now_iso(),
            }
        )


def _job_runner(job_id: str, payload: SynthesizeRequest) -> None:
    _update_job(job_id, status="running", error=None)
    try:
        result = _run_synthesis(payload)
    except HTTPException as exc:
        _update_job(job_id, status="failed", error=str(exc.detail))
        raise
    except Exception as exc:  # noqa: BLE001
        _update_job(job_id, status="failed", error=str(exc))
        raise
    else:
        _update_job(
            job_id,
            status="succeeded",
            output_path=result.output_path,
            content_type=result.content_type,
            bytes_written=result.bytes_written,
            error=None,
        )


@app.get("/health")
def health() -> dict[str, object]:
    with jobs_lock:
        queued = sum(1 for job in jobs.values() if job.status == "queued")
        running = sum(1 for job in jobs.values() if job.status == "running")
    return {
        "status": "ok",
        "tts_engines": sorted(SUPPORTED_ENGINES),
        "edge_default_voice": EDGE_TTS_VOICE,
        "tencent_configured": bool(
            TENCENT_PODCAST_APP_ID and TENCENT_PODCAST_SECRET_ID and TENCENT_PODCAST_SECRET_KEY
        ),
        "tencent_sdk_available": TENCENT_SDK_IMPORT_ERROR is None,
        "tencent_verify_ssl": TENCENT_PODCAST_VERIFY_SSL,
        "tts_disable_proxy": TTS_DISABLE_PROXY,
        "http_proxy": os.getenv("HTTP_PROXY") or os.getenv("http_proxy"),
        "https_proxy": os.getenv("HTTPS_PROXY") or os.getenv("https_proxy"),
        "output_dir": str(TTS_OUTPUT_DIR),
        "queued_jobs": queued,
        "running_jobs": running,
    }


@app.post("/synthesize", response_model=SynthesizeResponse)
def synthesize(payload: SynthesizeRequest) -> SynthesizeResponse:
    return _run_synthesis(payload)


@app.post("/jobs", response_model=SynthesizeJobCreateResponse)
def create_job(payload: SynthesizeRequest) -> SynthesizeJobCreateResponse:
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    job_id = uuid4().hex
    now = _utc_now_iso()
    with jobs_lock:
        jobs[job_id] = JobState(
            job_id=job_id,
            status="queued",
            created_at=now,
            updated_at=now,
            request=payload,
        )
        job_futures[job_id] = executor.submit(_job_runner, job_id, payload)
    return SynthesizeJobCreateResponse(job_id=job_id, status="queued")


@app.get("/jobs", response_model=list[JobState])
def list_jobs() -> list[JobState]:
    with jobs_lock:
        return sorted(jobs.values(), key=lambda item: item.created_at, reverse=True)


@app.get("/jobs/{job_id}", response_model=JobState)
def get_job(job_id: str) -> JobState:
    with jobs_lock:
        job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job
