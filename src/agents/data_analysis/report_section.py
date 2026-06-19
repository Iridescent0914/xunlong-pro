"""将 data_analysis_results 渲染为报告中的独立「金融数据分析」模块。"""

import json
import re
from typing import Any, Dict, List, Optional, Set

try:
    import markdown as md_lib
except ImportError:  # pragma: no cover
    md_lib = None

from .schemas import DataFinding, DataTable

_SOURCE_INDEX_RE = re.compile(r"\[(\d+)\]")


def build_data_analysis_section(
    data: Dict[str, Any],
    section_index: int,
    main_sections: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """把数据分析智能体输出转为可插入 FINAL_REPORT 的章节。"""
    if not data or data.get("status") != "success":
        return None

    source_blocks = data.get("source_blocks") or []
    charts = _collect_charts(data, source_blocks, section_index)
    markdown = _build_markdown(data, main_sections=main_sections or [], section_index=section_index)
    content_html = _render_html(markdown)
    cited_refs = _cited_search_refs(data)

    return {
        "section_id": "data_analysis",
        "title": "金融数据分析",
        "anchor": "金融数据分析",
        "content": markdown,
        "content_html": content_html,
        "charts": charts,
        "confidence": 1.0,
        "sources_used": [
            ref.get("url", ref.get("title", ""))
            for ref in cited_refs
            if ref.get("url") or ref.get("title")
        ],
        "level": 2,
        "is_data_analysis": True,
    }


def _collect_charts(
    data: Dict[str, Any],
    source_blocks: List[Dict[str, Any]],
    section_index: int,
) -> List[Dict[str, Any]]:
    if data.get("charts"):
        return _normalize_charts(data.get("charts", []), section_index)
    if source_blocks:
        charts = [b["chart"] for b in source_blocks if b.get("chart")]
        return _normalize_charts(charts, section_index)
    return []


def _render_unified_analysis_result(
    table: Dict[str, Any],
    conclusion: str,
    section_index: int,
) -> List[str]:
    parts = ["### 分析结果\n"]
    parts.extend(_render_table(table))
    parts.append(f'<div class="chart-wrapper" id="chart_{section_index}_0"></div>\n')
    parts.append(f"*图表：{table.get('title', '数值可视化')}*\n")
    parts.append("**结论**\n")
    parts.append(conclusion or "暂无结论。")
    parts.append("")
    return parts


def _build_markdown(
    data: Dict[str, Any],
    main_sections: Optional[List[Dict[str, Any]]] = None,
    section_index: int = 0,
) -> str:
    parts: List[str] = []

    methodology = data.get("methodology", "")
    if methodology:
        parts.append(
            "本节内容由**金融数据分析智能体**读取网页搜索结果，"
            "由 LLM 从正文中抽取数值并整理为下表。"
        )
        parts.append(f"\n**分析口径**：{methodology}\n")

    analysis_table = data.get("analysis_table")
    analysis_conclusion = (data.get("analysis_conclusion") or "").strip()

    if analysis_table and analysis_table.get("rows"):
        parts.extend(_render_unified_analysis_result(
            analysis_table, analysis_conclusion, section_index
        ))
    elif data.get("source_blocks"):
        parts.extend(_render_analysis_charts_section(
            data.get("source_blocks") or [], section_index
        ))
    else:
        parts.extend(_render_legacy_analysis_body(data))

    parts.extend(_render_analysis_sources_section(data))
    return "\n".join(parts)


def _render_analysis_charts_section(
    source_blocks: List[Dict[str, Any]],
    section_index: int,
) -> List[str]:
    parts = ["### 分析图表\n"]
    for j, block in enumerate(source_blocks):
        src_idx = block.get("source_index", "?")
        title = block.get("source_title", "")
        parts.append(f"#### 来源 [{src_idx}] {title}\n")

        table = block.get("table") or {}
        parts.extend(_render_table(table))

        chart = block.get("chart") or {}
        if chart:
            chart_id = f"chart_{section_index}_{j}"
            parts.append(f'<div class="chart-wrapper" id="{chart_id}"></div>\n')
            chart_title = chart.get("title") or "数据可视化"
            parts.append(f"*图表：{chart_title}*\n")

        conclusion = (block.get("conclusion") or "").strip()
        parts.append("**结论**\n")
        parts.append(conclusion or "暂无结论。")
        parts.append("")
    return parts


def _render_analysis_sources_section(data: Dict[str, Any]) -> List[str]:
    parts = ["### 分析来源\n"]
    cited_refs = _cited_search_refs(data)
    if cited_refs:
        for ref in cited_refs:
            idx = ref.get("_index", "")
            title = ref.get("title", "未知来源")
            url = ref.get("url", "")
            prefix = f"[{idx}] " if idx else ""
            if url:
                parts.append(f"- {prefix}[{title}]({url})")
            else:
                parts.append(f"- {prefix}{title}")
        parts.append("")
    else:
        parts.append("暂无引用来源。\n")
    return parts


def _cited_search_refs(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """仅返回分析结果表格「来源」列中出现过的搜索结果。"""
    search_refs = data.get("search_refs") or []
    if not search_refs:
        return []

    indices = _cited_source_indices(data)
    if not indices:
        return []

    cited: List[Dict[str, Any]] = []
    for idx in sorted(indices):
        if 1 <= idx <= len(search_refs):
            ref = dict(search_refs[idx - 1])
            ref["_index"] = idx
            cited.append(ref)
    return cited


def _cited_source_indices(data: Dict[str, Any]) -> Set[int]:
    indices: Set[int] = set()

    analysis_table = data.get("analysis_table")
    if isinstance(analysis_table, dict):
        indices.update(_indices_from_table(analysis_table))

    for block in data.get("source_blocks") or []:
        table = block.get("table")
        if isinstance(table, dict):
            table_indices = _indices_from_table(table)
            if table_indices:
                indices.update(table_indices)
            elif block.get("source_index") is not None:
                try:
                    indices.add(int(block["source_index"]))
                except (TypeError, ValueError):
                    pass

    for table in data.get("tables") or []:
        if isinstance(table, dict):
            indices.update(_indices_from_table(table))

    return indices


def _indices_from_table(table: Dict[str, Any]) -> Set[int]:
    columns = [str(c) for c in (table.get("columns") or [])]
    rows = table.get("rows") or []
    if not columns or not rows:
        return set()

    source_col = next(
        (i for i, col in enumerate(columns) if "来源" in col),
        None,
    )
    if source_col is None:
        return set()

    indices: Set[int] = set()
    for row in rows:
        if source_col >= len(row):
            continue
        cell = str(row[source_col])
        for match in _SOURCE_INDEX_RE.finditer(cell):
            indices.add(int(match.group(1)))
    return indices


def _render_legacy_analysis_body(data: Dict[str, Any]) -> List[str]:
    """无 source_blocks 时回退到旧版平铺结构。"""
    parts: List[str] = []
    metrics = data.get("metrics", {})
    if metrics:
        by_source = metrics.get("by_source") if isinstance(metrics, dict) else None
        parts.append("### 分析图表\n")
        if by_source:
            for src_key in sorted(by_source.keys(), key=lambda x: int(x) if str(x).isdigit() else x):
                block = by_source[src_key]
                title = block.get("source_title", "")
                src_idx = block.get("source_index", src_key)
                parts.append(f"#### 来源 [{src_idx}] {title}\n")
                src_metrics = block.get("metrics") or {}
                if src_metrics:
                    parts.append("| 指标 | 数值 |")
                    parts.append("| --- | --- |")
                    for key, value in src_metrics.items():
                        parts.append(f"| {_metric_label(key)} | {_format_metric_value(key, value)} |")
                    parts.append("")
        else:
            parts.append("| 指标 | 数值 |")
            parts.append("| --- | --- |")
            for key, value in metrics.items():
                if key == "by_source":
                    continue
                parts.append(f"| {_metric_label(key)} | {_format_metric_value(key, value)} |")
            parts.append("")

    for table in data.get("tables", []):
        if table.get("title") == "数值列相关性矩阵":
            continue
        parts.extend(_render_table(table))

    findings: List[DataFinding] = []
    for item in data.get("key_findings", []):
        if isinstance(item, dict):
            findings.append(DataFinding(**item))
        else:
            findings.append(item)
    if findings:
        parts.append("**结论**\n")
        for i, finding in enumerate(findings, 1):
            parts.append(f"{i}. **{finding.title}**：{finding.value}")
        parts.append("")

    charts = data.get("charts", [])
    if charts:
        for chart in charts:
            parts.append(f"- {chart.get('title', '图表')}（{chart.get('type', 'chart')}）")
        parts.append("")
    return parts


def _render_table(table: Dict[str, Any]) -> List[str]:
    parts: List[str] = []
    if not table:
        return parts
    title = table.get("title")
    if title:
        parts.append(f"**{title}**\n")
    columns = table.get("columns", [])
    rows = table.get("rows", [])
    if columns:
        parts.append("| " + " | ".join(str(c) for c in columns) + " |")
        parts.append("| " + " | ".join("---" for _ in columns) + " |")
        for row in rows:
            parts.append("| " + " | ".join(str(cell) for cell in row) + " |")
        parts.append("")
    return parts


def _normalize_charts(charts: List[Dict[str, Any]], section_index: int) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for j, chart in enumerate(charts):
        spec = chart.get("spec") or {}
        chart_id = spec.get("id") or chart.get("id") or f"chart_da_{j}"
        option = spec.get("option") if spec else chart.get("option")

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
        if spec:
            spec_copy = dict(spec)
            spec_copy["id"] = chart_id
            normalized[-1]["spec"] = spec_copy
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
