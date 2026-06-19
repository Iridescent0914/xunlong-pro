"""基于抽取数据点进行算法计算，产出 metrics / tables / key_findings。

按搜索来源（source_index）分组分析，不同来源的数据不混合计算。
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from .schemas import DataFinding, DataTable, RAGReference
from .search_extractor import ExtractedPoint

_LABEL_MAP = {
    "revenue_yoy": "营收同比增长",
    "net_profit_yoy": "净利润同比增长",
    "gross_margin": "毛利率",
    "debt_ratio": "资产负债率",
    "loan_growth": "贷款总额增幅",
    "asset_growth": "总资产增幅",
    "revenue_period_growth": "营收区间增幅",
    "avg_growth_rate": "平均增长率",
    "max_growth_rate": "最高增长率",
    "min_growth_rate": "最低增长率",
    "growth_rate": "增幅",
    "net_profit": "净利润",
    "total_assets": "总资产",
    "revenue": "营收",
}


def compute_analysis(
    points: List[ExtractedPoint],
    rag_refs: List[RAGReference],
    search_count: int,
) -> Tuple[Dict[str, Any], List[DataTable], List[DataFinding], str]:
    """算法主路径：按来源分组 → 分别计算 → 建表 → 生成结论。"""
    groups = _group_by_source(points)
    if not groups:
        return {}, [], [], _build_methodology(search_count, len(rag_refs), 0, rag_refs, 0)

    by_source: Dict[str, Dict[str, Any]] = {}
    tables: List[DataTable] = []
    findings: List[DataFinding] = []

    for source_index in sorted(groups.keys()):
        source_points = groups[source_index]
        source_title = source_points[0].source_title if source_points else ""
        source_metrics = _aggregate_metrics(source_points)
        source_metrics.update(_compute_derived_metrics(source_points))
        by_source[str(source_index)] = {
            "source_index": source_index,
            "source_title": source_title,
            "metrics": source_metrics,
            "point_count": len(source_points),
        }
        tables.extend(_build_source_tables(source_index, source_title, source_points))
        findings.extend(
            _build_source_findings(source_index, source_title, source_points, source_metrics, rag_refs)
        )

    metrics: Dict[str, Any] = {"by_source": by_source}
    methodology = _build_methodology(
        search_count, len(rag_refs), len(points), rag_refs, len(by_source)
    )
    return metrics, tables, findings[:20], methodology


def _group_by_source(points: List[ExtractedPoint]) -> Dict[int, List[ExtractedPoint]]:
    groups: Dict[int, List[ExtractedPoint]] = defaultdict(list)
    for p in points:
        groups[p.source_index].append(p)
    return dict(groups)


def _aggregate_metrics(points: List[ExtractedPoint]) -> Dict[str, Any]:
    """单来源内：同 metric_id 保留第一条（同正文重复匹配）。"""
    metrics: Dict[str, Any] = {}
    for p in sorted(points, key=lambda x: (x.metric_id, x.period or "")):
        key = p.metric_id
        if p.period and p.metric_id == "revenue":
            key = f"revenue_{p.period}"
        if key not in metrics:
            metrics[key] = round(p.value, 4) if p.unit == "%" else p.value
    return metrics


def _compute_derived_metrics(points: List[ExtractedPoint]) -> Dict[str, Any]:
    """单来源内的派生计算（时序增幅、百分比统计）。"""
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


def _build_source_tables(
    source_index: int,
    source_title: str,
    points: List[ExtractedPoint],
) -> List[DataTable]:
    tables: List[DataTable] = []
    short_title = source_title[:24] + ("…" if len(source_title) > 24 else "")
    label = f"[{source_index}] {short_title}"

    revenue_series = _series_by_period(
        [p for p in points if p.metric_id == "revenue" and p.period]
    )
    if revenue_series:
        rows = []
        prev: Optional[float] = None
        for period in sorted(revenue_series.keys()):
            value = revenue_series[period]
            mom = ""
            if prev and prev > 0:
                mom = f"{round((value - prev) / prev * 100, 1)}%"
            rows.append([period, value, mom])
            prev = value
        tables.append(
            DataTable(
                title=f"来源{label} · 分季度营收（万元）",
                columns=["季度", "营收（万元）", "环比"],
                rows=rows,
            )
        )

    scalar_rows = []
    for p in points:
        if p.metric_id == "revenue" and p.period:
            continue
        display = _format_value(p)
        scalar_rows.append([p.metric_label, display, p.period or "-", p.raw_text[:40]])
    if scalar_rows:
        tables.append(
            DataTable(
                title=f"来源{label} · 指标明细",
                columns=["指标", "数值", "期间", "原文片段"],
                rows=scalar_rows,
            )
        )
    return tables


def _build_source_findings(
    source_index: int,
    source_title: str,
    points: List[ExtractedPoint],
    metrics: Dict[str, Any],
    rag_refs: List[RAGReference],
) -> List[DataFinding]:
    findings: List[DataFinding] = []
    rag_hint = rag_refs[0].source if rag_refs else "RAG 口径"
    prefix = f"[来源{source_index}] "

    for metric_id, label in _LABEL_MAP.items():
        if metric_id not in metrics:
            continue
        value = metrics[metric_id]
        display = _format_metric_display(metric_id, value)
        source_point = next(
            (p for p in points if p.metric_id == metric_id or metric_id.startswith(p.metric_id)),
            None,
        )
        if source_point:
            evidence = (
                f"来源 [{source_index}] {source_title}；"
                f"抽取片段：{source_point.raw_text}；口径参考 {rag_hint}"
            )
        else:
            evidence = (
                f"来源 [{source_index}] {source_title}；"
                f"由 {metrics.get('revenue_start_period', '')}→{metrics.get('revenue_end_period', '')} "
                f"时序计算；口径参考 {rag_hint}"
            )
        findings.append(
            DataFinding(title=f"{prefix}{label}", value=display, evidence=evidence)
        )

    covered = set(_LABEL_MAP.keys())
    for p in points:
        if p.metric_id in covered and p.metric_id in metrics:
            continue
        findings.append(
            DataFinding(
                title=f"{prefix}{p.metric_label}",
                value=_format_value(p),
                evidence=f"来源 [{source_index}] {source_title}；抽取：{p.raw_text}",
            )
        )
    return findings[:6]


def _format_value(p: ExtractedPoint) -> str:
    if p.unit == "%":
        return f"{p.value * 100:.2f}%"
    return f"{p.value}{p.unit}"


def _format_metric_display(metric_id: str, value: Any) -> str:
    if isinstance(value, (int, float)) and (
        metric_id.endswith("_yoy")
        or "growth" in metric_id
        or metric_id.endswith("_rate")
        or metric_id in ("gross_margin", "debt_ratio", "loan_growth", "asset_growth")
    ):
        return f"{value * 100:.2f}%"
    return str(value)


def _build_methodology(
    search_count: int,
    rag_count: int,
    point_count: int,
    rag_refs: List[RAGReference],
    source_count: int,
) -> str:
    rag_sources = ", ".join({r.source for r in rag_refs[:3]}) or "无"
    return (
        f"算法分析路径：从 {search_count} 条搜索结果中结构化抽取 {point_count} 个数据点，"
        f"按 {source_count} 个来源分别聚合、计算同比/环比/均值，互不混合；"
        f"指标口径参考 RAG（{rag_sources}）。"
    )
