from __future__ import annotations

from collections import Counter
import re

TAXONOMY_VERSION = "finance-v2"

TOPIC_TAGS = [
    "macro/政策",
    "macro/利率",
    "macro/汇率",
    "macro/流动性",
    "macro/通胀",
    "macro/增长",
    "macro/数据",
    "asset/股票",
    "asset/债券",
    "asset/商品",
    "asset/外汇",
    "asset/基金",
    "asset/加密资产",
    "sector/科技",
    "sector/互联网",
    "sector/金融",
    "sector/消费",
    "sector/医药",
    "sector/制造",
    "sector/地产",
    "sector/能源",
    "sector/军工",
    "sector/汽车",
    "sector/半导体",
    "sector/新能源",
    "sector/周期",
    "theme/AI",
    "theme/大模型",
    "theme/出海",
    "theme/高股息",
    "theme/回购",
    "theme/分红",
    "theme/并购重组",
    "theme/降本增效",
    "theme/国产替代",
    "theme/供给侧",
    "theme/产业升级",
    "theme/全球化",
    "theme/自主可控",
    "event/财报",
    "event/业绩预告",
    "event/政策发布",
    "event/数据发布",
    "event/会议",
    "event/访谈",
    "event/调研",
    "event/公告",
    "event/路演",
    "event/行业跟踪",
    "region/中国",
    "region/美国",
    "region/欧洲",
    "region/日本",
    "region/新兴市场",
    "risk/估值",
    "risk/业绩",
    "risk/政策",
    "risk/流动性",
    "risk/地缘",
    "risk/竞争",
]

TOPIC_TAG_SET = set(TOPIC_TAGS)

STYLE_TAGS = [
    "style/深度研究",
    "style/快讯",
    "style/复盘",
    "style/访谈",
    "style/数据图表",
    "style/事件驱动",
    "style/案例驱动",
    "style/结构化",
]

STYLE_TAG_SET = set(STYLE_TAGS)

CONTENT_TYPES = [
    "深度研究",
    "快讯",
    "复盘",
    "访谈",
    "数据解读",
    "公告解读",
    "观点",
    "新闻",
]

CONTENT_TYPE_SET = set(CONTENT_TYPES)

_TOPIC_RULES: list[tuple[tuple[str, ...], list[str]]] = [
    (("降准", "降息", "LPR", "MLF", "央行", "公开市场", "回购利率", "货币政策"), ["macro/政策", "macro/流动性"]),
    (("利率", "收益率", "国债", "美债", "信用利差", "债券"), ["macro/利率", "asset/债券"]),
    (("汇率", "美元指数", "人民币", "外汇"), ["macro/汇率", "asset/外汇"]),
    (("CPI", "PPI", "PMI", "GDP", "社融", "信贷", "就业", "出口", "进口"), ["macro/数据", "macro/增长"]),
    (("股票", "A股", "港股", "美股", "ETF", "基金"), ["asset/股票", "asset/基金"]),
    (("财报", "业绩", "营收", "利润", "净利", "业绩预告", "报表"), ["event/财报", "risk/业绩"]),
    (("公告", "分红", "回购", "派息", "现金流"), ["event/公告", "theme/分红", "theme/回购"]),
    (("访谈", "采访", "对话", "圆桌", "问答"), ["event/访谈", "style/访谈"]),
    (("调研", "路演", "会议", "峰会", "论坛"), ["event/调研", "event/会议"]),
    (("AI", "人工智能", "大模型", "算力", "GPU", "芯片", "推理"), ["sector/科技", "theme/AI", "theme/大模型", "sector/半导体"]),
    (("互联网", "平台", "电商", "社交", "流量", "内容平台"), ["sector/互联网"]),
    (("银行", "保险", "券商", "信托", "资管"), ["sector/金融"]),
    (("消费", "零售", "品牌", "食品", "饮料", "家电"), ["sector/消费"]),
    (("医药", "医疗", "创新药", "器械", "疫苗"), ["sector/医药"]),
    (("制造", "工业", "设备", "机器人", "自动化"), ["sector/制造"]),
    (("地产", "房企", "楼市", "房地产"), ["sector/地产"]),
    (("能源", "油价", "天然气", "煤炭", "电力"), ["sector/能源", "asset/商品"]),
    (("军工", "国防", "航空航天"), ["sector/军工"]),
    (("汽车", "新能源车", "车企", "电动车"), ["sector/汽车", "sector/新能源"]),
    (("光伏", "储能", "风电", "锂电"), ["sector/新能源"]),
    (("估值", "PE", "PB", "折价", "溢价"), ["risk/估值"]),
    (("地缘", "冲突", "制裁", "关税", "贸易摩擦"), ["risk/地缘", "risk/政策"]),
    (("竞争", "份额", "替代", "格局", "壁垒"), ["risk/竞争"]),
    (("国产替代", "自主可控"), ["theme/国产替代", "theme/自主可控"]),
    (("供给侧", "产能", "库存"), ["theme/供给侧"]),
    (("出海", "海外收入", "全球化"), ["theme/出海", "theme/全球化", "region/新兴市场"]),
    (("高股息", "股息率"), ["theme/高股息", "theme/分红"]),
]

