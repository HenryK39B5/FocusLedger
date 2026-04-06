---
name: focusledger-notebooklm
description: Operate the local FocusLedger article library and notebook workspace from AI agent tools. Use when the user asks to import article links, search articles, organize tags, create or manage notebooks, ask questions against a notebook, generate podcast scripts, or generate podcast audio.
---

# FocusLedger NotebookLM Skill

This skill lets AI agent tools call the local FocusLedger backend through task-oriented commands.

Never expose tool calls, raw HTTP details, local script paths, or intermediate reasoning unless the user explicitly asks.
Reply with the final result only.

## Preconditions

- FocusLedger backend is running on `http://127.0.0.1:8000`
- If `AGENT_INTEGRATION_KEY` is configured in FocusLedger, the same key is available to this skill
- For notebook Q&A, podcast scripts, and podcast audio, FocusLedger must already have usable LLM / TTS configuration

## Core mental model

FocusLedger has three layers:

1. Article library
2. Notebook workspace
3. Notebook outputs

The podcast flow is strict:

1. A notebook contains source articles
2. A podcast script is generated from that notebook
3. Podcast audio is generated from that podcast script

Do not skip step 2.
Do not use notebook Q&A or article summary output as a substitute for a podcast script.

If the user asks for podcast audio and there is no existing script, you must create a podcast script first.

## Main capabilities

### 1. Import article links

Use when the user sends one or more WeChat article links and wants them added into FocusLedger.

```powershell
python <skill-install-dir>\scripts\run_focusledger_action.py import-links --urls "https://mp.weixin.qq.com/s/..." "https://mp.weixin.qq.com/s/..."
```

### 2. Search articles

Use when the user asks to find articles by keyword, source, tags, or time range.

```powershell
python <skill-install-dir>\scripts\run_focusledger_action.py search-articles --query "AI Agent" --limit 8
```

Optional filters:

- `--source-name`
- `--tags`
- `--date-from`
- `--date-to`
- `--favorited-only`

### 3. Update article tags or favorite status

Use when the user asks to add tags, remove tags, or mark articles as favorited.

```powershell
python <skill-install-dir>\scripts\run_focusledger_action.py update-article-tags --article-ids "id1" "id2" --add-tags "AI/AI Agent" "产品/工作流" --favorited true
```

### 4. Summarize articles with LLM

Use when the user asks to summarize one or more known articles.

```powershell
python <skill-install-dir>\scripts\run_focusledger_action.py summarize-articles --article-ids "id1" "id2"
```

### 5. Notebook management

Create notebook:

```powershell
python <skill-install-dir>\scripts\run_focusledger_action.py create-notebook --name "AI Agent 研究" --emoji "🤖"
```

List notebooks:

```powershell
python <skill-install-dir>\scripts\run_focusledger_action.py list-notebooks --query "AI"
```

Show notebook detail:

```powershell
python <skill-install-dir>\scripts\run_focusledger_action.py show-notebook --notebook-ref "AI Agent 研究"
```

Update notebook metadata:

```powershell
python <skill-install-dir>\scripts\run_focusledger_action.py update-notebook --notebook-ref "AI Agent 研究" --name "AI Agent 商业化研究" --emoji "🧠"
```

Add articles to notebook:

```powershell
python <skill-install-dir>\scripts\run_focusledger_action.py add-to-notebook --notebook-ref "AI Agent 研究" --article-ids "id1" "id2"
```

### 6. Ask questions against a notebook

Use when the user asks a research question against notebook sources.

```powershell
python <skill-install-dir>\scripts\run_focusledger_action.py ask-notebook --notebook-ref "AI Agent 研究" --message "请总结这些文章对 AI Agent 商业化的主要判断"
```

### 7. Generate podcast scripts

Generate a script:

```powershell
python <skill-install-dir>\scripts\run_focusledger_action.py generate-podcast-script --notebook-ref "AI Agent 研究" --format explainer --target-minutes 6
```

Optional:

- `--focus-prompt`
- `--article-ids`

List existing scripts:

```powershell
python <skill-install-dir>\scripts\run_focusledger_action.py list-podcast-scripts --notebook-ref "AI Agent 研究"
```

Show one script:

```powershell
python <skill-install-dir>\scripts\run_focusledger_action.py show-podcast-script --notebook-ref "AI Agent 研究" --script-id "script_id"
```

### 8. Generate podcast audio

Create audio job from an existing podcast script:

```powershell
python <skill-install-dir>\scripts\run_focusledger_action.py generate-podcast-audio --notebook-ref "AI Agent 研究" --script-id "script_id" --engine edge
```

Check audio job status:

```powershell
python <skill-install-dir>\scripts\run_focusledger_action.py get-audio-status --notebook-ref "AI Agent 研究" --script-id "script_id"
```

## Workflow guidance

### When the user gives article links

1. Use `import-links`
2. Return imported / updated / failed counts
3. Mention whether new sources were created if useful

### When the user asks to organize topic articles

1. Use `search-articles`
2. If needed, use `update-article-tags` or `summarize-articles`
3. Return a concise summary with titles or counts

### When the user asks to create a notebook

1. Use `create-notebook`
2. If the request also includes article context, then `search-articles` and `add-to-notebook`

### When the user asks to generate podcast audio

This is the mandatory workflow:

1. Resolve the notebook
2. Check whether a suitable podcast script already exists with `list-podcast-scripts`
3. If no suitable script exists, call `generate-podcast-script`
4. Then call `generate-podcast-audio`
5. If the audio job is not finished, call `get-audio-status` and report the current state

Never replace step 3 with:

- notebook Q&A
- article summaries
- ad hoc text synthesis

Podcast audio must always be generated from a notebook podcast script.

### When the user asks a broad notebook task

Choose the narrowest correct action:

- Research answer: `ask-notebook`
- Script output: `generate-podcast-script`
- Audio output: script first, then `generate-podcast-audio`

Do not confuse these three output types.

## Rules

- Prefer exact notebook names when available
- If multiple notebooks or sources match, ask the user to clarify rather than guessing
- Do not fabricate article IDs, notebook IDs, script IDs, or audio paths
- If a task depends on IDs, first search or list, then use the returned IDs
- If FocusLedger returns a backend error, report it concisely
- Keep the final response concise and task-oriented
