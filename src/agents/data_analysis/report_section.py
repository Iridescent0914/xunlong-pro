"""将 data_analysis_results 渲染为报告中的独立「金融数据分析」模块。"""

import json
from typing import Any, Dict, List, Optional

try:
    import markdown as md_lib
except ImportError:  # pragma: no cover
    md_lib = None

from .schemas import DataFinding


def build_data_analysis_section(
    data: Dict[str, Any],
    section_index: int,
) -> Optional[Dict[str, Any]]:
    """把数据分析智能体输出转为可插入 FINAL_REPORT 的章节。"""
    if not data or data.get("status") != "success":
        return None

    markdown = _build_markdown(data)
    charts = _normalize_charts(data.get("charts", []), section_index)
    content_html = _render_html(markdown)

    return {
        "section_id": "data_analysis",
        "title": "金融数据分析",
        "content": markdown,
        "content_html": content_html,
        "charts": charts,
        "confidence": 1.0,
        "sources_used": [
            ref.get("url", ref.get("title", ""))
            for ref in data.get("search_refs", [])
            if ref.get("url") or ref.get("title")
        ],
        "level": 2,
        "is_data_analysis": True,
    }


def _build_markdown(data: Dict[str, Any]) -> str:
    parts: List[str] = []

    methodology = data.get("methodology", "")
    if methodology:
        parts.append("本节内容由**金融数据分析智能体**基于网页搜索结果与 RAG 指标口径，经算法抽取与计算生成。")
        parts.append(f"\n**分析口径**：{methodology}\n")

    analysis_summary = data.get("analysis_summary")
    if analysis_summary:
        parts.append(analysis_summary)
        parts.append("")

    metrics = data.get("metrics", {})
    if metrics:
        parts.append("### 核心指标\n")
        parts.append("| 指标 | 数值 |")
        parts.append("| --- | --- |")
        for key, value in metrics.items():
            display = _format_metric_value(key, value)
            parts.append(f"| {_metric_label(key)} | {display} |")
        parts.append("")

    for table in data.get("tables", []):
        if table.get("title") == "数值列相关性矩阵":
            continue
        parts.append(f"### {table.get('title', '数据表')}\n")
        columns = table.get("columns", [])
        rows = table.get("rows", [])
        if columns:
            parts.append("| " + " | ".join(str(c) for c in columns) + " |")
            parts.append("| " + " | ".join("---" for _ in columns) + " |")
            for row in rows:
                parts.append("| " + " | ".join(str(cell) for cell in row) + " |")
            parts.append("")

    findings: List[DataFinding] = []
    for item in data.get("key_findings", []):
        if isinstance(item, dict):
            findings.append(DataFinding(**item))
        else:
            findings.append(item)

    if findings:
        parts.append("### 分析结论\n")
        for i, finding in enumerate(findings, 1):
            parts.append(f"{i}. **{finding.title}**：{finding.value}")
            if finding.evidence:
                parts.append(f"   - 依据：{finding.evidence}")
        parts.append("")

    charts = data.get("charts", [])
    if charts:
        parts.append("### 分析图表\n")
        for chart in charts:
            parts.append(f"- {chart.get('title', '图表')}（{chart.get('type', 'chart')}）")
        parts.append("")

    search_refs = data.get("search_refs", [])
    if search_refs:
        parts.append("### 分析引用来源\n")
        for i, ref in enumerate(search_refs, 1):
            title = ref.get("title", "未知来源")
            url = ref.get("url", "")
            if url:
                parts.append(f"{i}. [{title}]({url})")
            else:
                parts.append(f"{i}. {title}")
        parts.append("")

    rag_refs = data.get("rag_refs", [])
    if rag_refs:
        parts.append("### RAG 口径参考\n")
        for ref in rag_refs[:3]:
            source = ref.get("source", "")
            content = ref.get("content", "")
            parts.append(f"- **{source}**：{content}")
        parts.append("")

    return "\n".join(parts)


def _normalize_charts(charts: List[Dict[str, Any]], section_index: int) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for j, chart in enumerate(charts):
        # support two shapes: {"spec": {"id":..., "option":...}, ...} or {"id":..., "option":..., ...}
        spec = chart.get("spec") or {}
        chart_id = None
        option = None

        if spec:
            chart_id = spec.get("id")
            option = spec.get("option")
        else:
            chart_id = chart.get("id")
            option = chart.get("option")

        chart_id = chart_id or f"chart_da_{j}"
        chart_id = f"chart_{section_index}_{j}"

        if isinstance(option, str):
            try:
                option = json.loads(option)
            except json.JSONDecodeError:
                option = {}

        if option is None:
            option = {}

        normalized.append({
            "id": chart_id,
            "title": chart.get("title") or spec.get("title", "分析图表"),
            "option": option,
            "type": chart.get("type", "bar"),
        })
    return normalized


def _render_html(markdown_text: str) -> str:
    if md_lib:
        return md_lib.markdown(
            markdown_text,
            extensions=["extra", "tables", "nl2br"],
        )
    return "<p>" + markdown_text.replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"


def _metric_label(key: str) -> str:
    labels = {
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
        "net_profit": "净利润",
        "total_assets": "总资产",
        "revenue": "营收",
    }
    return labels.get(key, key)


def _format_metric_value(key: str, value: Any) -> str:
    if isinstance(value, (int, float)):
        rate_keys = {
            "revenue_yoy", "net_profit_yoy", "gross_margin", "debt_ratio",
            "loan_growth", "asset_growth", "revenue_period_growth",
            "avg_growth_rate", "max_growth_rate", "min_growth_rate", "growth_rate",
        }
        if key in rate_keys or key.endswith("_yoy") or key.endswith("_rate") or "growth" in key:
            return f"{value * 100:.2f}%"
    return str(value)
