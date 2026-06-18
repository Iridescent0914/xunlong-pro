"""从搜索正文中结构化抽取数值（算法路径，非 LLM）。"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ExtractedPoint:
    """一条从正文抽取的可计算数据点。"""

    metric_id: str
    metric_label: str
    value: float
    unit: str
    period: Optional[str]
    source_index: int
    source_title: str
    raw_text: str


# (pattern, metric_id, label, unit, value_group, divisor)
_SCALAR_PATTERNS: List[Tuple[str, str, str, str, int, float]] = [
    (r"营收.*?同比(?:增长|增幅)?\s*(\d+(?:\.\d+)?)\s*%", "revenue_yoy", "营收同比增长", "%", 1, 100),
    (r"收入.*?同比(?:增长|增幅)?\s*(\d+(?:\.\d+)?)\s*%", "revenue_yoy", "营收同比增长", "%", 1, 100),
    (r"净利润.*?同比(?:增长|增幅)?\s*(\d+(?:\.\d+)?)\s*%", "net_profit_yoy", "净利润同比增长", "%", 1, 100),
    (r"归母净利润.*?同比(?:增长|增幅)?\s*(\d+(?:\.\d+)?)\s*%", "net_profit_yoy", "净利润同比增长", "%", 1, 100),
    (r"同比(?:增长|增幅)(?:达)?\s*(\d+(?:\.\d+)?)\s*%", "revenue_yoy", "同比增长", "%", 1, 100),
    (r"毛利率\s*(\d+(?:\.\d+)?)\s*%", "gross_margin", "毛利率", "%", 1, 100),
    (r"资产负债率\s*(\d+(?:\.\d+)?)\s*%", "debt_ratio", "资产负债率", "%", 1, 100),
    (r"贷款总额增幅\s*(?:达)?\s*(\d+(?:\.\d+)?)\s*%", "loan_growth", "贷款总额增幅", "%", 1, 100),
    (r"总资产.*?增长\s*(\d+(?:\.\d+)?)\s*%", "asset_growth", "总资产增幅", "%", 1, 100),
    (r"增幅\s*(?:达)?\s*(\d+(?:\.\d+)?)\s*%", "growth_rate", "增幅", "%", 1, 100),
]

# (pattern, metric_id, label, unit, value_group)
_ABSOLUTE_PATTERNS: List[Tuple[str, str, str, str, int]] = [
    (r"净利润\s*(?:为|达)?\s*(\d+(?:\.\d+)?)\s*亿(?:欧元|美元|元)?", "net_profit", "净利润", "亿元", 1),
    (r"总资产(?:规模)?[^。\n]{0,20}?(\d+(?:\.\d+)?)\s*万亿", "total_assets", "总资产", "万亿元", 1),
    (r"营收\s*(?:为|达)?\s*(\d+(?:\.\d+)?)\s*万(?:元)?", "revenue", "营收", "万元", 1),
]

_PERIOD_PATTERN = re.compile(
    r"(20\d{2}(?:Q[1-4]|年(?:第[一二三四1-4]季度)?)?)"
)


def extract_from_search_results(
    search_results: List[Dict[str, Any]],
    max_items: int = 5,
) -> List[ExtractedPoint]:
    """逐条搜索正文抽取结构化数据点。"""
    points: List[ExtractedPoint] = []
    for i, item in enumerate(search_results[:max_items], 1):
        title = item.get("title", "")
        body = item.get("content") or item.get("snippet") or ""
        if not body:
            continue
        points.extend(_extract_from_text(body, source_index=i, source_title=title))
    return points


def _extract_from_text(
    text: str,
    source_index: int,
    source_title: str,
) -> List[ExtractedPoint]:
    points: List[ExtractedPoint] = []
    seen: set = set()

    for pattern, metric_id, label, unit, group, divisor in _SCALAR_PATTERNS:
        for match in re.finditer(pattern, text):
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

    for pattern, metric_id, label, unit, group in _ABSOLUTE_PATTERNS:
        for match in re.finditer(pattern, text):
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

    points.extend(_extract_quarterly_rows(text, source_index, source_title))
    return points


def _find_nearby_period(text: str, pos: int) -> Optional[str]:
    window = text[max(0, pos - 40) : pos + 40]
    match = _PERIOD_PATTERN.search(window)
    return match.group(1) if match else None


def _extract_quarterly_rows(
    text: str,
    source_index: int,
    source_title: str,
) -> List[ExtractedPoint]:
    """匹配「2024Q1 ... 12000」类时序片段。"""
    points: List[ExtractedPoint] = []
    pattern = re.compile(
        r"(20\d{2}Q[1-4])[^\d]{0,30}?"
        r"(?:营收|收入)\s*(?:为|达)?\s*(\d+(?:\.\d+)?)\s*万"
    )
    for match in pattern.finditer(text):
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
