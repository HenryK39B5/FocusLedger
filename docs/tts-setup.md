# TTS Worker Setup (edge-tts)

## Goal

This stack provides TTS (text-to-speech) for FocusLedger's podcast audio feature:

- FocusLedger generates podcast scripts
- `tts-worker` turns scripts into TTS jobs
- edge-tts (Microsoft Neural TTS) provides the audio synthesis
- Audio files (MP3) are written to `data/audio/`

FocusLedger does not call edge-tts directly. The worker layer is the integration boundary.

## Requirements

- Python (Anaconda): `D:\anaconda3\python.exe`
- `edge-tts` package: `pip install edge-tts -i https://pypi.tuna.tsinghua.edu.cn/simple`

The TTS worker is started manually when needed.

## Manual Start / Stop

```powershell
# Start
powershell -ExecutionPolicy Bypass -File .\scripts\tts-start.ps1

# Stop
powershell -ExecutionPolicy Bypass -File .\scripts\tts-stop.ps1
```

## Health Check

```
http://localhost:8010/health
```

## Worker Endpoints

- `GET /health`
- `POST /synthesize`
- `POST /jobs`
- `GET /jobs`
- `GET /jobs/{job_id}`

## Voice Configuration

Default voice: `zh-CN-XiaoxiaoNeural` (Mandarin Chinese, female)

Other good Chinese voices:
- `zh-CN-YunyangNeural` (male, news style)
- `zh-CN-YunxiNeural` (male, natural)

## Output

Audio files are saved as MP3 to `data/audio/`.
