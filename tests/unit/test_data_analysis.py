"""金融数据分析智能体单元测试（mock 模式，不依赖 LLM / 真实 RAG）。"""

import asyncio
import importlib
import json
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 绕过 src.agents.__init__ 的重依赖链，仅注册 namespace
if "src" not in sys.modules:
    src_pkg = types.ModuleType("src")
    src_pkg.__path__ = [str(PROJECT_ROOT / "src")]
    sys.modules["src"] = src_pkg
if "src.agents" not in sys.modules:
    agents_pkg = types.ModuleType("src.agents")
    agents_pkg.__path__ = [str(PROJECT_ROOT / "src" / "agents")]
    sys.modules["src.agents"] = agents_pkg

from src.agents.data_analysis.chart_builder import build_charts
from src.agents.data_analysis.data_analysis_agent import DataAnalysisAgent
from src.agents.data_analysis.evidence_adapter import (
    build_analysis_input,
    build_web_pack,
    load_rag_evidence_pack,
    parse_rag_evidence_pack,
    rag_pack_to_refs,
    resolve_search_results,
    search_result_to_evidence,
)
from src.agents.data_analysis.search_relevance import (
    parse_query_terms,
    select_relevant_search_results_with_fallback,
)
from src.agents.data_analysis.data_analysis_context import (
    has_usable_analysis,
    mark_data_integration_sections,
)
from src.agents.data_analysis.report_section import build_data_analysis_section
from src.agents.data_analysis.financial_analyzer import FinancialAnalyzer
from src.agents.data_analysis.file_analyzer import FileDataAnalyzer
from src.agents.data_analysis.file_report import build_file_analysis_html, build_file_analysis_markdown
from src.agents.data_analysis.rag_client import RAGClient

FIXTURES = PROJECT_ROOT / "fixtures"


@pytest.fixture
def mock_search():
    return json.loads((FIXTURES / "mock_search.json").read_text(encoding="utf-8"))


@pytest.fixture
def mock_rag_raw():
    return json.loads((FIXTURES / "mock_rag.json").read_text(encoding="utf-8"))


class TestSearchRelevance:
    def test_huawei_revenue_query_rejects_news_digest(self):
        query = "分析2024年华为公司营收趋势"
        digest = {
            "title": "早报｜追觅组织调整，取消未落地业务/DeepSeek识图模式上线",
            "snippet": "追觅营收同比增长4%。另讯：博世因向华为出货被调查。某板块同比增长23%。",
            "content": (
                "追觅组织调整，取消未落地业务。追觅营收同比增长4%。"
                "另讯：博世因向华为出货被调查。某板块整体同比增长23%。"
            ),
        }
        huawei_article = {
            "title": "2024年华为公司营收分析",
            "snippet": "2024年华为公司营业收入同比增长8%。",
            "content": "2024年华为公司全年营业收入达7000亿元，同比增长8%，业绩稳步提升。",
        }
        selected, meta = select_relevant_search_results_with_fallback(
            query, [digest, huawei_article]
        )
        titles = [item["title"] for item in selected]
        assert any("华为" in t for t in titles)
        assert not any("追觅" in t for t in titles)
        assert meta.selected_count >= 1

    def test_no_match_returns_empty_but_runs_analysis_path(self):
        query = "分析2024年华为公司营收趋势"
        irrelevant = {
            "title": "2024年某手机品牌销量排行",
            "snippet": "市场整体同比增长12%。",
            "content": "2024年智能手机市场整体同比增长12%，与华为无关。",
        }
        selected, meta = select_relevant_search_results_with_fallback(
            query, [irrelevant]
        )
        assert selected == []
        assert meta.selected_count == 0
        assert "分析流程已执行" in meta.methodology_note()

    def test_parse_query_terms_huawei(self):
        terms = parse_query_terms("分析2024年华为公司营收趋势")
        assert "华为" in terms.entities
        assert "2024" in terms.years
        assert "营收" in terms.topics


