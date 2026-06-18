"""成员 2：根据 ProcessedStats 生成图表 spec。"""

from typing import Any, Dict, List

from loguru import logger

from ..html.echarts_generator import EChartsGenerator
from .schemas import ProcessedStats


def build_charts(stats: ProcessedStats) -> List[Dict[str, Any]]:
    """从 metrics / tables 构建 ECharts 配置列表。"""
    charts: List[Dict[str, Any]] = []
    generator = EChartsGenerator()

    revenue_table = _find_table(stats, "分季度")
    if revenue_table:
        categories = [str(row[0]) for row in revenue_table.rows]
        values = [_to_float(row[1]) for row in revenue_table.rows]
        spec = generator.add_bar_chart(
            chart_id="chart_revenue",
            title=revenue_table.title,
            categories=categories,
            data=values,
            y_axis_name="营收（万元）",
        )
        charts.append({"type": "bar", "title": revenue_table.title, "spec": spec})
        return charts

    # 骨架 fallback：用 metrics 生成简单柱状图
    if stats.metrics:
        keys = list(stats.metrics.keys())[:5]
        values = [_to_float(stats.metrics[k]) for k in keys]
        spec = generator.add_bar_chart(
            chart_id="chart_metrics",
            title="核心指标概览",
            categories=keys,
            data=values,
        )
        charts.append({"type": "bar", "title": "核心指标概览", "spec": spec})

    logger.info(f"[ChartBuilder] 生成 {len(charts)} 个图表 spec")
    return charts


def _find_table(stats: ProcessedStats, keyword: str):
    for table in stats.tables:
        if keyword in table.title:
            return table
    return None


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
