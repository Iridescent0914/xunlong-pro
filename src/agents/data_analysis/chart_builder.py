"""根据数据表生成图表 spec（数据分析智能体输出流程的一部分）。"""

import re
from typing import Any, Dict, List, Optional, Union

from ..html.echarts_generator import EChartsGenerator
from .schemas import DataTable

_NUMERIC_CELL_RE = re.compile(
    r"(-?\d[\d,]*(?:\.\d+)?)\s*(%|\uff05|\u4e07\u4ebf|\u4ebf\u5143|\u4ebf|\u4e07\u5143|\u4e07|\u7f8e\u5143|\u7f8e\u91d1|\u5143|b|bn|billion)?",
    re.IGNORECASE,
)



def build_chart_for_table(
    table: Union[DataTable, Dict[str, Any]],
    chart_id: str,
) -> Optional[Dict[str, Any]]:
    """为单张表生成最合适的 ECharts spec。"""
    if isinstance(table, dict):
        table_obj = DataTable(**table)
    else:
        table_obj = table

    if not table_obj.rows or not table_obj.columns or len(table_obj.columns) < 2:
        return None

    generator = EChartsGenerator()
    categories = [str(row[0]) for row in table_obj.rows[:12]]
    if not categories:
        return None

    if "季度" in "".join(table_obj.columns) or any("Q" in c for c in categories):
        values = [_to_float(row[1]) for row in table_obj.rows[:12]]
        if any(v != 0 for v in values):
            spec = generator.add_line_chart(
                chart_id=chart_id,
                title=table_obj.title,
                categories=categories,
                data=values,
                y_axis_name=table_obj.columns[1],
                smooth=True,
            )
            return {"type": "line", "title": table_obj.title, "spec": spec}

    cells = [str(row[1]) for row in table_obj.rows[:12]]
    unit_kinds = {_value_unit_kind(cell) for cell in cells}
    unit_kinds.discard("plain")
    if len(unit_kinds) > 1:
        return None

    values = [_parse_metric_value(row[1]) for row in table_obj.rows[:12]]
    y_axis_name = _infer_y_axis_name(cells)
    if not any(v != 0 for v in values):
        return None
    spec = generator.add_bar_chart(
        chart_id=chart_id,
        title=table_obj.title,
        categories=categories,
        data=values,
        y_axis_name=y_axis_name,
    )
    return {"type": "bar", "title": table_obj.title, "spec": spec}


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_metric_value(value: Any) -> float:
    if value is None or value == "" or value == "-":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace(",", "").replace("，", "")
    match = _NUMERIC_CELL_RE.search(text)
    if not match:
        return 0.0

    number = float(match.group(1).replace(",", ""))
    unit = (match.group(2) or "").strip()
    unit_lower = unit.lower()

    if unit in ("%", "％"):
        return number
    if unit == "万亿":
        return number * 10000
    if unit in ("亿", "亿元"):
        return number
    if unit in ("万", "万元"):
        return number / 10000
    if unit_lower in ("b", "bn", "billion"):
        return number * 10
    return number


def _value_unit_kind(cell: str) -> str:
    lowered = str(cell).lower()
    if "%" in lowered or "％" in lowered:
        return "percent"
    amount_tokens = (
        "$",
        "billion",
        "bn",
        "万亿",
        "亿元",
        "亿",
        "万元",
        "万",
        "美元",
        "美金",
    )
    if any(token in lowered for token in amount_tokens):
        return "amount"
    if re.search(r"\d\s*b\b", lowered):
        return "amount"
    return "plain"


def _infer_y_axis_name(cells: List[str]) -> str:
    joined = " ".join(cells)
    if "%" in joined or "％" in joined:
        return "百分比（%）"
    if "万亿" in joined:
        return "数值（万亿元）"
    if any(token in joined for token in ("亿", "美元", "美金", "$")) or re.search(r"(?i)\d\s*(b|bn|billion)\b", joined):
        return "数值（亿美元）"
    if "万" in joined:
        return "数值（万元）"
    return "数值"

