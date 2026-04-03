from __future__ import annotations

import asyncio
import io
import os
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


PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)


def _clear_proxy_env() -> None:
    # edge-tts uses aiohttp with trust_env=True upstream, so isolate this worker
    # from any ambient proxy variables inherited from the shell or editor.
    for key in PROXY_ENV_KEYS:
        os.environ.pop(key, None)


_clear_proxy_env()

EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "zh-CN-XiaoxiaoNeural")
TTS_OUTPUT_DIR = Path(os.getenv("TTS_OUTPUT_DIR", "./data/outputs")).resolve()
TTS_MAX_CONCURRENT_JOBS = max(int(os.getenv("TTS_MAX_CONCURRENT_JOBS", "1")), 1)
TTS_MIN_WAV_DURATION_SECONDS = float(os.getenv("TTS_MIN_WAV_DURATION_SECONDS", "0.5"))

TTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="FocusLedger TTS Worker", version="0.4.0")

executor = ThreadPoolExecutor(max_workers=TTS_MAX_CONCURRENT_JOBS, thread_name_prefix="tts-job")
jobs_lock = Lock()
job_futures: dict[str, Future] = {}
jobs: dict[str, "JobState"] = {}


class SynthesizeRequest(BaseModel):
    text: str
    format: str = Field(default="mp3")
    filename_prefix: str = Field(default="podcast")
    voice: str | None = None
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


async def _synthesize_with_edge_tts(text: str, voice: str, rate: str) -> bytes:
    """Call edge-tts and return MP3 bytes."""
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    mp3_buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_buffer.write(chunk["data"])
    audio_bytes = mp3_buffer.getvalue()
    if not audio_bytes:
        raise RuntimeError("edge-tts returned empty audio; check the text input")
    return audio_bytes


def _run_synthesis(payload: SynthesizeRequest) -> SynthesizeResponse:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    voice = payload.voice or EDGE_TTS_VOICE
    rate = payload.rate or "-8%"

    try:
        audio_bytes = asyncio.run(_synthesize_with_edge_tts(text, voice, rate))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"edge-tts synthesis failed: {exc}") from exc

    # edge-tts always outputs MP3
    output_path = _write_output(audio_bytes, prefix=payload.filename_prefix, extension=".mp3")
    return SynthesizeResponse(
        output_path=str(output_path),
        content_type="audio/mpeg",
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
        "tts_engine": "edge-tts",
        "voice": EDGE_TTS_VOICE,
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
