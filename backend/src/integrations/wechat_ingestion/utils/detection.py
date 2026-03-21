from __future__ import annotations


def is_wechat_captcha_page(html: str, url: str | None = None) -> bool:
    markers = (
        "wappoc_appmsgcaptcha",
        "appmsgcaptcha",
        "captcha",
        "验证码",
        "安全验证",
        "访问过于频繁",
        "weixin.qq.com/mp/wappoc_appmsgcaptcha",
    )
    haystack = f"{url or ''}\n{html}".lower()
    return any(marker.lower() in haystack for marker in markers)