class TestSearchExtractor:
    def test_comma_separated_revenue_not_truncated(self):
        from src.agents.data_analysis.search_extractor import extract_from_search_results

        results = [
            {
                "title": "华为2024年报发布：营收8621亿，同比增长22%",
                "content": "2024年华为全年销售收入8,621亿元，同比增长22%，净利润626亿元。",
            }
        ]
        points = extract_from_search_results(results, entity_terms=["华为"])
        revenue_points = [p for p in points if p.metric_id == "revenue"]
        assert revenue_points
        assert revenue_points[0].value == 8621.0
        assert "8,621" in revenue_points[0].raw_text or "8621" in revenue_points[0].raw_text


class TestLLMSearchAnalyzer:
    def test_extract_table_from_search(self):
        from src.agents.data_analysis.llm_search_analyzer import extract_table_from_search

        llm_json = json.dumps(
            {
                "table": {
                    "title": "2024年华为营收相关数值",
                    "columns": ["指标", "数值", "期间", "来源", "原文依据"],
                    "rows": [
                        ["2024年营业收入", "8621亿元", "2024", "[1]", "销售收入8,621亿"],
                    ],
                },
                "conclusion": "华为2024年营收8621亿元。",
                "methodology": "从1条搜索结果抽取营收指标",
            },
            ensure_ascii=False,
        )

        async def mock_llm(user, system):
            return llm_json

        search = [
            {
                "title": "华为2024年报",
                "url": "https://example.com/huawei",
                "content": "2024年华为全年销售收入8,621亿元，同比增长22%。",
            }
        ]
        out = asyncio.run(
            extract_table_from_search("分析2024年华为公司营收趋势", search, mock_llm)
        )
        assert out is not None
        assert len(out.table.rows) == 1
        assert "8621" in out.table.rows[0][1]
        assert out.conclusion
        assert len(out.search_refs) == 1


class TestReportSection:
    def test_unified_analysis_table_layout(self):
        payload = {
            "status": "success",
            "methodology": "从 2 条网页搜索结果抽取",
            "analysis_table": {
                "title": "2024年华为营收数值",
                "columns": ["指标", "数值", "期间", "来源", "原文依据"],
                "rows": [["营收", "8621亿元", "2024", "[1]", "8,621亿"]],
            },
            "analysis_conclusion": "华为2024年营收8621亿元。",
            "charts": [{"type": "bar", "title": "t", "spec": {"id": "x", "option": {}}}],
            "search_refs": [{"title": "华为年报", "url": "https://example.com", "snippet": "..."}],
        }
        section = build_data_analysis_section(payload, section_index=2)
        md = section["content"]
        assert "### 分析结果" in md
        assert "### 分析来源" in md
        assert "8621亿元" in md
        assert "chart_2_0" in md
        assert "[1]" in md
        assert "摘要" not in md
        assert section["sources_used"] == ["https://example.com"]

    def test_analysis_sources_only_cited_indices(self):
        payload = {
            "status": "success",
            "methodology": "测试",
            "analysis_table": {
                "title": "华为营收",
                "columns": ["指标", "数值", "期间", "来源", "原文依据"],
                "rows": [
                    ["2024年营业收入", "8621亿元", "2024", "[1]", "片段1"],
                    ["2025年营业收入", "8809亿元", "2025", "[6]", "片段2"],
                ],
            },
            "search_refs": [
                {"title": "来源一", "url": "https://example.com/1", "snippet": "s1"},
                {"title": "来源二", "url": "https://example.com/2", "snippet": "s2"},
                {"title": "来源三", "url": "https://example.com/3", "snippet": "s3"},
                {"title": "来源四", "url": "https://example.com/4", "snippet": "s4"},
                {"title": "来源五", "url": "https://example.com/5", "snippet": "s5"},
                {"title": "来源六", "url": "https://example.com/6", "snippet": "s6"},
            ],
        }
        section = build_data_analysis_section(payload, section_index=1)
        md = section["content"]
        assert "https://example.com/1" in md
        assert "https://example.com/6" in md
        assert "https://example.com/2" not in md
        assert "摘要" not in md
        assert md.count("https://example.com/") == 2

    def test_new_layout_with_source_blocks(self):
        payload = {
            "status": "success",
            "methodology": "测试口径",
            "search_refs": [
                {"title": "华为2024年报", "url": "https://example.com/a", "snippet": "营收8621亿"},
            ],
            "source_blocks": [
                {
                    "source_index": 1,
                    "source_title": "华为2024年报",
                    "source_url": "https://example.com/a",
                    "table": {
                        "title": "来源 [1] 华为 · 分析表",
                        "columns": ["指标", "数值"],
                        "rows": [["营收", "8621亿元"]],
                    },
                    "chart": {
                        "type": "bar",
                        "title": "来源 [1] 华为 · 分析表",
                        "spec": {"id": "x", "option": {"series": []}},
                    },
                    "conclusion": "华为2024年营收达8621亿元，同比保持增长。",
                }
            ],
        }
        section = build_data_analysis_section(payload, section_index=3)
        assert section is not None
        md = section["content"]
        assert "### 分析图表" in md
        assert "### 分析来源" in md
        assert "#### 来源 [1]" in md
        assert "**结论**" in md
        assert "8621亿元" in md
        assert "chart_3_0" in md
        assert section["charts"]
        assert section["charts"][0]["id"] == "chart_3_0"


