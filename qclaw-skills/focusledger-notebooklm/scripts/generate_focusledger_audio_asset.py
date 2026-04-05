from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
DEFAULT_BASE_URL = "http://127.0.0.1:8100"
DEFAULT_FORMAT = "explainer"
DEFAULT_TARGET_MINUTES = 5
DEFAULT_ENGINE = "tencent"
DEFAULT_VOICE_MODE = "duet"
DEFAULT_POLL_INTERVAL_SECONDS = 4
DEFAULT_TIMEOUT_SECONDS = 900
DEFAULT_QCLAW_SKILLS_ROOT = r"E:\QClaw\QClaw\resources\openclaw\config\skills"


class PipelineError(RuntimeError):
    pass


@dataclass
class ApiContext:
    base_url: str
    integration_key: str | None


def parse_date(raw: str) -> str:
    value = raw.strip()
    today = datetime.now(SHANGHAI_TZ).date()

    alias_map = {
        "今天": today,
        "昨日": today - timedelta(days=1),
        "昨天": today - timedelta(days=1),
        "前天": today - timedelta(days=2),
    }
    if value in alias_map:
        return alias_map[value].isoformat()

    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            pass

    month_day = re.fullmatch(r"\s*(\d{1,2})月(\d{1,2})日\s*", value)
    if month_day:
        return datetime(today.year, int(month_day.group(1)), int(month_day.group(2))).date().isoformat()

    raise ValueError(f"无法识别日期: {raw}")


def slugify_group(value: str | None) -> str:
    if not value:
        return ""
    compact = re.sub(r"[^0-9A-Za-z]+", "-", value.strip()).strip("-")
    return compact[:40]


def build_notebook_name(report_date: str, group: str | None) -> str:
    suffix = slugify_group(group)
    return f"FL-QClaw-Podcast-{report_date}" + (f"-{suffix}" if suffix else "")


def _headers(integration_key: str | None, *, json_body: bool = False) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if json_body:
        headers["Content-Type"] = "application/json"
    if integration_key:
        headers["X-Integration-Key"] = integration_key
    return headers


