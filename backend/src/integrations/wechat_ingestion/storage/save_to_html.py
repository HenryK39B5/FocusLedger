from __future__ import annotations

import json

import requests
from urllib3.exceptions import InsecureRequestWarning

from src.integrations.wechat_ingestion.utils.detection import is_wechat_captcha_page
from src.integrations.wechat_ingestion.utils.tools import ensure_dir


class SaveWebpageToHtml:
    def __init__(self, verify_ssl: bool = False):
        self.html_filename = "index.html"
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.proxies = {"http": None, "https": None}
        if not self.verify_ssl:
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

    def save_webpage_with_resources(self, url: str, output_dir: str, timeout: int = 20) -> str | None:
        target_dir = ensure_dir(output_dir)
        try:
            response = self.session.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0"},
                verify=self.verify_ssl,
                proxies={"http": None, "https": None},
            )
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
