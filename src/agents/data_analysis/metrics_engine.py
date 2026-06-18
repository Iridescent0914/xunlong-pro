"""基于抽取数据点进行算法计算，产出 metrics / tables / key_findings。"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from .schemas import DataFinding, DataTable, RAGReference
from .search_extractor import ExtractedPoint


def compute_analysis(
    points: List[ExtractedPoint],
    rag_refs: List[RAGReference],
    search_count: int,
) -> Tuple[Dict[str, Any], List[DataTable], List[DataFinding], str]:
    """算法主路径：聚合 → 计算 → 建表 → 生成结论。"""
    metrics = _aggregate_metrics(points)
    metrics.update(_compute_derived_metrics(points))
    tables = _build_tables(points)
    findings = _build_findings(points, metrics, rag_refs)
    methodology = _build_methodology(search_count, len(rag_refs), len(points), rag_refs)
    return metrics, tables, findings, methodology


def _aggregate_metrics(points: List[ExtractedPoint]) -> Dict[str, Any]:
    """同指标多点时取首个可溯源值（按来源序号优先）。"""
    metrics: Dict[str, Any] = {}
    sorted_points = sorted(points, key=lambda p: (p.metric_id, p.source_index))
    for p in sorted_points:
        if p.metric_id not in metrics:
            if p.unit == "%":
                metrics[p.metric_id] = round(p.value, 4)
            else:
                metrics[p.metric_id] = p.value
    return metrics


def _compute_derived_metrics(points: List[ExtractedPoint]) -> Dict[str, Any]:
    """对时序营收点计算环比/趋势统计。"""
    derived: Dict[str, Any] = {}
    revenue_series = _series_by_period(
        [p for p in points if p.metric_id == "revenue" and p.period]
    )
    if len(revenue_series) >= 2:
        periods = sorted(revenue_series.keys())
        first, last = periods[0], periods[-1]
        v0, v1 = revenue_series[first], revenue_series[last]
        if v0:
            derived["revenue_period_growth"] = round((v1 - v0) / v0, 4)
            derived["revenue_start_period"] = first
            derived["revenue_end_period"] = last

    pct_points = [p for p in points if p.unit == "%"]
    if pct_points:
        values = [p.value for p in pct_points]
        derived["avg_growth_rate"] = round(sum(values) / len(values), 4)
        derived["max_growth_rate"] = round(max(values), 4)
        derived["min_growth_rate"] = round(min(values), 4)
    return derived


def _series_by_period(points: List[ExtractedPoint]) -> Dict[str, float]:
    series: Dict[str, float] = {}
    for p in points:
        if p.period and p.period not in series:
            series[p.period] = p.value
    return series


def _build_tables(points: List[ExtractedPoint]) -> List[DataTable]:
    tables: List[DataTable] = []

    revenue_series = _series_by_period(
        [p for p in points if p.metric_id == "revenue" and p.period]
    )
    if revenue_series:
        rows = []
        prev: Optional[float] = None
        for period in sorted(revenue_series.keys()):
            value = revenue_series[period]
            yoy = ""
            if prev and prev > 0:
                yoy = f"{round((value - prev) / prev * 100, 1)}%"
            rows.append([period, value, yoy])
            prev = value
        tables.append(
            DataTable(
                title="分季度营收（万元）",
                columns=["季度", "营收（万元）", "环比"],
                rows=rows,
            )
        )

    scalar_rows = []
    for p in points:
        if p.metric_id == "revenue" and p.period:
            continue
        display = f"{p.value * 100:.2f}%" if p.unit == "%" else f"{p.value}{p.unit}"
        scalar_rows.append(
            [p.metric_label, display, p.period or "-", f"[{p.source_index}] {p.source_title[:30]}"]
        )
    if scalar_rows:
        tables.append(
            DataTable(
                title="抽取指标明细",
                columns=["指标", "数值", "期间", "来源"],
                rows=scalar_rows[:20],
            )
        )
    return tables


def _build_findings(
    points: List[ExtractedPoint],
    metrics: Dict[str, Any],
    rag_refs: List[RAGReference],
) -> List[DataFinding]:
    findings: List[DataFinding] = []
    rag_hint = rag_refs[0].source if rag_refs else "RAG 口径"

    label_map = {
        "revenue_yoy": "营收同比增长",
        "net_profit_yoy": "净利润同比增长",
        "gross_margin": "毛利率",
        "debt_ratio": "资产负债率",
        "loan_growth": "贷款总额增幅",
        "asset_growth": "总资产增幅",
        "revenue_period_growth": "营收区间增幅",
        "avg_growth_rate": "平均增长率",
    }

    for metric_id, label in label_map.items():
        if metric_id not in metrics:
            continue
        value = metrics[metric_id]
        display = f"{value * 100:.2f}%" if metric_id.endswith("_yoy") or "growth" in metric_id or metric_id.endswith("_rate") or metric_id in ("gross_margin", "debt_ratio", "loan_growth", "asset_growth") else str(value)
        source_point = next((p for p in points if p.metric_id == metric_id.split("_period")[0] or p.metric_id == metric_id), None)
        if source_point:
            evidence = f"算法抽取自 [{source_point.source_index}] {source_point.source_title}；口径参考 {rag_hint}"
        else:
            evidence = f"算法由 {metrics.get('revenue_start_period', '')}→{metrics.get('revenue_end_period', '')} 时序计算；口径参考 {rag_hint}"
        findings.append(DataFinding(title=label, value=display, evidence=evidence))

    for p in points[:5]:
        if p.metric_id in metrics:
            continue
        display = f"{p.value * 100:.2f}%" if p.unit == "%" else f"{p.value}{p.unit}"
        findings.append(
            DataFinding(
                title=p.metric_label,
                value=display,
                evidence=f"正则抽取：{p.raw_text}；来源 [{p.source_index}] {p.source_title}",
            )
        )
    return findings[:8]


def _build_methodology(
    search_count: int,
    rag_count: int,
    point_count: int,
    rag_refs: List[RAGReference],
) -> str:
    rag_sources = ", ".join({r.source for r in rag_refs[:3]}) or "无"
    return (
        f"算法分析路径：从 {search_count} 条搜索结果中结构化抽取 {point_count} 个数据点，"
        f"经聚合与同比/环比/均值计算得到 metrics 与 tables；"
        f"指标口径参考 RAG（{rag_sources}）。"
    )