class TestEvidenceAdapter:
    def test_resolve_search_no_silent_mock(self):
        resolved = resolve_search_results([], use_mock=False)
        assert resolved == []

    def test_search_result_to_evidence(self, mock_search):
        ev = search_result_to_evidence(mock_search[0], 1)
        assert ev.origin == "web_search"
        assert ev.title == "2024年银行业财报解读"
        assert "23%" in ev.content or "23%" in ev.summary

    def test_load_rag_evidence_pack_legacy_list(self, mock_rag_raw):
        pack = load_rag_evidence_pack(mock_rag_raw, query="测试")
        assert pack.source == "financial_rag"
        assert len(pack.evidence) == 3
        assert pack.evidence[0].content
        assert pack.evidence[0].score > 0

    def test_build_analysis_input(self, mock_search, mock_rag_raw):
        pack = load_rag_evidence_pack(mock_rag_raw)
        inp = build_analysis_input(
            query="分析2024年银行业营收趋势",
            search_results=mock_search,
            rag_pack=pack,
        )
        assert len(inp.search_refs) >= 1
        assert len(inp.rag_refs) == 3
        assert len(inp.unified.all_evidence) == len(mock_search) + 3

    def test_rag_pack_to_refs(self, mock_rag_raw):
        pack = load_rag_evidence_pack(mock_rag_raw)
        refs = rag_pack_to_refs(pack)
        assert refs[0].score > 0
        assert refs[0].content


class TestRAGClient:
    def test_retrieve_pack_mock(self):
        client = RAGClient(use_mock=True)
        pack = asyncio.run(client.retrieve_pack("测试查询"))
        assert pack.source == "financial_rag"
        assert len(pack.evidence) >= 1

    def test_retrieve_compat(self):
        client = RAGClient(use_mock=True)
        refs = asyncio.run(client.retrieve("测试查询"))
        assert len(refs) >= 1
        assert refs[0].content


class TestFinancialAnalyzer:
    def test_rule_based_analysis(self, mock_search, mock_rag_raw):
        pack = load_rag_evidence_pack(mock_rag_raw)
        rag_refs = rag_pack_to_refs(pack)
        analyzer = FinancialAnalyzer()
        output = asyncio.run(
            analyzer.analyze(
                query="分析2024年银行业营收趋势",
                search_results=mock_search,
                rag_refs=rag_refs,
                use_mock=False,
            )
        )

        by_source = output.metrics.get("by_source", {})
        assert by_source or output.metrics
        assert len(output.key_findings) >= 1
        assert len(output.tables) >= 1
        assert output.search_refs
        assert output.rag_refs

    def test_empty_search_without_mock(self, mock_rag_raw):
        pack = load_rag_evidence_pack(mock_rag_raw)
        rag_refs = rag_pack_to_refs(pack)
        analyzer = FinancialAnalyzer()
        output = asyncio.run(
            analyzer.analyze(
                query="分析华为营收",
                search_results=[],
                rag_refs=rag_refs,
                use_mock=False,
            )
        )
        assert output.metrics == {}
        assert output.tables == []
        assert "未获取到网页搜索结果" in output.methodology

    def test_mock_fallback_without_search(self, mock_rag_raw):
        pack = load_rag_evidence_pack(mock_rag_raw)
        rag_refs = rag_pack_to_refs(pack)
        analyzer = FinancialAnalyzer()
        output = asyncio.run(
            analyzer.analyze(
                query="分析2024年银行业营收趋势",
                search_results=[],
                rag_refs=rag_refs,
                use_mock=True,
            )
        )
        assert output.metrics
        assert output.key_findings


