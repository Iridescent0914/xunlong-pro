"""金融数据分析智能体单元测试（mock 模式，不依赖真实 LLM / 搜索）。"""

import asyncio
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

from src.agents.data_analysis.data_analysis_agent import DataAnalysisAgent
from src.agents.data_analysis.report_section import build_data_analysis_section
from src.agents.data_analysis.ppt_section import build_data_analysis_slides
from src.agents.data_analysis.file_analyzer import FileDataAnalyzer
from src.agents.data_analysis.file_report import build_file_analysis_markdown

FIXTURES = PROJECT_ROOT / "fixtures"


@pytest.fixture
def mock_search():
    return json.loads((FIXTURES / "mock_search.json").read_text(encoding="utf-8"))


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


class TestPptSection:
    _UNIFIED_PAYLOAD = {
        "status": "success",
        "methodology": "从网页搜索结果抽取",
        "analysis_table": {
            "title": "2024年华为营收数值",
            "columns": ["指标", "数值", "期间", "来源", "原文依据"],
            "rows": [["营收", "8621亿元", "2024", "[1]", "8,621亿"]],
        },
        "analysis_conclusion": "华为2024年营收8621亿元。",
        "charts": [
            {
                "type": "bar",
                "title": "华为营收",
                "spec": {
                    "option": {
                        "xAxis": {"type": "category", "data": ["2024"]},
                        "yAxis": {"type": "value"},
                        "series": [{"type": "bar", "data": [8621]}],
                    }
                },
            }
        ],
        "search_refs": [
            {"title": "华为年报", "url": "https://example.com/1", "snippet": "s1"},
            {"title": "其他来源", "url": "https://example.com/2", "snippet": "s2"},
        ],
    }

    def test_build_slides_from_unified_analysis(self):
        slides = build_data_analysis_slides(self._UNIFIED_PAYLOAD, section_index=5)
        assert len(slides) == 3
        titles = [s["title"] for s in slides]
        assert "金融数据分析 · 分析结果" in titles
        assert "金融数据分析 · 分析来源" in titles
        assert all(s.get("html_content") for s in slides)
        assert "8621亿元" in slides[0]["html_content"]
        assert "echarts.init" in slides[1]["html_content"]
        sources_html = slides[2]["html_content"]
        assert "https://example.com/1" in sources_html
        assert "https://example.com/2" not in sources_html
        assert "摘要" not in sources_html

    def test_build_slides_skipped_when_not_success(self):
        assert build_data_analysis_slides({"status": "skipped"}) == []

    def test_inject_before_conclusion(self):
        from src.agents.ppt.ppt_coordinator import PPTCoordinator

        coordinator = PPTCoordinator(MagicMock(), MagicMock())
        slides_data = [
            {"slide_number": 1, "title": "封面", "html_content": "<div>cover</div>"},
            {"slide_number": 2, "title": "内容", "html_content": "<div>body</div>"},
            {"slide_number": 3, "title": "总结", "html_content": "<div>end</div>"},
        ]
        outline = {
            "colors": {"primary": "#111", "accent": "#222"},
            "pages": [
                {"page_type": "title"},
                {"page_type": "content"},
                {"page_type": "conclusion"},
            ],
        }
        merged = coordinator._inject_data_analysis_slides(
            slides_data, outline, self._UNIFIED_PAYLOAD
        )
        assert len(merged) == 6
        assert merged[2].get("is_data_analysis")
        assert merged[-1]["title"] == "总结"
        assert [s["slide_number"] for s in merged] == [1, 2, 3, 4, 5, 6]


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

    def test_mixed_percent_and_absolute_rows_use_percent_only(self):
        from src.agents.data_analysis.chart_builder import build_chart_for_table
        from src.agents.data_analysis.schemas import DataTable

        table = DataTable(
            title="贵州茅台指标",
            columns=["指标", "数值", "期间", "来源", "原文依据"],
            rows=[
                ["主营业务收入增长率", "6.538%", "2024", "[W1]", "x"],
                ["主营业务利润(元)", "40161115859.23", "2024", "[W1]", "y"],
            ],
        )
        chart = build_chart_for_table(table, chart_id="chart_moutai")
        assert chart is not None
        option_raw = chart["spec"]["option"]
        option = json.loads(option_raw) if isinstance(option_raw, str) else option_raw
        assert len(option["xAxis"]["data"]) == 1
        assert option["series"][0]["data"][0]["value"] == 6.538


