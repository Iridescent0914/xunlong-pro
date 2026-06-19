"""Demo: 使用 fixtures/mock_search.json + fixtures/mock_rag.json 运行数据分析并生成 Markdown/HTML 报告

用法:
    python scripts/demo_data_analysis_run.py

输出:
    output/demo_report.md
    output/demo_report.html
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'fixtures'
OUTDIR = ROOT / 'output'
OUTDIR.mkdir(exist_ok=True)

sys.path.insert(0,str(Path(__file__).parent.parent))

from src.agents.data_analysis.rag_client import RAGClient
from src.agents.data_analysis.evidence_adapter import build_analysis_input, parse_rag_evidence_pack
from src.agents.data_analysis.financial_analyzer import FinancialAnalyzer
from src.agents.data_analysis.chart_builder import build_charts
from src.agents.data_analysis.report_section import build_data_analysis_section


async def main():
    query = '分析2024年银行业营收趋势'

    mock_search = json.loads((FIXTURES / 'mock_search.json').read_text(encoding='utf-8'))
    mock_rag = json.loads((FIXTURES / 'mock_rag.json').read_text(encoding='utf-8'))

    # parse rag pack
    rag_pack = parse_rag_evidence_pack(mock_rag)
    from src.agents.data_analysis.evidence_adapter import rag_pack_to_refs
    rag_refs = rag_pack_to_refs(rag_pack)

    analyzer = FinancialAnalyzer()
    analysis_output = await analyzer.analyze(
        query=query,
        search_results=mock_search,
        rag_refs=rag_refs,
        use_mock=True,
        llm_callback=None,
        use_llm=False,
    )

    charts = build_charts(analysis_output)

    # assemble result
    result = {
        'status': 'success',
        'metrics': analysis_output.metrics,
        'tables': [t.model_dump() for t in analysis_output.tables],
        'charts': charts,
        'key_findings': [f.model_dump() for f in analysis_output.key_findings],
        'methodology': analysis_output.methodology,
        'rag_refs': [r.model_dump() for r in analysis_output.rag_refs],
        'search_refs': [r.model_dump() for r in analysis_output.search_refs],
    }

    # build markdown section
    section = build_data_analysis_section(result, section_index=1)
    md = '# Demo Report - 数据分析\n\n'
    md += section['content'] if section else '未生成数据分析章节'

    md_path = OUTDIR / 'demo_report.md'
    md_path.write_text(md, encoding='utf-8')
    print('Written', md_path)

    # simple HTML page that embeds echarts
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
    html_lines.append('charts.forEach((c,i)=>{const d=document.createElement("div");d.className="chart";d.id="chart_"+i;document.getElementById("charts").appendChild(d);const chart=echarts.init(d);const opt = c.spec? (typeof c.spec.option==="string"?JSON.parse(c.spec.option):c.spec.option) : c.option;chart.setOption(opt);});')
    html_lines.append('</script></body></html>')

    html_path = OUTDIR / 'demo_report.html'
    html_path.write_text('\n'.join(html_lines), encoding='utf-8')
    print('Written', html_path)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
