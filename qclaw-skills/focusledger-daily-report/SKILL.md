---
name: focusledger-daily-report
description: Generate a FocusLedger WeChat daily report for a specific date by calling the local FocusLedger API. Use when the user asks for 日报、公众号日报、某天的日报、今天/昨天/前天的日报、详细版、完整版、原文链接, or asks QClaw to summarize FocusLedger content for a date. Do not use for syncing sources, browsing article lists, or source management.
---

# FocusLedger Daily Report

Call the local FocusLedger backend and return the generated daily report text.

Never expose intermediate steps, tool calls, retries, encoding diagnostics, or reasoning. Reply only once with the final report text or a concise error message.

## Preconditions

- FocusLedger backend is running on `http://127.0.0.1:8100`
- The requested date already has synced articles in FocusLedger

## Workflow

1. Extract the target date from the user request.
2. If the user explicitly mentions a source group, pass it through `--group`.
3. Run the script:

```powershell
$env:FOCUSLEDGER_BASE_URL = "http://127.0.0.1:8100"
python E:\QClaw\QClaw\resources\openclaw\config\skills\focusledger-daily-report\scripts\fetch_daily_report.py --date "2026-04-02" --style brief
```

With source group:

```powershell
$env:FOCUSLEDGER_BASE_URL = "http://127.0.0.1:8100"
python E:\QClaw\QClaw\resources\openclaw\config\skills\focusledger-daily-report\scripts\fetch_daily_report.py --date "昨天" --group "投研/券商/中金" --style brief
```

4. Return the script stdout directly to the user. Do not rewrite the report unless the user asks for a shorter version.
5. If the user asks for `详细版`、`完整版` or `原文链接`, rerun the script with `--style full`.

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
- Do not fabricate report content.
- If the script says there are no matching articles, tell the user directly.
- If the API request fails, report the exact failure and suggest checking whether FocusLedger backend is running.
