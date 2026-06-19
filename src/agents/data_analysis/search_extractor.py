"""从搜索正文中结构化抽取数值（算法路径，非 LLM）。"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .search_relevance import _entity_matches_name, primary_entities


@dataclass
class ExtractedPoint:
    metric_id: str
    metric_label: str
    value: float
    unit: str
    period: Optional[str]
    source_index: int
    source_title: str
    raw_text: str


_SCALAR_PATTERNS: List[Tuple[str, str, str, str, int, float]] = [
    (r"销售收入[^。\n]{0,20}?(\d+(?:\.\d+)?)\s*亿", "revenue", "销售收入", "亿元", 1, 1),
    (r"营业收入[^。\n]{0,20}?(\d+(?:\.\d+)?)\s*亿", "revenue", "营业收入", "亿元", 1, 1),
    (r"营收[^。\n]{0,20}?(\d+(?:\.\d+)?)\s*亿", "revenue", "营收", "亿元", 1, 1),
    (r"营收.*?同比(?:增长|增幅)?\s*(\d+(?:\.\d+)?)\s*%", "revenue_yoy", "营收同比增长", "%", 1, 100),
    (r"收入.*?同比(?:增长|增幅)?\s*(\d+(?:\.\d+)?)\s*%", "revenue_yoy", "营收同比增长", "%", 1, 100),
    (r"净利润.*?同比(?:增长|增幅)?\s*(\d+(?:\.\d+)?)\s*%", "net_profit_yoy", "净利润同比增长", "%", 1, 100),
    (r"归母净利润.*?同比(?:增长|增幅)?\s*(\d+(?:\.\d+)?)\s*%", "net_profit_yoy", "净利润同比增长", "%", 1, 100),
    (r"毛利率\s*(\d+(?:\.\d+)?)\s*%", "gross_margin", "毛利率", "%", 1, 100),
    (r"资产负债率\s*(\d+(?:\.\d+)?)\s*%", "debt_ratio", "资产负债率", "%", 1, 100),
    (r"贷款总额增幅\s*(?:达)?\s*(\d+(?:\.\d+)?)\s*%", "loan_growth", "贷款总额增幅", "%", 1, 100),
    (r"总资产.*?增长\s*(\d+(?:\.\d+)?)\s*%", "asset_growth", "总资产增幅", "%", 1, 100),
]

_GENERIC_YOY_PATTERN = re.compile(
    r"同比(?:增长|增幅)(?:达)?\s*(\d+(?:\.\d+)?)\s*%"
)

_ABSOLUTE_PATTERNS: List[Tuple[str, str, str, str, int]] = [
    (
        r"(?:营收|销售收入|营业收入)(?:为|达|突破|约)?[^。\n]{0,15}?(\d+(?:\.\d+)?)\s*亿",
        "revenue",
        "营收",
        "亿元",
        1,
    ),
    (r"净利润\s*(?:为|达)?\s*(\d+(?:\.\d+)?)\s*亿(?:欧元|美元|元)?", "net_profit", "净利润", "亿元", 1),
    (r"总资产(?:规模)?[^。\n]{0,20}?(\d+(?:\.\d+)?)\s*万亿", "total_assets", "总资产", "万亿元", 1),
    (r"营收\s*(?:为|达)?\s*(\d+(?:\.\d+)?)\s*万(?:元)?", "revenue", "营收", "万元", 1),
]

_PERIOD_PATTERN = re.compile(
    r"(20\d{2}(?:Q[1-4]|年(?:第[一二三四1-4]季度)?)?)"
)

_COMPANY_IN_CONTEXT = re.compile(
    r"([\u4e00-\u9fffA-Za-z·]{2,8})(?:公司|集团|汽车|股份)?"
)

_CONTEXT_RADIUS = 90


def extract_from_search_results(
    search_results: List[Dict[str, Any]],
    max_items: int = 8,
    entity_terms: Optional[Sequence[str]] = None,
) -> List[ExtractedPoint]:
    primaries = primary_entities(list(entity_terms or []))
    points: List[ExtractedPoint] = []
    for i, item in enumerate(search_results[:max_items], 1):
        title = item.get("title", "")
        body = (item.get("content") or item.get("snippet") or "")[:4000]
        if not body:
            continue
        points.extend(
            _extract_from_text(
                body,
                source_index=i,
                source_title=title,
                entity_terms=primaries,
            )
        )
    return points


def _context_window(text: str, pos: int, radius: int = _CONTEXT_RADIUS) -> str:
    return text[max(0, pos - radius) : pos + radius]


def _entity_names_in_context(context: str, entity_terms: List[str]) -> bool:
    if not entity_terms:
        return True
    return any(e in context for e in entity_terms)


def _competing_subject_in_context(context: str, entity_terms: List[str]) -> bool:
    if not entity_terms:
        return False

    for match in _COMPANY_IN_CONTEXT.finditer(context):
        name = match.group(1)
        if len(name) < 2:
            continue
        if _entity_matches_name(name, entity_terms):
            continue
        tail = context[match.end() : match.end() + 35]
        if re.search(r"(?:营收|收入|净利润|利润|业绩)", tail):
            before = context[: match.start()]
            if not any(e in before[-40:] for e in entity_terms):
                return True
    return False


def _metric_bound_to_entity(
    text: str,
    match_start: int,
    match_end: int,
    entity_terms: List[str],
) -> bool:
    if not entity_terms:
        return True

    context = _context_window(text, match_start)
    if not _entity_names_in_context(context, entity_terms):
        return False
    if _competing_subject_in_context(context, entity_terms):
        return False

    local = text[max(0, match_start - 80) : match_end + 30]
    if any(e in local for e in entity_terms):
        return True

    return False


def _extract_from_text(
    text: str,
    source_index: int,
    source_title: str,
    entity_terms: Optional[List[str]] = None,
) -> List[ExtractedPoint]:
    entities = list(entity_terms or [])
    points: List[ExtractedPoint] = []
    seen: set = set()

    for pattern, metric_id, label, unit, group, divisor in _SCALAR_PATTERNS:
        for match in re.finditer(pattern, text):
            if not _metric_bound_to_entity(text, match.start(), match.end(), entities):
                continue
            raw = match.group(0)
            value = float(match.group(group)) / divisor
            period = _find_nearby_period(text, match.start())
            key = (metric_id, value, period, source_index)
            if key in seen:
                continue
            seen.add(key)
            points.append(
                ExtractedPoint(
                    metric_id=metric_id,
                    metric_label=label,
                    value=value,
                    unit=unit,
                    period=period,
                    source_index=source_index,
                    source_title=source_title,
                    raw_text=raw[:80],
                )
            )

    for match in _GENERIC_YOY_PATTERN.finditer(text):
        if not _metric_bound_to_entity(text, match.start(), match.end(), entities):
            continue
        raw = match.group(0)
        value = float(match.group(1)) / 100
        period = _find_nearby_period(text, match.start())
        key = ("revenue_yoy", value, period, source_index)
        if key in seen:
            continue
        seen.add(key)
        points.append(
            ExtractedPoint(
                metric_id="revenue_yoy",
                metric_label="同比增长",
                value=value,
                unit="%",
                period=period,
                source_index=source_index,
                source_title=source_title,
                raw_text=raw[:80],
            )
        )

    for pattern, metric_id, label, unit, group in _ABSOLUTE_PATTERNS:
        for match in re.finditer(pattern, text):
            if not _metric_bound_to_entity(text, match.start(), match.end(), entities):
                continue
            raw = match.group(0)
            value = float(match.group(group))
            period = _find_nearby_period(text, match.start())
            key = (metric_id, value, period, source_index)
            if key in seen:
                continue
            seen.add(key)
            points.append(
                ExtractedPoint(
                    metric_id=metric_id,
                    metric_label=label,
                    value=value,
                    unit=unit,
                    period=period,
                    source_index=source_index,
                    source_title=source_title,
                    raw_text=raw[:80],
                )
            )

    points.extend(_extract_quarterly_rows(text, source_index, source_title, entities))
    return points


def _find_nearby_period(text: str, pos: int) -> Optional[str]:
    window = text[max(0, pos - 40) : pos + 40]
    match = _PERIOD_PATTERN.search(window)
    return match.group(1) if match else None


def _extract_quarterly_rows(
    text: str,
    source_index: int,
    source_title: str,
    entity_terms: Optional[List[str]] = None,
) -> List[ExtractedPoint]:
    points: List[ExtractedPoint] = []
    pattern = re.compile(
        r"(20\d{2}Q[1-4])[^\d]{0,30}?"
        r"(?:营收|收入)\s*(?:为|达)?\s*(\d+(?:\.\d+)?)\s*万"
    )
    entities = list(entity_terms or [])
    for match in pattern.finditer(text):
        if not _metric_bound_to_entity(text, match.start(), match.end(), entities):
            continue
        period, value_str = match.group(1), match.group(2)
        points.append(
            ExtractedPoint(
                metric_id="revenue",
                metric_label="营收",
                value=float(value_str),
                unit="万元",
                period=period,
                source_index=source_index,
                source_title=source_title,
                raw_text=match.group(0)[:80],
            )
        )
    return points
