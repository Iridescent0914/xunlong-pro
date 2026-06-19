"""Report rendering helpers for file-based data analysis."""

import json
from typing import Dict, Any


def build_file_analysis_markdown(section: Dict[str, Any]) -> str:
    title = section.get("title", "数据分析报告")
    body = section.get("content", "")
    return f"# {title}\n\n{body}"


def build_file_analysis_html(section: Dict[str, Any], report_title: str = "数据分析报告") -> str:
    charts = section.get("charts", []) or []
    html_parts = [
        "<!DOCTYPE html>",
        "<html lang=\"zh\">",
        "<head>",
        "<meta charset=\"UTF-8\" />",
        f"<title>{report_title}</title>",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />",
        "<script src=\"https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js\"></script>",
        "<style>",
        "body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.7; margin: 0; color: #222; background: #eef2f7; }",
        "* { box-sizing: border-box; }",
        ".page-container { width: min(1200px, 100%); margin: 0 auto; padding: 24px; }",
        ".report-header { background: linear-gradient(135deg, #5A6B5C 20%, #0ea5e9 80%); color: #fff; padding: 28px 32px; border-radius: 24px; box-shadow: 0 20px 60px rgba(15, 23, 42, 0.12); margin-bottom: 24px; }",
        ".report-header h1 { margin: 0 0 12px; font-size: 2.2rem; letter-spacing: 0.01em; }",
        ".report-header p { margin: 0; color: #dbeafe; font-size: 1rem; max-width: 860px; }",
        ".section-card { background: #fff; border-radius: 24px; padding: 24px; margin-bottom: 24px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08); }",
        ".section-card h2, .section-card h3 { color: #111827; margin-top: 0; }",
        ".section-card p { color: #475569; }",
        "table { width: 100%; border-collapse: collapse; margin-bottom: 24px; box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.16); }",
        "th, td { border: none; padding: 14px 12px; text-align: left; }",
        "th { background: #f8fafc; color: #0f172a; font-weight: 700; border-bottom: 2px solid #e2e8f0; }",
        "tr:nth-child(even) td { background: #f8fafc; }",
        "tr:hover td { background: #eef2ff; }",
        ".chart-container { width: 100%; min-height: 420px; margin: 24px 0; border-radius: 20px; overflow: hidden; background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%); box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08); }",
        ".chart-box { padding: 18px 20px 0; }",
        ".chart-box > div { width: 100%; height: 360px; }",
        ".report-table { overflow-x: auto; max-width: 100%; }",
        ".section-card table { table-layout: fixed; width: 100%; }",
        ".section-card th, .section-card td { word-break: break-word; white-space: normal; }",
        ".section-card td { max-width: 220px; overflow: hidden; text-overflow: ellipsis; }",
        ".chart-title { margin: 0 0 10px; font-size: 1.05rem; color: #1e293b; }",
        ".chart-container canvas, .chart-container svg { width: 100% !important; height: 100% !important; }",
        "/* table controls */",
        ".table-controls { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; }",
        ".table-controls .btn { background: #5A6B5C; color: #fff; border: none; padding: 6px 10px; border-radius: 8px; cursor: pointer; font-size: 0.9rem; }",
        ".table-controls .panel { display: none; background: rgba(255,255,255,0.98); border-radius: 8px; padding: 8px; box-shadow: 0 8px 24px rgba(2,6,23,0.08); }",
        ".table-controls .panel.show { display: block; position: absolute; z-index: 40; }",
        ".report-table { position: relative; margin-bottom: 18px; }",
        "/* nicer headings and key points */",
        ".section-card h2 { display: flex; align-items: center; gap: 12px; font-size: 1.35rem; border-left: 4px solid #0ea5e9; padding-left: 12px; margin-top: 6px; }",
        ".section-card h3 { color: #064e3b; margin-bottom: 6px; }",
        ".key-badge { display: inline-block; background: #fef3c7; color: #92400e; padding: 4px 8px; border-radius: 999px; font-weight: 700; margin-right: 8px; font-size: 0.85rem; }",
        ".section-card ul { padding-left: 1.1rem; }",
        "@media (max-width: 900px) { .page-container { padding: 16px; } .report-header h1 { font-size: 1.8rem; } }",
        "</style>",
        "</head>",
        "<body>",
        "<div class=\"page-container\">",
        "<div class=\"report-header\">",
        f"<h1>{report_title}</h1>",
        "<p>自动生成数据分析报告，包含关键指标、样本摘要、图表与结构化结论。可直接用于展示或导出。</p>",
        "</div>",
        "<div class=\"section-card\">",
        section.get("content_html", ""),
        "</div>",
    ]

    for i, chart in enumerate(charts):
        chart_id = chart.get("id") or f"chart_{i}"
        # ensure id is safe
        chart_id = str(chart_id).replace(' ', '_')
        html_parts.append(f'<div class="chart-container"><div class="chart-box"><h3 class="chart-title">{chart.get("title", "图表")}</h3><div id="{chart_id}"></div></div></div>')

    html_parts.append("<script>")
    html_parts.append("var __generated_charts = [];\n")
    for i, chart in enumerate(charts):
        chart_id = chart.get("id") or f"chart_{i}"
        chart_id = str(chart_id).replace(' ', '_')
        option = chart.get("option", {})
        if isinstance(option, str):
            try:
                option = json.loads(option)
            except Exception:
                option = {}
        try:
            option_json = json.dumps(option, ensure_ascii=False)
        except Exception:
            # fallback to empty option if serialization fails
            option_json = "{}"
        varname = f"chart_inst_{i}"
        safe_id = chart_id.replace("'", "\\'")
        html_parts.append(
            f"var {varname} = echarts.init(document.getElementById('{safe_id}')); {varname}.setOption({option_json}); __generated_charts.push({varname});"
        )
    # add resize handler
    html_parts.append("window.addEventListener('resize', function(){ __generated_charts.forEach(function(c){ try{ c.resize(); }catch(e){} }); });")

    # table controls: add tooltips, colgroup widths and a small column visibility panel
    html_parts.append("\n(function(){\n  function processTables(){\n    var tables = document.querySelectorAll('.section-card table');\n    tables.forEach(function(table, tIdx){\n      // wrap if not wrapped\n      var wrap = table.closest('.report-table');\n      if(!wrap){\n        var container = document.createElement('div'); container.className = 'report-table';\n        table.parentNode.insertBefore(container, table);\n        container.appendChild(table);\n      }\n      // compute headers\n      var headers = table.querySelectorAll('thead th');\n      var colCount = headers.length || (table.rows[0] ? table.rows[0].cells.length : 0);\n      // add colgroup widths if missing\n      if(!table.querySelector('colgroup')){\n        var colgroup = document.createElement('colgroup');\n        var widths = [];\n        if(colCount <= 4){\n          for(var i=0;i<colCount;i++) widths.push((100/colCount).toFixed(2)+'%');\n        } else {\n          widths.push('18%');\n          var remain = 82;\n          var mid = colCount-2;\n          for(var i=0;i<mid;i++) widths.push((remain/mid).toFixed(2)+'%');\n          widths.push('12%');\n        }\n        for(var i=0;i<colCount;i++){ var c = document.createElement('col'); c.style.width = widths[i] || 'auto'; colgroup.appendChild(c); }\n        table.insertBefore(colgroup, table.firstChild);\n      }\n      // add title tooltips for long cells\n      Array.from(table.querySelectorAll('td')).forEach(function(td){ var txt = td.textContent || ''; if(txt.length>35) td.setAttribute('title', txt.trim()); });\n      // add column controls panel\n      var controls = document.createElement('div'); controls.className = 'table-controls';\n      var btn = document.createElement('button'); btn.className = 'btn'; btn.innerText = '列显示';\n      var panel = document.createElement('div'); panel.className = 'panel';\n      panel.style.display = 'none';\n      headers.forEach(function(h, idx){ var label = h.textContent || ('列'+(idx+1)); var cb = document.createElement('label'); cb.style.display='block'; cb.style.margin='4px 8px'; var input = document.createElement('input'); input.type='checkbox'; input.checked = true; input.dataset.col = idx; input.style.marginRight='6px'; input.addEventListener('change', function(e){ toggleColumn(table, parseInt(this.dataset.col,10), this.checked); }); cb.appendChild(input); cb.appendChild(document.createTextNode(label)); panel.appendChild(cb); });\n      btn.addEventListener('click', function(e){ panel.style.display = panel.style.display === 'block' ? 'none' : 'block'; });\n      controls.appendChild(btn); controls.appendChild(panel);\n      table.parentNode.insertBefore(controls, table);\n    });\n  }\n  function toggleColumn(table, colIndex, show){\n    var rows = table.rows;\n    for(var r=0;r<rows.length;r++){ var cell = rows[r].cells[colIndex]; if(cell) cell.style.display = show ? '' : 'none'; }\n  }\n  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', processTables); else processTables();\n})();")
    html_parts.append("</script>")
    html_parts.append("</body>")
    html_parts.append("</html>")
    return "\n".join(html_parts)