class TestChartBuilder:
    def test_parse_metric_value_with_yi_unit(self):
        from src.agents.data_analysis.chart_builder import (
            _parse_metric_value,
            build_chart_for_table,
        )
        from src.agents.data_analysis.schemas import DataTable

        assert _parse_metric_value("8621亿元") == 8621.0
        assert _parse_metric_value("626亿元") == 626.0
        assert _parse_metric_value("23%") == 23.0

        table = DataTable(
            title="2024年华为公司营收趋势分析",
            columns=["指标", "数值", "期间", "来源", "原文依据"],
            rows=[
                ["2024年营业收入", "8621亿元", "2024", "[1]", "8,621亿"],
                ["2024年净利润", "626亿元", "2024", "[1]", "62.6 billion"],
            ],
        )
        chart = build_chart_for_table(table, chart_id="chart_test")
        assert chart is not None
        option_raw = chart["spec"]["option"]
        option = json.loads(option_raw) if isinstance(option_raw, str) else option_raw
        values = [d["value"] if isinstance(d, dict) else d for d in option["series"][0]["data"]]
        assert values[0] == 8621.0
        assert values[1] == 626.0


class TestChartBuilderLegacy:
    def test_build_charts_from_analysis(self, mock_search, mock_rag_raw):
        pack = load_rag_evidence_pack(mock_rag_raw)
        rag_refs = rag_pack_to_refs(pack)
        analysis = asyncio.run(
            FinancialAnalyzer().analyze(
                query="q",
                search_results=mock_search,
                rag_refs=rag_refs,
            )
        )
        charts = build_charts(analysis)
        assert len(charts) >= 1
        assert charts[0]["type"] == "bar"
        assert "spec" in charts[0]


