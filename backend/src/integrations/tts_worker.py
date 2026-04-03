from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from src.core.config import Settings


class TTSWorkerError(RuntimeError):
    pass


class TTSWorkerClient:
    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.tts_worker_base_url.rstrip("/")
        self.timeout = settings.tts_worker_timeout_seconds
        self.audio_output_path = Path(settings.tts_audio_output_path).resolve()

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout, trust_env=False)

    def create_job(
        self,
        *,
        text: str,
        filename_prefix: str,
        format: str = "mp3",
        voice: str | None = None,
        rate: str = "-8%",
        extra_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "text": text,
            "format": format,
            "filename_prefix": filename_prefix,
            "rate": rate,
            "extra_payload": extra_payload or {},
        }
        if voice:
            payload["voice"] = voice
        try:
            with self._client() as client:
                response = client.post(f"{self.base_url}/jobs", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TTSWorkerError(f"tts worker create job failed: {exc}") from exc
        data = response.json()
        if not isinstance(data, dict) or not data.get("job_id"):
            raise TTSWorkerError("tts worker returned an invalid create-job response")
        return data

    def get_job(self, job_id: str) -> dict[str, Any]:
        try:
            with self._client() as client:
                response = client.get(f"{self.base_url}/jobs/{job_id}")
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TTSWorkerError(f"tts worker get job failed: {exc}") from exc
        data = response.json()
        if not isinstance(data, dict) or not data.get("job_id"):
            raise TTSWorkerError("tts worker returned an invalid job response")
        return data

    def resolve_output_path(self, worker_output_path: str | None) -> str | None:
        if not worker_output_path:
            return None
        filename = Path(worker_output_path).name
        return str((self.audio_output_path / filename).resolve())
