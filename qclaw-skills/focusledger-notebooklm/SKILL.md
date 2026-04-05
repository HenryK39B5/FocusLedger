---
name: focusledger-notebooklm
description: Generate a FocusLedger daily podcast for a specific date, then upload the final audio through QClaw cloud delivery so the user can open it from WeChat/QClaw. Use when the user asks for 播客、音频、日报播客、生成某天播客、把播客发给我、发到微信、发到手机、附件发送. Do not use for daily report generation alone or source syncing.
---

# FocusLedger Daily Podcast Delivery

Reuse the FocusLedger backend + TTS worker pipeline that already works in the web UI, then upload the final audio with QClaw's built-in `cloud-upload-backup` flow.

Return only the script stdout. Do not expose notebook IDs, retries, API details, or local debug output.

## Preconditions

- FocusLedger backend is running on `http://127.0.0.1:8100`
- The requested date already has synced articles in FocusLedger
- QClaw desktop is running so `cloud-upload-backup` can use the local proxy

## Workflow

1. Extract the target date from the user request.
2. If the user explicitly mentions a source group, pass it through `--group`.
3. Run the script with delivery enabled:

```powershell
$env:FOCUSLEDGER_BASE_URL = "http://127.0.0.1:8100"
python E:\QClaw\QClaw\resources\openclaw\config\skills\focusledger-notebooklm\scripts\generate_focusledger_audio_asset.py --date "2026-04-02" --deliver
```

With source group:

```powershell
$env:FOCUSLEDGER_BASE_URL = "http://127.0.0.1:8100"
python E:\QClaw\QClaw\resources\openclaw\config\skills\focusledger-notebooklm\scripts\generate_focusledger_audio_asset.py --date "2026-04-02" --group "投研/券商/中金" --deliver
```

4. Return the script stdout directly to the user.

## Date Handling

Accept these date forms:

- `2026-04-02`
- `2026/04/02`
- `2026年4月2日`
- `4月2日`
- `今天`
- `昨天`
- `前天`

If the request does not contain a date, ask the user to specify one.

## Rules

- Do not announce that you found this skill.
- Do not say you are reading `SKILL.md`.
- Do not narrate retries, encoding fixes, API discovery, or debugging steps.
- Do not send progress updates.
- Send a single final reply.
- Do not fabricate file links or audio paths.
- If there are no matching articles, tell the user directly.
- If the API request fails, report the exact failure and suggest checking whether FocusLedger backend / TTS worker is running.
- If delivery fails after audio generation, return the exact upload failure from the script.
