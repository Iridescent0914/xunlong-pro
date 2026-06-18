"""根据 AnalysisOutput 生成图表 spec（数据分析智能体输出流程的一部分）。"""

from typing import Any, Dict, List, Union

from loguru import logger

from ..html.echarts_generator import EChartsGenerator
from .analysis_output import AnalysisOutput
from .schemas import ProcessedStats


def build_charts(analysis: Union[AnalysisOutput, ProcessedStats]) -> List[Dict[str, Any]]:
    """从算法计算产出的 metrics / tables 构建 ECharts 配置列表。"""
    charts: List[Dict[str, Any]] = []
    generator = EChartsGenerator()

    revenue_table = _find_table(analysis, "分季度")
    if revenue_table and len(revenue_table.rows) >= 2:
        categories = [str(row[0]) for row in revenue_table.rows]
        values = [_to_float(row[1]) for row in revenue_table.rows]
        spec = generator.add_line_chart(
            chart_id="chart_revenue_trend",
            title=revenue_table.title,
            categories=categories,
            data=values,
            y_axis_name="营收（万元）",
        )
        charts.append({"type": "line", "title": revenue_table.title, "spec": spec})

        if revenue_table.columns and len(revenue_table.columns) >= 3:
            mom_values = [_parse_pct(row[2]) for row in revenue_table.rows if len(row) >= 3]
            if any(v != 0 for v in mom_values):
                spec = generator.add_bar_chart(
                    chart_id="chart_revenue_mom",
                    title="营收环比变化",
                    categories=categories,
                    data=mom_values,
                    y_axis_name="环比（%）",
                )
                charts.append({"type": "bar", "title": "营收环比变化", "spec": spec})
        return charts

    detail_table = _find_table(analysis, "抽取指标")
    if detail_table and detail_table.rows:
        categories = [str(row[0]) for row in detail_table.rows[:8]]
        values = [_parse_metric_value(row[1]) for row in detail_table.rows[:8]]
        spec = generator.add_bar_chart(
            chart_id="chart_extracted_metrics",
            title="抽取指标对比",
            categories=categories,
            data=values,
        )
        charts.append({"type": "bar", "title": "抽取指标对比", "spec": spec})
        return charts

    if analysis.metrics:
        rate_keys = [
            k for k in analysis.metrics
            if k.endswith("_yoy") or k.endswith("_growth") or k.endswith("_rate")
            or k in ("gross_margin", "debt_ratio", "loan_growth", "asset_growth", "avg_growth_rate")
        ]
        keys = rate_keys[:5] if rate_keys else list(analysis.metrics.keys())[:5]
        values = [_to_float(analysis.metrics[k]) for k in keys]
        spec = generator.add_bar_chart(
            chart_id="chart_metrics",
            title="核心指标概览",
            categories=keys,
            data=values,
        )
        charts.append({"type": "bar", "title": "核心指标概览", "spec": spec})

    logger.info(f"[ChartBuilder] 生成 {len(charts)} 个图表 spec")
    return charts


def _find_table(analysis, keyword: str):
    for table in analysis.tables:
        if keyword in table.title:
            return table
    return None


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_pct(value: Any) -> float:
    if value is None or value == "" or value == "-":
        return 0.0
    text = str(value).replace("%", "").strip()
    try:
        return float(text)
    except ValueError:
        return 0.0


def _parse_metric_value(value: Any) -> float:
    text = str(value).replace("%", "").strip()
    try:
        return float(text)
    except ValueError:
        return 0.0
