"""根据 AnalysisOutput 生成图表 spec（数据分析智能体输出流程的一部分）。"""

from typing import Any, Dict, List, Optional, Union
import json

from loguru import logger

from ..html.echarts_generator import EChartsGenerator
from .analysis_output import AnalysisOutput
from .schemas import ProcessedStats


def build_charts(analysis: Union[AnalysisOutput, ProcessedStats]) -> List[Dict[str, Any]]:
    """从算法计算产出的 metrics / tables 构建 ECharts 配置列表。

    扩展：支持折线、柱状、双轴、面积、堆叠图表。
    """
    charts: List[Dict[str, Any]] = []
    generator = EChartsGenerator()

    # 优先：任一来历的分季度营收表
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
            smooth=True,
            area=True,
        )
        charts.append({"type": "line", "title": revenue_table.title, "spec": spec})

        # 环比柱状图
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

    # 多列指标表 -> 尝试生成堆叠/双轴图
    for table in analysis.tables:
        # 如果表包含多列数值，优先用堆叠图或双轴展示
        if table.columns and len(table.columns) >= 3 and table.rows:
            cols = table.columns
            # assume first col is category
            categories = [str(r[0]) for r in table.rows]
            # 尝试解析数值列
            series_list = []
            for cidx in range(1, len(cols)):
                col_vals = []
                for r in table.rows:
                    if len(r) > cidx:
                        col_vals.append(_to_float(r[cidx]))
                    else:
                        col_vals.append(0.0)
                series_list.append({"name": cols[cidx], "data": col_vals})

            # 如果有两列数值且单位相差大，生成双轴图（简单启发式：最大值比 > 10）
            if len(series_list) >= 2:
                max_vals = [max(s["data"]) if s["data"] else 0 for s in series_list[:2]]
                if max_vals[0] and max_vals[1] and (max_vals[0] / max_vals[1] > 10 or max_vals[1] / max_vals[0] > 10):
                    spec = generator.add_dual_axis_chart(
                        chart_id=f"chart_dual_{table.title}",
                        title=table.title,
                        categories=categories,
                        bar_data=series_list[0]["data"],
                        line_data=series_list[1]["data"],
                        bar_name=series_list[0]["name"],
                        line_name=series_list[1]["name"],
                        bar_y_axis_name=series_list[0]["name"],
                        line_y_axis_name=series_list[1]["name"],
                    )
                    charts.append({"type": "dual", "title": table.title, "spec": spec})
                    return charts

                # 否则生成堆叠柱状图
                data_for_pie = []
                # build stacked series in generator by using add_bar_chart for each series and merging options
                # simpler: provide combined option via dual_axis with multiple series
                option_series = []
                for s in series_list:
                    option_series.append({"name": s["name"], "type": "bar", "data": s["data"], "stack": "总量"})

                # build simple stacked bar option using existing generator.add_bar_chart as fallback
                spec = generator.add_bar_chart(
                    chart_id=f"chart_stacked_{table.title}",
                    title=table.title,
                    categories=categories,
                    data=series_list[0]["data"],
                    y_axis_name="数值",
                )
                # attach extra series into option for downstream rendering
                try:
                    opt = spec.get("option")
                    if isinstance(opt, str):
                        opt_json = json.loads(opt)
                    else:
                        opt_json = opt
                    opt_json["series"] = option_series
                    spec["option"] = json.dumps(opt_json, ensure_ascii=False)
                except Exception:
                    pass

                charts.append({"type": "stacked", "title": table.title, "spec": spec})
                return charts

    # 分来源指标对比（metrics.by_source）
    by_source = _extract_by_source_metrics(analysis.metrics)
    if by_source and len(by_source) >= 1:
        compare = _build_source_comparison(by_source, generator)
        if compare:
            charts.append(compare)
            logger.info(f"[ChartBuilder] 生成 {len(charts)} 个图表 spec")
            return charts

    # 分来源指标明细表
    detail_tables = [t for t in analysis.tables if "指标明细" in t.title]
    if detail_tables:
        for i, table in enumerate(detail_tables[:3]):
            categories = [str(row[0]) for row in table.rows[:8]]
            values = [_parse_metric_value(row[1]) for row in table.rows[:8]]
            if categories and any(v != 0 for v in values):
                spec = generator.add_bar_chart(
                    chart_id=f"chart_source_detail_{i}",
                    title=table.title,
                    categories=categories,
                    data=values,
                )
                charts.append({"type": "bar", "title": table.title, "spec": spec})
        if charts:
            logger.info(f"[ChartBuilder] 生成 {len(charts)} 个图表 spec")
            return charts

    # fallback: flat metrics overview
    flat_metrics = _flatten_metrics(analysis.metrics)
    if flat_metrics:
        rate_keys = [
            k for k in flat_metrics
            if k.endswith("_yoy") or k.endswith("_growth") or k.endswith("_rate")
            or k in ("gross_margin", "debt_ratio", "loan_growth", "asset_growth", "avg_growth_rate")
        ]
        keys = rate_keys[:5] if rate_keys else list(flat_metrics.keys())[:5]
        values = [_to_float(flat_metrics[k]) for k in keys]
        spec = generator.add_bar_chart(
            chart_id="chart_metrics",
            title="核心指标概览",
            categories=keys,
            data=values,
            y_axis_name="数值",
        )
        charts.append({"type": "bar", "title": "核心指标概览", "spec": spec})

    logger.info(f"[ChartBuilder] 生成 {len(charts)} 个图表 spec")
    return charts


