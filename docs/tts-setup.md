# TTS Worker Setup

## Goal

This stack provides TTS for FocusLedger's podcast audio feature:

- FocusLedger generates podcast scripts
- `tts-worker` turns scripts into TTS jobs
- edge-tts or Tencent TTS performs synthesis
- Audio files are written to `data/audio/`

FocusLedger does not call TTS providers directly. The worker layer is the integration boundary.

## Python Environment

The project standard is:

- `backend\.venv\Scripts\python.exe`

Do not mix this worker with:

- `D:\anaconda3\python.exe`
- another global `python`

## Install Worker Dependencies

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r .\tools\tts-worker\requirements.txt
```

## Manual Start / Stop

```powershell
# Start
powershell -ExecutionPolicy Bypass -File .\scripts\tts-start.ps1

# Stop
powershell -ExecutionPolicy Bypass -File .\scripts\tts-stop.ps1
```

## Health Check

```text
http://localhost:8010/health
```

## Worker Endpoints

- `GET /health`
- `POST /jobs`
- `GET /jobs`
- `GET /jobs/{job_id}`

## Voice Configuration

Default Edge voice:

- `zh-CN-XiaoxiaoNeural`

Other common Edge voices:

- `zh-CN-YunyangNeural`
- `zh-CN-YunxiNeural`

Tencent TTS requires:

- `TENCENT_PODCAST_APP_ID`
- `TENCENT_PODCAST_SECRET_ID`
- `TENCENT_PODCAST_SECRET_KEY`

## Proxy Notes

If your environment requires Clash or another local proxy for Edge TTS, configure:

```env
TTS_DISABLE_PROXY=false
TTS_HTTP_PROXY=http://127.0.0.1:7890
TTS_HTTPS_PROXY=http://127.0.0.1:7890
```

If you explicitly want the worker to ignore proxy variables:

```env
TTS_DISABLE_PROXY=true
```
