from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import requests


def build_base_url() -> str:
    return os.getenv("FOCUSLEDGER_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def build_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    integration_key = os.getenv("AGENT_INTEGRATION_KEY", "").strip()
    if integration_key:
        headers["x-integration-key"] = integration_key
    return headers


def request_json(method: str, path: str, *, params: dict[str, Any] | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.request(
        method=method,
        url=f"{build_base_url()}{path}",
        headers=build_headers(),
        params=params,
        json=payload,
        timeout=90,
    )
    try:
        data = response.json()
    except Exception:
        data = {"detail": response.text.strip()}
    if not response.ok:
        detail = data.get("detail") if isinstance(data, dict) else response.text
        raise RuntimeError(f"{response.status_code}: {detail}")
    if not isinstance(data, dict):
        raise RuntimeError("unexpected response payload")
    return data


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def str_to_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("boolean value expected")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run task-oriented FocusLedger actions for AI agent tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search = subparsers.add_parser("search-articles")
    search.add_argument("--query", default=None)
    search.add_argument("--source-name", default=None)
    search.add_argument("--tags", nargs="*", default=[])
    search.add_argument("--date-from", default=None)
    search.add_argument("--date-to", default=None)
    search.add_argument("--favorited-only", action="store_true")
    search.add_argument("--limit", type=int, default=10)

    import_links = subparsers.add_parser("import-links")
    import_links.add_argument("--urls", nargs="+", required=True)

    update_tags = subparsers.add_parser("update-article-tags")
    update_tags.add_argument("--article-ids", nargs="+", required=True)
    update_tags.add_argument("--add-tags", nargs="*", default=[])
    update_tags.add_argument("--remove-tags", nargs="*", default=[])
    update_tags.add_argument("--favorited", type=str_to_bool, default=None)

    summarize = subparsers.add_parser("summarize-articles")
    summarize.add_argument("--article-ids", nargs="+", required=True)

    list_notebooks = subparsers.add_parser("list-notebooks")
    list_notebooks.add_argument("--query", default=None)
    list_notebooks.add_argument("--limit", type=int, default=20)

    show_notebook = subparsers.add_parser("show-notebook")
    show_notebook.add_argument("--notebook-ref", required=True)

    create_notebook = subparsers.add_parser("create-notebook")
    create_notebook.add_argument("--name", required=True)
    create_notebook.add_argument("--emoji", default="📒")
    create_notebook.add_argument("--description", default=None)

    update_notebook = subparsers.add_parser("update-notebook")
    update_notebook.add_argument("--notebook-ref", required=True)
    update_notebook.add_argument("--name", default=None)
    update_notebook.add_argument("--emoji", default=None)
    update_notebook.add_argument("--description", default=None)

    add_to_notebook = subparsers.add_parser("add-to-notebook")
    add_to_notebook.add_argument("--notebook-ref", required=True)
    add_to_notebook.add_argument("--article-ids", nargs="+", required=True)

    ask_notebook = subparsers.add_parser("ask-notebook")
    ask_notebook.add_argument("--notebook-ref", required=True)
    ask_notebook.add_argument("--message", required=True)

    gen_script = subparsers.add_parser("generate-podcast-script")
    gen_script.add_argument("--notebook-ref", required=True)
    gen_script.add_argument("--format", default="explainer")
    gen_script.add_argument("--target-minutes", type=int, default=5)
    gen_script.add_argument("--focus-prompt", default=None)
    gen_script.add_argument("--article-ids", nargs="*", default=[])

    list_scripts = subparsers.add_parser("list-podcast-scripts")
    list_scripts.add_argument("--notebook-ref", required=True)

    show_script = subparsers.add_parser("show-podcast-script")
    show_script.add_argument("--notebook-ref", required=True)
    show_script.add_argument("--script-id", required=True)

    gen_audio = subparsers.add_parser("generate-podcast-audio")
    gen_audio.add_argument("--notebook-ref", required=True)
    gen_audio.add_argument("--script-id", default=None)
    gen_audio.add_argument("--engine", default="edge")
    gen_audio.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    gen_audio.add_argument("--voice-mode", default=None)
    gen_audio.add_argument("--rate", default="-8%")

    audio_status = subparsers.add_parser("get-audio-status")
    audio_status.add_argument("--notebook-ref", required=True)
    audio_status.add_argument("--script-id", required=True)

    args = parser.parse_args()

    try:
        if args.command == "search-articles":
            data = request_json(
                "GET",
                "/api/v1/integrations/agent/articles/search",
                params={
                    "q": args.query,
                    "source_name": args.source_name,
                    "tags": ",".join(args.tags) if args.tags else None,
                    "date_from": args.date_from,
                    "date_to": args.date_to,
                    "favorited_only": "true" if args.favorited_only else "false",
                    "limit": args.limit,
                },
            )
        elif args.command == "import-links":
            data = request_json(
                "POST",
                "/api/v1/integrations/agent/articles/import-links",
                payload={"urls": args.urls},
            )
        elif args.command == "update-article-tags":
            data = request_json(
                "POST",
                "/api/v1/integrations/agent/articles/tags",
                payload={
                    "article_ids": args.article_ids,
                    "add_tags": args.add_tags,
                    "remove_tags": args.remove_tags,
                    "favorited": args.favorited,
                },
            )
        elif args.command == "summarize-articles":
            data = request_json(
                "POST",
                "/api/v1/integrations/agent/articles/summarize",
                payload={"article_ids": args.article_ids},
            )
        elif args.command == "list-notebooks":
            data = request_json(
                "GET",
                "/api/v1/integrations/agent/notebooks",
                params={"q": args.query, "limit": args.limit},
            )
        elif args.command == "show-notebook":
            data = request_json("GET", f"/api/v1/integrations/agent/notebooks/{args.notebook_ref}")
        elif args.command == "create-notebook":
            data = request_json(
                "POST",
                "/api/v1/integrations/agent/notebooks",
                payload={"name": args.name, "emoji": args.emoji, "description": args.description},
            )
        elif args.command == "update-notebook":
            data = request_json(
                "POST",
                "/api/v1/integrations/agent/notebooks/update",
                payload={
                    "notebook_ref": args.notebook_ref,
                    "name": args.name,
                    "emoji": args.emoji,
                    "description": args.description,
                },
            )
        elif args.command == "add-to-notebook":
            data = request_json(
                "POST",
                "/api/v1/integrations/agent/notebooks/add-articles",
                payload={"notebook_ref": args.notebook_ref, "article_ids": args.article_ids},
            )
        elif args.command == "ask-notebook":
            data = request_json(
                "POST",
                "/api/v1/integrations/agent/notebooks/ask",
                payload={"notebook_ref": args.notebook_ref, "message": args.message},
            )
        elif args.command == "generate-podcast-script":
            data = request_json(
                "POST",
                "/api/v1/integrations/agent/notebooks/generate-podcast-script",
                payload={
                    "notebook_ref": args.notebook_ref,
                    "format": args.format,
                    "target_minutes": args.target_minutes,
                    "focus_prompt": args.focus_prompt,
                    "article_ids": args.article_ids,
                },
            )
        elif args.command == "list-podcast-scripts":
            data = request_json(
                "GET",
                f"/api/v1/integrations/agent/notebooks/{args.notebook_ref}/podcasts",
            )
        elif args.command == "show-podcast-script":
            data = request_json(
                "GET",
                f"/api/v1/integrations/agent/notebooks/{args.notebook_ref}/podcasts/{args.script_id}",
            )
        elif args.command == "generate-podcast-audio":
            data = request_json(
                "POST",
                "/api/v1/integrations/agent/notebooks/generate-podcast-audio",
                payload={
                    "notebook_ref": args.notebook_ref,
                    "script_id": args.script_id,
                    "engine": args.engine,
                    "voice": args.voice,
                    "voice_mode": args.voice_mode,
                    "rate": args.rate,
                },
            )
        elif args.command == "get-audio-status":
            data = request_json(
                "GET",
                f"/api/v1/integrations/agent/notebooks/{args.notebook_ref}/podcasts/{args.script_id}/audio",
            )
        else:
            raise RuntimeError("unsupported command")
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print_json(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
