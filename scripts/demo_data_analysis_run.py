"""Demo: 使用 fixtures/mock_search.json 运行 LLM 数据分析并生成 Markdown/HTML 报告

用法:
    python scripts/demo_data_analysis_run.py

输出:
    output/demo_report.md
    output/demo_report.html
"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'fixtures'
OUTDIR = ROOT / 'output'
OUTDIR.mkdir(exist_ok=True)

sys.path.insert(0, str(ROOT))

from src.agents.data_analysis.data_analysis_agent import DataAnalysisAgent
from src.agents.data_analysis.report_section import build_data_analysis_section
from src.llm.manager import LLMManager


async def main():
    query = '分析2024年银行业营收趋势'
    mock_search = json.loads((FIXTURES / 'mock_search.json').read_text(encoding='utf-8'))

    agent = DataAnalysisAgent(LLMManager())
    out = await agent.process({
        'query': query,
        'search_results': mock_search,
        'use_mock': True,
    })
    result = out.get('result') or {}
    charts = result.get('charts') or []

    section = build_data_analysis_section(result, section_index=1)
    md = '# Demo Report - 数据分析\n\n'
    md += section['content'] if section else '未生成数据分析章节'

    md_path = OUTDIR / 'demo_report.md'
    md_path.write_text(md, encoding='utf-8')
    print('Written', md_path)

    html_lines = [
        '<!doctype html>',
        '<html><head><meta charset="utf-8"><title>Demo Report</title>',
        '<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>',
        '<style>.chart{width:100%;height:360px;margin-bottom:24px}</style>',
        '</head><body>',
        '<h1>Demo Report - 数据分析</h1>',
        f'<div>{section["content"] if section else ""}</div>',
        '<div id="charts"></div>',
        '<script>'
    ]
    html_lines.append('const charts = ' + json.dumps(charts, ensure_ascii=False) + ';')
    html_lines.append(
        'charts.forEach((c,i)=>{const d=document.createElement("div");d.className="chart";'
        'd.id="chart_"+i;document.getElementById("charts").appendChild(d);'
        'const chart=echarts.init(d);const opt = c.spec? '
        '(typeof c.spec.option==="string"?JSON.parse(c.spec.option):c.spec.option) : c.option;'
        'chart.setOption(opt);});'
    )
    html_lines.append('</script></body></html>')

    html_path = OUTDIR / 'demo_report.html'
    html_path.write_text('\n'.join(html_lines), encoding='utf-8')
    print('Written', html_path)


if __name__ == '__main__':
    asyncio.run(main())