def _extract_by_source_metrics(metrics: Any) -> Dict[str, Dict[str, Any]]:
    if not isinstance(metrics, dict):
        return {}
    by_source = metrics.get("by_source")
    if not isinstance(by_source, dict):
        return {}
    return by_source


def _flatten_metrics(metrics: Any) -> Dict[str, Any]:
    if not isinstance(metrics, dict):
        return {}
    by_source = metrics.get("by_source")
    if isinstance(by_source, dict):
        flat: Dict[str, Any] = {}
        for src_key, block in by_source.items():
            if not isinstance(block, dict):
                continue
            for k, v in (block.get("metrics") or {}).items():
                flat[f"src{src_key}_{k}"] = v
        return flat
    return metrics


def _build_source_comparison(
    by_source: Dict[str, Dict[str, Any]],
    generator: EChartsGenerator,
) -> Optional[Dict[str, Any]]:
    """对各来源的同一类增长率指标做对比柱状图。"""
    compare_keys = ["revenue_yoy", "net_profit_yoy", "loan_growth", "asset_growth", "gross_margin"]
    for metric_key in compare_keys:
        categories: List[str] = []
        values: List[float] = []
        for src_key in sorted(by_source.keys(), key=lambda x: int(x) if str(x).isdigit() else 0):
            block = by_source[src_key]
            src_metrics = block.get("metrics") or {}
            if metric_key not in src_metrics:
                continue
            idx = block.get("source_index", src_key)
            title = (block.get("source_title") or "")[:16]
            categories.append(f"[{idx}] {title}")
            values.append(_to_float(src_metrics[metric_key]))
        if len(values) >= 2:
            label = metric_key.replace("_", " ")
            spec = generator.add_bar_chart(
                chart_id=f"chart_compare_{metric_key}",
                title=f"分来源对比 · {_metric_label(metric_key)}",
                categories=categories,
                data=values,
                y_axis_name="比率",
            )
            return {"type": "bar", "title": f"分来源对比 · {_metric_label(metric_key)}", "spec": spec}
    return None


def _metric_label(key: str) -> str:
    labels = {
        "revenue_yoy": "营收同比增长",
        "net_profit_yoy": "净利润同比增长",
        "gross_margin": "毛利率",
        "debt_ratio": "资产负债率",
        "loan_growth": "贷款总额增幅",
        "asset_growth": "总资产增幅",
    }
    return labels.get(key, key)


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
