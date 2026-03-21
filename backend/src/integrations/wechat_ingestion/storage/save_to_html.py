from __future__ import annotations

import json

import requests

from src.integrations.wechat_ingestion.utils.detection import is_wechat_captcha_page
from src.integrations.wechat_ingestion.utils.tools import ensure_dir


class SaveWebpageToHtml:
    def __init__(self):
        self.html_filename = "index.html"

    def save_webpage_with_resources(self, url: str, output_dir: str, timeout: int = 20) -> str | None:
        target_dir = ensure_dir(output_dir)
        try:
            response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}, verify=False)
            response.raise_for_status()
            if is_wechat_captcha_page(response.text, response.url):
                return None
            html_path = target_dir / self.html_filename
            html_path.write_text(response.text, encoding="utf-8")
            (target_dir / "page_meta.json").write_text(
                json.dumps({"url": url, "status_code": response.status_code}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return str(html_path)
        except Exception:
            return None