class TestLLMSearchAnalyzer:
    def test_normalize_table_monetary_units_unifies_yuan_and_yi(self):
        from src.agents.data_analysis.llm_search_analyzer import normalize_table_monetary_units
        from src.agents.data_analysis.schemas import DataTable

        table = DataTable(
            title="贵州茅台关键指标",
            columns=["指标", "数值", "期间", "来源", "原文依据"],
            rows=[
                ["2026年第一季度营业收入", "547.03亿元", "2026Q1", "[W1]", "片段1"],
                ["2025年营业总收入", "170899152276.34元", "2025", "[W2]", "片段2"],
                ["2024年归母净利润", "86228146421.62元", "2024", "[W3]", "片段3"],
                ["营收同比增长", "6.538%", "2024", "[W4]", "片段4"],
            ],
        )

        normalized = normalize_table_monetary_units(table)

        assert normalized.rows[0][1] == "547.03亿元"
        assert normalized.rows[1][1] == "1708.99亿元"
        assert normalized.rows[2][1] == "862.28亿元"
        assert normalized.rows[3][1] == "6.538%"
        assert normalized.columns[1] == "数值（亿元）"

    def test_normalize_table_uses_wan_for_small_amounts(self):
        from src.agents.data_analysis.llm_search_analyzer import normalize_table_monetary_units
        from src.agents.data_analysis.schemas import DataTable

        table = DataTable(
            title="门店营收",
            columns=["指标", "数值", "期间"],
            rows=[
                ["门店A营收", "520万元", "2024"],
                ["门店B营收", "860万元", "2024"],
                ["门店C营收", "12000000元", "2024"],
            ],
        )
        normalized = normalize_table_monetary_units(table)
        assert normalized.rows[0][1] == "520万元"
        assert normalized.rows[1][1] == "860万元"
        assert normalized.rows[2][1] == "1200万元"
        assert normalized.columns[1] == "数值（万元）"

    def test_normalize_table_uses_yuan_for_tiny_amounts(self):
        from src.agents.data_analysis.llm_search_analyzer import normalize_table_monetary_units
        from src.agents.data_analysis.schemas import DataTable

        table = DataTable(
            title="费用明细",
            columns=["指标", "数值", "期间"],
            rows=[
                ["办公费用", "3500元", "2024"],
                ["差旅费用", "8200元", "2024"],
            ],
        )
        normalized = normalize_table_monetary_units(table)
        assert normalized.rows[0][1] == "3500元"
        assert normalized.rows[1][1] == "8200元"
        assert normalized.columns[1] == "数值（元）"

    def test_normalize_table_monetary_units_enables_bar_chart(self):
        from src.agents.data_analysis.chart_builder import build_chart_for_table
        from src.agents.data_analysis.llm_search_analyzer import normalize_table_monetary_units
        from src.agents.data_analysis.schemas import DataTable

        table = normalize_table_monetary_units(
            DataTable(
                title="营收对比",
                columns=["指标", "数值", "期间"],
                rows=[
                    ["2025年营业收入", "1720.54亿元", "2025"],
                    ["2025年营业总收入", "170899152276.34元", "2025"],
                ],
            )
        )
        chart = build_chart_for_table(table, chart_id="chart_unified")
        assert chart is not None
        option_raw = chart["spec"]["option"]
        option = json.loads(option_raw) if isinstance(option_raw, str) else option_raw
        values = [d["value"] if isinstance(d, dict) else d for d in option["series"][0]["data"]]
        assert len(values) == 2
        assert values[0] == 1720.54
        assert values[1] == 1708.99


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

    def test_analyze_mode_not_skipped_with_irrelevant_search(self):
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
        agent.get_llm_response = AsyncMock(return_value=self._banking_llm_response())

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
        payload = result["result"]
        assert payload["source_type"] == "mock"
        assert payload["analysis_table"]
        assert payload["charts"]


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
