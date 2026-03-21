from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def parse_date(raw: str) -> str:
    value = raw.strip()
    today = datetime.now(SHANGHAI_TZ).date()

    if value == "今天":
        return today.isoformat()
    if value == "昨天":
        return (today - timedelta(days=1)).isoformat()
    if value == "前天":
        return (today - timedelta(days=2)).isoformat()

    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            pass

    if "月" in value and "日" in value:
        try:
            month_part, day_part = value.split("月", 1)
            day_value = day_part.replace("日", "").strip()
            parsed = datetime(today.year, int(month_part.strip()), int(day_value)).date()
            return parsed.isoformat()
        except ValueError:
            pass

    raise ValueError(f"无法识别日期: {raw}")


def build_url(base_url: str, date: str, group: str | None, limit: int) -> str:
    query = {"date": parse_date(date), "limit": str(limit)}
    if group:
        query["source_group"] = group.strip()
    return f"{base_url.rstrip('/')}/api/v1/integrations/qclaw/daily-report?{urlencode(query)}"


def fetch(url: str, integration_key: str | None) -> dict:
    headers = {"Accept": "application/json"}
    if integration_key:
        headers["X-Integration-Key"] = integration_key
    request = Request(url, headers=headers, method="GET")
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Fetch FocusLedger daily report for QClaw.")
    parser.add_argument("--date", required=True, help="目标日期，如 2026-03-20 / 今天 / 昨天")
    parser.add_argument("--group", help="可选，来源分组路径")
    parser.add_argument("--limit", type=int, default=12, help="日报纳入文章上限")
    parser.add_argument("--style", choices=("brief", "full"), default="brief", help="返回短版还是完整版")
    parser.add_argument("--json", action="store_true", help="输出完整 JSON")
    args = parser.parse_args()

    base_url = os.environ.get("FOCUSLEDGER_BASE_URL", "http://127.0.0.1:8000")
    integration_key = os.environ.get("FOCUSLEDGER_QCLAW_KEY") or None
    url = build_url(base_url, args.date, args.group, args.limit)
    separator = "&" if "?" in url else "?"
    url = f"{url}{separator}style={args.style}"

    try:
        payload = fetch(url, integration_key)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"FocusLedger API 请求失败: HTTP {exc.code} {body}", file=sys.stderr)
        return 3
    except URLError as exc:
        print(f"无法连接 FocusLedger 后端: {exc.reason}", file=sys.stderr)
        return 4

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    reply_text = str(payload.get("reply_text") or "").strip()
    if not reply_text:
        print("FocusLedger 没有返回日报文本。", file=sys.stderr)
        return 5

    print(reply_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