_STYLE_RULES: list[tuple[tuple[str, ...], list[str]]] = [
    (("快讯", "简讯", "速览", "速递"), ["style/快讯"]),
    (("复盘", "回顾", "盘点", "总结"), ["style/复盘"]),
    (("访谈", "采访", "对话", "问答"), ["style/访谈"]),
    (("图表", "数据", "统计", "指标"), ["style/数据图表"]),
    (("结构", "框架", "拆解", "系统"), ["style/结构化"]),
    (("案例", "案例研究"), ["style/案例驱动"]),
]

_VARIABLE_KEYWORDS = [
    "增长",
    "收入",
    "营收",
    "利润",
    "净利",
    "现金流",
    "估值",
    "利率",
    "流动性",
    "库存",
    "订单",
    "需求",
    "供给",
    "政策",
    "汇率",
    "成本",
    "毛利率",
    "市占率",
]


def normalize_tag_items(items: list[str] | None, *, allowed: set[str] | None = None, limit: int | None = None) -> list[str]:
    if not items:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        if allowed is not None and cleaned not in allowed:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
        if limit is not None and len(normalized) >= limit:
            break
    return normalized


def _matches_keywords(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _apply_rules(text: str, rules: list[tuple[tuple[str, ...], list[str]]], limit: int) -> list[str]:
    picks: list[str] = []
    for keywords, tags in rules:
        if _matches_keywords(text, keywords):
            picks.extend(tags)
        if len(picks) >= limit:
            break
    return normalize_tag_items(picks, limit=limit)


def _dedupe_preserve(items: list[str], limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def suggest_topic_tags(text: str, limit: int = 8) -> list[str]:
    picks = _apply_rules(text, _TOPIC_RULES, limit)
    if picks:
      return normalize_tag_items(picks, allowed=TOPIC_TAG_SET, limit=limit)

    tokens = re.findall(r"[\u4e00-\u9fffA-Za-z0-9_]+", text)
    counts = Counter(token for token in tokens if len(token) > 1)
    return _dedupe_preserve([token for token, _ in counts.most_common(limit * 2)], limit)


def suggest_style_tags(text: str, limit: int = 4) -> list[str]:
    picks = _apply_rules(text, _STYLE_RULES, limit)
    if len(text) > 1800 and "style/深度研究" not in picks:
        picks.insert(0, "style/深度研究")
    if len(text) < 500 and "style/快讯" not in picks and "style/复盘" not in picks:
        picks.insert(0, "style/快讯")
    return normalize_tag_items(picks, allowed=STYLE_TAG_SET, limit=limit)


def suggest_content_type(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("访谈", "采访", "问答")):
        return "访谈"
    if any(token in lowered for token in ("快讯", "简讯", "速览", "速递")):
        return "快讯"
    if any(token in lowered for token in ("复盘", "回顾", "盘点")):
        return "复盘"
    if any(token in lowered for token in ("公告", "财报", "业绩预告", "招股书")):
        return "公告解读"
    if any(token in lowered for token in ("数据", "cpi", "ppi", "pmi", "gdp", "社融")):
        return "数据解读"
    if len(text) > 1800:
        return "深度研究"
    if len(text) < 600:
        return "新闻"
    return "观点"


def extract_entity_tags(text: str, limit: int = 8) -> list[str]:
    candidates = re.findall(r"[\u4e00-\u9fffA-Za-z0-9_.&·-]{2,}", text)
    filtered: list[str] = []
    for candidate in candidates:
      if candidate.isdigit():
        continue
      if candidate in TOPIC_TAGS:
        continue
      if candidate.lower() in {"the", "and", "with", "from"}:
        continue
      filtered.append(candidate)
    counts = Counter(filtered)
    return _dedupe_preserve([item for item, _ in counts.most_common(limit * 2)], limit)


def suggest_core_claims(text: str, limit: int = 4) -> list[str]:
    sentences = [line.strip() for line in re.split(r"[。！？!?]\s*", text) if line.strip()]
    return [sentence[:120] for sentence in sentences[:limit]]


def suggest_key_variables(text: str, limit: int = 5) -> list[str]:
    picks = [item for item in _VARIABLE_KEYWORDS if item in text]
    if not picks:
        picks = suggest_topic_tags(text, limit=limit)
    return normalize_tag_items(picks, limit=limit)


def suggest_catalysts(text: str, limit: int = 3) -> list[str]:
    picks = []
    for keyword in ("政策", "财报", "会议", "调研", "访谈", "发布", "数据", "降息", "降准", "回购", "分红"):
        if keyword in text:
            picks.append(keyword)
    return normalize_tag_items(picks, limit=limit)


def suggest_risks(text: str, limit: int = 3) -> list[str]:
    picks = []
    for keyword in ("估值", "业绩", "政策", "流动性", "地缘", "竞争", "波动", "回撤", "不确定性"):
        if keyword in text:
            picks.append(keyword)
    return normalize_tag_items(picks, limit=limit)


def taxonomy_prompt_block() -> str:
    topic = "、".join(TOPIC_TAGS)
    style = "、".join(STYLE_TAGS)
    content = "、".join(CONTENT_TYPES)
    return (
        "可用 topic_tags 只能从下列财经标签体系中选择，使用命名空间格式，尽量控制在 3 到 8 个：\n"
        f"{topic}\n\n"
        "可用 style_tags 只能从下列样式标签中选择，尽量控制在 1 到 3 个：\n"
        f"{style}\n\n"
        "content_type 只能从下列类型中选择 1 个：\n"
        f"{content}\n"
    )
