"""根据数据表生成图表 spec（数据分析智能体输出流程的一部分）。"""

import re
from typing import Any, Dict, List, Optional, Union

from ..html.echarts_generator import EChartsGenerator
from .schemas import DataTable

_NUMERIC_RE = re.compile(r"([-+]?\d[\d,]*(?:\.\d+)?)")



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

    chart_rows, value_cells = _select_chart_rows(table_obj)
    if not chart_rows:
        return None

    generator = EChartsGenerator()
    categories = [str(row[0]) for row in chart_rows]

    if "季度" in "".join(table_obj.columns) or any("Q" in c for c in categories):
        values = [_to_float(row[1]) for row in chart_rows]
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

    values = [_parse_metric_value(row[1]) for row in chart_rows]
    y_axis_name = _infer_y_axis_name(value_cells)
    if not any(v != 0 for v in values):
        # 尝试其他数值列
        for col_idx in range(1, len(table_obj.columns)):
            col_cells = [str(row[col_idx]) for row in chart_rows]
            col_kinds = {_value_unit_kind(c) for c in col_cells}
            col_kinds.discard("plain")
            if len(col_kinds) <= 1:
                values = [_parse_metric_value(row[col_idx]) for row in chart_rows]
                if any(v != 0 for v in values):
                    spec = generator.add_bar_chart(
                        chart_id=chart_id,
                        title=table_obj.title,
                        categories=categories,
                        data=values,
                        y_axis_name=_infer_y_axis_name(col_cells),
                    )
                    return {"type": "bar", "title": table_obj.title, "spec": spec}
        return None
    spec = generator.add_bar_chart(
        chart_id=chart_id,
        title=table_obj.title,
        categories=categories,
        data=values,
        y_axis_name=y_axis_name,
    )
    return {"type": "bar", "title": table_obj.title, "spec": spec}


def _select_chart_rows(table_obj: DataTable) -> tuple[List[List[Any]], List[str]]:
    """选取单位一致的行用于绘图；百分比与绝对值混排时优先保留百分比行。"""
    rows = list(table_obj.rows[:12])
    if not rows:
        return [], []

    value_cells = [str(row[1]) for row in rows if len(row) > 1]
    kinds = [_value_unit_kind(cell) for cell in value_cells]
    if not kinds:
        return rows, value_cells

    if "percent" in kinds and "amount" in kinds:
        filtered = [row for row in rows if len(row) > 1 and _value_unit_kind(str(row[1])) == "percent"]
        if filtered:
            return filtered, [str(row[1]) for row in filtered]
        return [], []

    unit_kinds = set(kinds)
    unit_kinds.discard("plain")
    if len(unit_kinds) > 1:
        return [], []
    return rows, value_cells


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_metric_value(value: Any) -> float:
    """从任意格式的数值字符串中提取数值并按单位换算（单位在数值之后）。"""
    if value is None or value == "" or value == "-":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    match = _NUMERIC_RE.match(text)
    if not match:
        return 0.0

    number = float(match.group(1).replace(",", ""))
    suffix = text[match.end() :].strip().lower()

    if "%" in suffix:
        return number
    if "万亿" in suffix:
        return number * 10000
    if "亿" in suffix:
        return number
    if "万" in suffix and "亿" not in suffix:
        return number / 10000
    if suffix.startswith(("$", "美元", "美金", "usd")):
        return number
    if suffix.startswith(("b", "bn")) and "billion" not in suffix:
        return number * 10
    if "billion" in suffix:
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
    if "元" in lowered and "%" not in lowered and "％" not in lowered:
        return "amount"
    if re.search(r"\d\s*b\b", lowered):
        return "amount"

    match = _NUMERIC_RE.search(str(cell))
    if match:
        try:
            if abs(float(match.group(1).replace(",", ""))) >= 1000:
                return "amount"
        except ValueError:
            pass
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