def api_request(
    context: ApiContext,
    method: str,
    path: str,
    *,
    query: dict[str, str | int | None] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> Any:
    query_string = ""
    if query:
        compact_query = {key: str(value) for key, value in query.items() if value not in {None, ""}}
        if compact_query:
            query_string = f"?{urlencode(compact_query)}"

    body = None
    headers = _headers(context.integration_key, json_body=payload is not None)
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    request = Request(
        f"{context.base_url.rstrip('/')}{path}{query_string}",
        headers=headers,
        data=body,
        method=method,
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_daily_report(context: ApiContext, report_date: str, group: str | None, limit: int) -> dict[str, Any]:
    payload = api_request(
        context,
        "GET",
        "/api/v1/integrations/qclaw/daily-report",
        query={
            "date": report_date,
            "source_group": group,
            "limit": limit,
            "style": "full",
        },
        timeout=90,
    )
    if not isinstance(payload, dict):
        raise PipelineError("FocusLedger 返回了无效的日报响应。")
    return payload


def list_notebooks(context: ApiContext) -> list[dict[str, Any]]:
    payload = api_request(context, "GET", "/api/v1/notebooks")
    if not isinstance(payload, dict):
        raise PipelineError("FocusLedger 返回了无效的 notebook 列表。")
    items = payload.get("items")
    if not isinstance(items, list):
        raise PipelineError("FocusLedger notebook 列表缺少 items。")
    return [item for item in items if isinstance(item, dict)]


def create_notebook(context: ApiContext, name: str, description: str) -> dict[str, Any]:
    payload = api_request(
        context,
        "POST",
        "/api/v1/notebooks",
        payload={
            "name": name,
            "emoji": "FL",
            "description": description,
        },
    )
    if not isinstance(payload, dict) or not payload.get("id"):
        raise PipelineError("创建播客 notebook 失败。")
    return payload


def get_notebook(context: ApiContext, notebook_id: str) -> dict[str, Any]:
    payload = api_request(context, "GET", f"/api/v1/notebooks/{notebook_id}")
    if not isinstance(payload, dict) or not payload.get("id"):
        raise PipelineError("读取播客 notebook 失败。")
    return payload


def add_notebook_articles(context: ApiContext, notebook_id: str, article_ids: list[str]) -> dict[str, Any]:
    payload = api_request(
        context,
        "POST",
        f"/api/v1/notebooks/{notebook_id}/articles",
        payload={"article_ids": article_ids},
    )
    if not isinstance(payload, dict) or not payload.get("id"):
        raise PipelineError("向 notebook 添加文章失败。")
    return payload


def list_podcasts(context: ApiContext, notebook_id: str) -> list[dict[str, Any]]:
    payload = api_request(context, "GET", f"/api/v1/notebooks/{notebook_id}/podcasts")
    if not isinstance(payload, dict):
        raise PipelineError("读取 notebook 播客列表失败。")
    items = payload.get("items")
    if not isinstance(items, list):
        raise PipelineError("播客列表响应缺少 items。")
    return [item for item in items if isinstance(item, dict)]


def create_podcast_script(
    context: ApiContext,
    notebook_id: str,
    article_ids: list[str],
    report_title: str,
    report_date: str,
) -> dict[str, Any]:
    payload = api_request(
        context,
        "POST",
        f"/api/v1/notebooks/{notebook_id}/podcasts",
        payload={
            "format": DEFAULT_FORMAT,
            "target_minutes": DEFAULT_TARGET_MINUTES,
            "focus_prompt": f"Generate a polished Chinese podcast for {report_date} based on the FocusLedger daily report: {report_title}",
            "article_ids": article_ids,
        },
        timeout=180,
    )
    if not isinstance(payload, dict) or not payload.get("id"):
        raise PipelineError("生成播客脚本失败。")
    return payload


def create_audio_job(context: ApiContext, notebook_id: str, script_id: str) -> dict[str, Any]:
    payload = api_request(
        context,
        "POST",
        f"/api/v1/notebooks/{notebook_id}/podcasts/{script_id}/audio",
        payload={
            "engine": DEFAULT_ENGINE,
            "voice_mode": DEFAULT_VOICE_MODE,
        },
        timeout=120,
    )
    if not isinstance(payload, dict):
        raise PipelineError("创建播客音频任务失败。")
    return payload


def get_audio_job(context: ApiContext, notebook_id: str, script_id: str) -> dict[str, Any]:
    payload = api_request(
        context,
        "GET",
        f"/api/v1/notebooks/{notebook_id}/podcasts/{script_id}/audio",
        timeout=120,
    )
    if not isinstance(payload, dict):
        raise PipelineError("读取播客音频任务失败。")
    return payload


def article_id_set(item: dict[str, Any]) -> set[str]:
    articles = item.get("articles")
    if not isinstance(articles, list):
        return set()
    result: set[str] = set()
    for article in articles:
        if isinstance(article, dict):
            article_id = str(article.get("id") or "").strip()
            if article_id:
                result.add(article_id)
    return result


def select_notebook(
    notebooks: list[dict[str, Any]],
    target_name: str,
    target_article_ids: set[str],
) -> dict[str, Any] | None:
    exact_name = next((item for item in notebooks if str(item.get("name") or "").strip() == target_name), None)
    if exact_name:
        return exact_name

    exact_articles: list[dict[str, Any]] = []
    superset_articles: list[dict[str, Any]] = []
    for item in notebooks:
        notebook_article_ids = article_id_set(item)
        if not notebook_article_ids:
            continue
        if notebook_article_ids == target_article_ids:
            exact_articles.append(item)
        elif target_article_ids.issubset(notebook_article_ids):
            superset_articles.append(item)

    if exact_articles:
        return sorted(exact_articles, key=lambda item: str(item.get("updated_at") or ""), reverse=True)[0]
    if superset_articles:
        return sorted(superset_articles, key=lambda item: str(item.get("updated_at") or ""), reverse=True)[0]
    return None


def choose_reusable_script(
    podcasts: list[dict[str, Any]],
    target_article_ids: set[str],
) -> dict[str, Any] | None:
    ranked = sorted(podcasts, key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    exact_match = None
    active_script = None
    for item in ranked:
        cited_ids = {
            str(article_id).strip()
            for article_id in (item.get("cited_article_ids") or [])
            if str(article_id).strip()
        }
        audio_status = str(item.get("audio_status") or "")
        has_audio = bool(item.get("audio_path"))

        if audio_status == "succeeded" and has_audio and cited_ids == target_article_ids:
            return item
        if audio_status in {"queued", "running"} and cited_ids == target_article_ids:
            active_script = item
        if exact_match is None and cited_ids == target_article_ids:
            exact_match = item

    return active_script or exact_match


def wait_for_audio(
    context: ApiContext,
    notebook_id: str,
    script_id: str,
    timeout_seconds: int,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    last_status = ""
    last_error = ""

    while time.monotonic() < deadline:
        payload = get_audio_job(context, notebook_id, script_id)
        status = str(payload.get("audio_status") or "").strip()
        last_status = status or last_status
        last_error = str(payload.get("audio_error") or "").strip() or last_error
        audio_path = str(payload.get("audio_path") or "").strip()

        if status == "succeeded" and audio_path:
            if Path(audio_path).exists():
                return audio_path
            raise PipelineError(f"播客音频任务已完成，但本地文件不存在: {audio_path}")
        if status == "failed":
            raise PipelineError(last_error or "播客音频生成失败。")

        time.sleep(DEFAULT_POLL_INTERVAL_SECONDS)

    raise PipelineError(f"播客音频生成超时，最后状态：{last_status or 'unknown'}")


def ensure_notebook(
    context: ApiContext,
    report_date: str,
    group: str | None,
    article_ids: list[str],
) -> dict[str, Any]:
    notebooks = list_notebooks(context)
    target_name = build_notebook_name(report_date, group)
    target_article_ids = set(article_ids)

    notebook = select_notebook(notebooks, target_name, target_article_ids)
    if notebook is None:
        notebook = create_notebook(
            context,
            name=target_name,
            description=f"QClaw daily podcast notebook for {report_date}",
        )

    notebook = get_notebook(context, str(notebook["id"]))
    existing_ids = article_id_set(notebook)
    missing_ids = [article_id for article_id in article_ids if article_id not in existing_ids]
    if missing_ids:
        notebook = add_notebook_articles(context, str(notebook["id"]), missing_ids)
    return notebook


def generate_or_reuse_audio(
    context: ApiContext,
    notebook: dict[str, Any],
    article_ids: list[str],
    report_title: str,
    report_date: str,
    timeout_seconds: int,
) -> str:
    notebook_id = str(notebook["id"])
    target_article_ids = set(article_ids)
    podcasts = list_podcasts(context, notebook_id)
    reusable = choose_reusable_script(podcasts, target_article_ids)

    if reusable is not None:
        try:
            script_id = str(reusable.get("id") or "").strip()
            audio_status = str(reusable.get("audio_status") or "").strip()
            audio_path = str(reusable.get("audio_path") or "").strip()
            if audio_status == "succeeded" and audio_path and Path(audio_path).exists():
                return audio_path
            if audio_status == "succeeded" and audio_path and script_id:
                create_audio_job(context, notebook_id, script_id)
                return wait_for_audio(context, notebook_id, script_id, timeout_seconds)
            if audio_status in {"queued", "running"} and script_id:
                return wait_for_audio(context, notebook_id, script_id, timeout_seconds)
            if script_id:
                create_audio_job(context, notebook_id, script_id)
                return wait_for_audio(context, notebook_id, script_id, timeout_seconds)
        except PipelineError:
            pass

    script = create_podcast_script(context, notebook_id, article_ids, report_title, report_date)
    script_id = str(script["id"])
    create_audio_job(context, notebook_id, script_id)
    return wait_for_audio(context, notebook_id, script_id, timeout_seconds)


def locate_cloud_backup_cmd() -> Path:
    candidate_roots = [
        Path(__file__).resolve().parents[2],
        Path(os.environ.get("QCLAW_SKILLS_ROOT", DEFAULT_QCLAW_SKILLS_ROOT)),
    ]
    for skills_root in candidate_roots:
        cmd_path = skills_root / "cloud-upload-backup" / "scripts" / "windows" / "cloud_backup.cmd"
        if cmd_path.exists():
            return cmd_path
    searched = " ; ".join(str(root) for root in candidate_roots)
    raise PipelineError(f"未找到 QClaw cloud-upload-backup 脚本。已搜索: {searched}")


def build_remote_path(audio_path: Path, report_date: str, group: str | None) -> str:
    group_suffix = slugify_group(group)
    segments = ["focusledger", "podcasts", report_date]
    if group_suffix:
        segments.append(group_suffix)
    segments.append(audio_path.name)
    return "/".join(segments)


def extract_json_payload(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if not text:
        raise PipelineError("QClaw 云文件上传没有返回内容。")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for candidate in reversed(lines):
        if candidate.startswith("{") and candidate.endswith("}"):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PipelineError(f"QClaw 云文件上传返回了无法解析的内容: {text}") from exc

    if not isinstance(parsed, dict):
        raise PipelineError("QClaw 云文件上传返回了非对象 JSON。")
    return parsed


def upload_to_qclaw_cloud(audio_path: str, report_date: str, group: str | None) -> dict[str, Any]:
    local_path = Path(audio_path)
    if not local_path.exists():
        raise PipelineError(f"播客音频已生成，但本地文件不存在: {local_path}")

    cloud_backup_cmd = locate_cloud_backup_cmd()
    remote_path = build_remote_path(local_path, report_date, group)
    command = [
        "cmd",
        "/c",
        str(cloud_backup_cmd),
        "upload",
        "--local-path",
        str(local_path),
        "--remote-path",
        remote_path,
        "--conflict-strategy",
        "ask",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    payload = extract_json_payload(stdout or stderr)
    success = bool(payload.get("success"))
    message = str(payload.get("message") or "").strip()
    if not success:
        http_status_match = re.search(r"状态码:\s*(\d{3})", message)
        if http_status_match:
            status_code = http_status_match.group(1)
            raise PipelineError(
                f"QClaw 云文件上传当前返回 HTTP {status_code}。请在 QClaw 实际对话中调用该 skill，"
                "并确认 QClaw 桌面端已登录且云文件能力可用。"
            )
        raise PipelineError(message or f"QClaw 云文件上传失败: {stderr or stdout or 'unknown error'}")
    if not message:
        raise PipelineError("QClaw 云文件上传成功，但缺少可返回给用户的消息内容。")
    return payload


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Generate or reuse a FocusLedger daily podcast audio file for QClaw.")
    parser.add_argument("--date", required=True, help="目标日期，例如 2026-04-02 / 今天 / 昨天")
    parser.add_argument("--group", help="可选，来源分组路径")
    parser.add_argument("--limit", type=int, default=12, help="日报纳入文章上限")
    parser.add_argument("--base-url", default=os.environ.get("FOCUSLEDGER_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--integration-key", default=os.environ.get("FOCUSLEDGER_QCLAW_KEY") or "")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS, help="等待音频生成的总超时秒数")
    parser.add_argument("--deliver", action="store_true", help="生成后自动上传到 QClaw 云文件并返回可分享消息")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    try:
        report_date = parse_date(args.date)
        context = ApiContext(
            base_url=args.base_url.rstrip("/"),
            integration_key=args.integration_key.strip() or None,
        )
        report = get_daily_report(context, report_date, args.group, max(1, min(args.limit, 30)))
        if not report.get("ok"):
            raise PipelineError(str(report.get("reply_text") or "该日期暂无可用日报数据。").strip())

        article_links = report.get("article_links")
        if not isinstance(article_links, list):
            raise PipelineError("日报响应缺少 article_links，无法生成播客。")

        article_ids = [
            str(item.get("id") or "").strip()
            for item in article_links
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        ]
        if not article_ids:
            raise PipelineError(f"{report_date} 暂无可用于播客生成的文章。")

        notebook = ensure_notebook(context, report_date, args.group, article_ids)
        audio_path = generate_or_reuse_audio(
            context,
            notebook=notebook,
            article_ids=article_ids,
            report_title=str(report.get("title") or f"{report_date} Daily Report").strip(),
            report_date=report_date,
            timeout_seconds=max(60, args.timeout),
        )

        delivery_payload: dict[str, Any] | None = None
        if args.deliver:
            delivery_payload = upload_to_qclaw_cloud(audio_path, report_date, args.group)

        if args.json:
            output: dict[str, Any] = {
                "ok": True,
                "date": report_date,
                "group": args.group,
                "notebook_id": notebook.get("id"),
                "audio_path": audio_path,
            }
            if delivery_payload is not None:
                output["delivery"] = delivery_payload
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            if delivery_payload is not None:
                print(str(delivery_payload.get("message") or "").strip())
            else:
                print(audio_path)
        return 0
    except ValueError as exc:
        message = str(exc)
        if args.json:
            print(json.dumps({"ok": False, "message": message}, ensure_ascii=False, indent=2))
        else:
            print(message, file=sys.stderr)
        return 2
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        message = f"FocusLedger API 请求失败: HTTP {exc.code} {body}"
        if args.json:
            print(json.dumps({"ok": False, "message": message}, ensure_ascii=False, indent=2))
        else:
            print(message, file=sys.stderr)
        return 3
    except URLError as exc:
        message = f"无法连接 FocusLedger 服务: {exc.reason}"
        if args.json:
            print(json.dumps({"ok": False, "message": message}, ensure_ascii=False, indent=2))
        else:
            print(message, file=sys.stderr)
        return 4
    except PipelineError as exc:
        message = str(exc)
        if args.json:
            print(json.dumps({"ok": False, "message": message}, ensure_ascii=False, indent=2))
        else:
            print(message, file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
