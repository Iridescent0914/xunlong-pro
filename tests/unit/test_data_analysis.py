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
    select_relevant_search_results,
)
from src.agents.data_analysis.data_analysis_context import (
    build_main_body_relation,
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
    def test_end_to_end_mock(self, mock_search):
        llm_manager = MagicMock()
        agent = DataAnalysisAgent(llm_manager=llm_manager, rag_client=RAGClient(use_mock=True))
        agent.get_llm_response = AsyncMock(side_effect=RuntimeError("skip llm"))

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
        assert payload["source_type"] == "web_rag"
        assert payload["metrics"]
        assert payload["charts"]
        assert payload["key_findings"]
        assert payload["rag_refs"]
        assert payload["search_refs"]

    def test_skipped_without_search(self):
        llm_manager = MagicMock()
        agent = DataAnalysisAgent(llm_manager=llm_manager, rag_client=RAGClient(use_mock=True))
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
        agent = DataAnalysisAgent(llm_manager=llm_manager, rag_client=RAGClient(use_mock=True))
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
