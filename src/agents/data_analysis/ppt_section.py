"""将 data_analysis_results 渲染为 PPT 幻灯片（确定性 HTML，不经过 LLM）。"""

import html
import json
from typing import Any, Dict, List, Optional

from .data_analysis_context import has_usable_analysis
from .report_section import (
    _collect_charts,
    _cited_search_refs,
    _render_table,
)


def build_data_analysis_slides(
    data: Optional[Dict[str, Any]],
    *,
    section_index: int = 0,
    colors: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """构建金融数据分析模块的 PPT 幻灯片数据（html_content 模式）。"""
    if not has_usable_analysis(data):
        return []

    colors = colors or {}
    primary = colors.get("primary", "#1a237e")
    accent = colors.get("accent", "#2E8B57")
    source_blocks = data.get("source_blocks") or []
    charts = _collect_charts(data, source_blocks, section_index)

    slides: List[Dict[str, Any]] = []

    result_html = _build_analysis_result_html(data, primary, accent)
    if result_html:
        slides.append(_slide_entry("金融数据分析 · 分析结果", result_html))

    for chart in charts:
        chart_html = _build_chart_html(chart, primary, accent)
        if chart_html:
            title = chart.get("title") or "金融数据分析 · 图表"
            slides.append(_slide_entry(title, chart_html))

    sources_html = _build_sources_html(data, primary, accent)
    if sources_html:
        slides.append(_slide_entry("金融数据分析 · 分析来源", sources_html))

    return slides


def _slide_entry(title: str, html_content: str) -> Dict[str, Any]:
    return {
        "type": "content",
        "title": title,
        "template": "slide_content.html",
        "html_content": html_content,
        "is_data_analysis": True,
    }


def _build_slide_shell(title: str, body: str, primary: str, accent: str) -> str:
    return f"""<div style="width:100%;height:100%;padding:48px 64px 96px 64px;
background:linear-gradient(135deg,#f8fafc 0%,#eef2ff 100%);overflow:auto;box-sizing:border-box">
  <div style="border-left:6px solid {accent};padding-left:20px;margin-bottom:28px">
    <h1 style="font-size:2rem;font-weight:700;color:{primary};margin:0">{html.escape(title)}</h1>
  </div>
  {body}
</div>"""


def _build_analysis_result_html(
    data: Dict[str, Any],
    primary: str,
    accent: str,
) -> str:
    parts: List[str] = []

    methodology = (data.get("methodology") or "").strip()
    if methodology:
        parts.append(
            f'<p style="color:#555;font-size:0.95rem;margin-bottom:16px">'
            f'<strong>分析口径：</strong>{html.escape(methodology)}</p>'
        )

    analysis_table = data.get("analysis_table")
    if isinstance(analysis_table, dict) and analysis_table.get("rows"):
        parts.append(_markdown_table_to_html(analysis_table))
        conclusion = (data.get("analysis_conclusion") or "").strip()
        if conclusion:
            parts.append(_conclusion_block(conclusion, accent))
    elif source_blocks:
        for block in source_blocks:
            table = block.get("table") or {}
            src_idx = block.get("source_index", "?")
            src_title = block.get("source_title", "")
            parts.append(
                f'<p style="font-weight:600;color:{primary};margin:12px 0 8px">'
                f'来源 [{src_idx}] {html.escape(str(src_title))}</p>'
            )
            parts.append(_markdown_table_to_html(table))
            conclusion = (block.get("conclusion") or "").strip()
            if conclusion:
                parts.append(_conclusion_block(conclusion, accent))
    else:
        legacy_md = "\n".join(_render_table(t) for t in (data.get("tables") or []) if t)
        if legacy_md.strip():
            parts.append(_markdown_table_to_html_from_md(legacy_md))
        conclusion_parts = []
        for item in data.get("key_findings") or []:
            if isinstance(item, dict):
                conclusion_parts.append(f"{item.get('title', '')}：{item.get('value', '')}")
            else:
                conclusion_parts.append(str(item))
        if conclusion_parts:
            parts.append(_conclusion_block("\n".join(conclusion_parts), accent))

    if not parts:
        return ""

    body = "\n".join(parts)
    return _build_slide_shell("分析结果", body, primary, accent)


def _build_chart_html(chart: Dict[str, Any], primary: str, accent: str) -> str:
    option = chart.get("option") or {}
    if not option:
        return ""

    chart_title = chart.get("title") or "分析图表"
    option_json = json.dumps(option, ensure_ascii=False)
    chart_id = chart.get("id") or "da_ppt_chart"

    body = f"""
<div style="background:rgba(255,255,255,0.92);border-radius:12px;padding:20px;
box-shadow:0 4px 16px rgba(0,0,0,0.08);height:calc(100% - 80px)">
  <div id="{html.escape(chart_id)}" style="width:100%;height:100%;min-height:420px"></div>
</div>
<script>
(function() {{
  var dom = document.getElementById({json.dumps(chart_id)});
  if (!dom || typeof echarts === 'undefined') return;
  var chart = echarts.init(dom);
  chart.setOption({option_json});
  window.addEventListener('resize', function() {{ chart.resize(); }});
}})();
</script>"""
    return _build_slide_shell(chart_title, body, primary, accent)


def _build_sources_html(data: Dict[str, Any], primary: str, accent: str) -> str:
    cited_refs = _cited_search_refs(data)
    if not cited_refs:
        return ""

    items: List[str] = []
    for ref in cited_refs:
        idx = ref.get("_index", "")
        title = ref.get("title", "未知来源")
        url = ref.get("url", "")
        prefix = f"[{idx}] " if idx else ""
        if url:
            safe_url = html.escape(url)
            safe_title = html.escape(title)
            items.append(
                f'<li style="margin-bottom:14px;font-size:1.05rem;line-height:1.5">'
                f'{prefix}<a href="{safe_url}" style="color:{accent};text-decoration:none" '
                f'target="_blank" rel="noopener">{safe_title}</a></li>'
            )
        else:
            items.append(
                f'<li style="margin-bottom:14px;font-size:1.05rem;line-height:1.5">'
                f'{prefix}{html.escape(title)}</li>'
            )

    body = f'<ul style="list-style:none;padding:0;margin:0;color:#333">{"".join(items)}</ul>'
    return _build_slide_shell("分析来源", body, primary, accent)


def _conclusion_block(text: str, accent: str) -> str:
    return (
        f'<div style="margin-top:20px;padding:16px 20px;background:rgba(255,255,255,0.9);'
        f'border-radius:10px;border-left:4px solid {accent}">'
        f'<p style="font-weight:600;color:#333;margin:0 0 8px">结论</p>'
        f'<p style="color:#444;margin:0;line-height:1.6;white-space:pre-wrap">'
        f'{html.escape(text)}</p></div>'
    )


def _markdown_table_to_html(table: Dict[str, Any]) -> str:
    lines = _render_table(table)
    return _markdown_table_to_html_from_md("\n".join(lines))


def _markdown_table_to_html_from_md(md: str) -> str:
    rows: List[List[str]] = []
    for line in md.strip().splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= {"-"} for c in cells):
            continue
        rows.append(cells)

    if not rows:
        return ""

    header = rows[0]
    body_rows = rows[1:]
    thead = "<tr>" + "".join(
        f'<th style="padding:10px 12px;background:#1a237e;color:#fff;text-align:left;'
        f'font-size:0.9rem">{html.escape(c)}</th>' for c in header
    ) + "</tr>"
    tbody = ""
    for i, row in enumerate(body_rows):
        bg = "#fff" if i % 2 == 0 else "#f5f7fb"
        cells = row + [""] * (len(header) - len(row))
        tbody += "<tr>" + "".join(
            f'<td style="padding:10px 12px;background:{bg};font-size:0.88rem;'
            f'border-bottom:1px solid #e8ecf4">{html.escape(str(c))}</td>'
            for c in cells[: len(header)]
        ) + "</tr>"

    return (
        '<div style="overflow-x:auto;margin-bottom:12px">'
        '<table style="width:100%;border-collapse:collapse;border-radius:8px;overflow:hidden">'
        f"<thead>{thead}</thead><tbody>{tbody}</tbody></table></div>"
    )