class TestDataAnalysisAgent:
    @staticmethod
    def _banking_llm_response():
        return json.dumps(
            {
                "table": {
                    "title": "2024年银行业营收相关数值",
                    "columns": ["指标", "数值", "期间", "来源", "原文依据"],
                    "rows": [
                        ["营收同比增长", "23%", "2024", "[1]", "同比增长23%"],
                    ],
                },
                "conclusion": "2024年银行业营收同比增长23%。",
                "methodology": "从搜索结果正文抽取财务指标",
            },
            ensure_ascii=False,
        )

    def test_end_to_end_llm_search(self, mock_search):
        llm_manager = MagicMock()
        agent = DataAnalysisAgent(llm_manager=llm_manager)
        agent.get_llm_response = AsyncMock(return_value=self._banking_llm_response())

        result = asyncio.run(
            agent.process(
                {
                    "query": "分析2024年银行业营收趋势",
                    "search_results": mock_search,
                    "use_mock": False,
                }
            )
        )

        assert result["status"] == "success"
        payload = result["result"]
        assert payload["status"] == "success"
        assert payload["analysis_table"]
        assert payload["analysis_table"]["rows"]
        assert payload["charts"]
        assert payload["search_refs"]

    def test_no_skip_when_search_irrelevant_to_prompt(self, mock_rag_raw):
        pack = load_rag_evidence_pack(mock_rag_raw)
        rag_refs = rag_pack_to_refs(pack)
        irrelevant_search = [
            {
                "title": "2024年某手机品牌销量排行",
                "snippet": "市场整体同比增长12%。",
                "content": "2024年智能手机市场整体同比增长12%，与华为无关。",
            }
        ]
        analyzer = FinancialAnalyzer()
        output = asyncio.run(
            analyzer.analyze(
                query="分析2024年华为公司营收趋势",
                search_results=irrelevant_search,
                rag_refs=rag_refs,
                use_mock=False,
            )
        )
        assert output.metrics == {}
        assert "分析流程已执行" in output.methodology

    def test_analyze_mode_not_skipped_with_irrelevant_search(self, mock_rag_raw):
        llm_manager = MagicMock()
        agent = DataAnalysisAgent(llm_manager=llm_manager)
        agent.get_llm_response = AsyncMock(side_effect=RuntimeError("skip llm"))

        result = asyncio.run(
            agent.process(
                {
                    "query": "分析2024年华为公司营收趋势",
                    "search_results": [
                        {
                            "title": "2024年某手机品牌销量排行",
                            "content": "2024年智能手机市场整体同比增长12%。",
                        }
                    ],
                    "use_mock": False,
                }
            )
        )
        assert result["status"] == "success"
        payload = result["result"]
        assert payload["status"] == "success"
        assert not payload.get("analysis_table")
        assert "LLM 未能生成" in (payload.get("methodology") or "")

    def test_skipped_without_search(self):
        llm_manager = MagicMock()
        agent = DataAnalysisAgent(llm_manager=llm_manager)
        agent.get_llm_response = AsyncMock(side_effect=RuntimeError("skip llm"))

        result = asyncio.run(
            agent.process(
                {
                    "query": "分析华为营收",
                    "search_results": [],
                    "use_mock": False,
                }
            )
        )
        assert result["status"] == "success"
        payload = result["result"]
        assert payload["status"] == "skipped"
        assert payload["source_type"] == "web_rag"
        assert payload["metrics"] == {}

    def test_full_mock_mode(self):
        llm_manager = MagicMock()
        agent = DataAnalysisAgent(llm_manager=llm_manager)
        agent.get_llm_response = AsyncMock(side_effect=RuntimeError("skip llm"))

        result = asyncio.run(
            agent.process(
                {
                    "query": "分析2024年银行业营收趋势",
                    "search_results": [],
                    "use_mock": True,
                }
            )
        )
        assert result["status"] == "success"
        assert result["result"]["source_type"] == "mock"


class TestFileDataAnalyzer:
    def test_csv_analysis_generates_summary_and_charts(self):
        csv_content = (
            "date,revenue,profit\n"
            "2024-01,100,10\n"
            "2024-02,120,12\n"
            "2024-03,140,14\n"
        )
        analyzer = FileDataAnalyzer()
        result = analyzer.analyze_file(
            query="测试CSV",
            file_name="sample.csv",
            file_type="csv",
            file_content=csv_content,
        )

        assert result["status"] == "success"
        assert result["source_type"] == "csv"
        assert result["metrics"]["row_count"] == 3
        assert result["metrics"]["column_count"] == 3
        assert result["tables"]
        assert result["charts"]
        section = build_file_analysis_markdown({
            "title": "测试报告",
            "content": "测试内容",
            "content_html": "<p>测试内容</p>",
            "charts": result["charts"],
        })
        assert "# 测试报告" in section

    def test_text_analysis_generates_keywords(self):
        text_content = "这是一个测试文本。文本中出现关键词：财务、盈利、增长。财务分析结果需要重点关注。"
        analyzer = FileDataAnalyzer()
        result = analyzer.analyze_file(
            query="测试文本",
            file_name="sample.txt",
            file_type="text",
            file_content=text_content,
        )

        assert result["status"] == "success"
        assert result["source_type"] == "text"
        assert result["metrics"]["word_count"] > 0
        assert result["tables"]
        assert result["charts"]


class TestFixtures:
    def test_fixture_files_exist(self):
        assert (FIXTURES / "mock_search.json").exists()
        assert (FIXTURES / "mock_rag.json").exists()
        assert (FIXTURES / "mock_stats.json").exists()

    def test_web_pack_shape(self, mock_search):
        pack = build_web_pack("q", mock_search)
        assert pack.source == "web_search"
        assert len(pack.evidence) == len(mock_search)
