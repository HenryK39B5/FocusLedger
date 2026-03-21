from __future__ import annotations

from src.parsers.wechat import parse_wechat_html


def test_parse_wechat_html_extracts_title():
    html = """
    <html>
      <head>
        <meta property="og:title" content="测试文章" />
        <meta property="og:url" content="https://mp.weixin.qq.com/s/test" />
        <meta name="author" content="张三" />
      </head>
      <body>
        <div class="wx_follow_nickname">测试公众号</div>
        <article>第一段内容。第二段内容。</article>
      </body>
    </html>
    """
    parsed = parse_wechat_html(html, "https://mp.weixin.qq.com/s/test")
    assert parsed.title == "测试文章"
    assert parsed.author == "张三"
    assert parsed.source_name == "测试公众号"
    assert parsed.url == "https://mp.weixin.qq.com/s/test"

