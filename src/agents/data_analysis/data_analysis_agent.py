"""金融数据分析智能体：编排 RAG 获取、金融分析、图表生成与结果输出。"""

import json
from pathlib import Path
from typing import Any, Dict, List
from typing import Any, Dict

from loguru import logger

from ..base import AgentConfig, BaseAgent
from ...llm import LLMManager, PromptManager
from .chart_builder import build_chart_for_table
from .llm_search_analyzer import _build_search_refs, extract_table_from_search
from .schemas import DataAnalysisResult, DataFinding

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MOCK_SEARCH_PATH = PROJECT_ROOT / "fixtures" / "mock_search.json"
from .chart_builder import build_charts
from .evidence_adapter import parse_rag_evidence_pack, rag_pack_to_refs
from .financial_analyzer import FinancialAnalyzer
from .rag_client import RAGClient
from .schemas import DataAnalysisResult
from .source_report_builder import build_source_blocks


class DataAnalysisAgent(BaseAgent):
    """智能体入口：调用 FinancialAnalyzer 完成分析，并组装最终输出。"""

    def __init__(
        self,
        llm_manager: LLMManager,
        prompt_manager: PromptManager = None,
        rag_client: RAGClient = None,
        analyzer: FinancialAnalyzer = None,
    ):
        config = AgentConfig(
            name="金融数据分析智能体",
            description="输入网页搜索与 RAG，调用金融分析模块，输出结构化结论与图表",
            llm_config_name="default",
            temperature=0.3,
            max_tokens=4000,
        )
        super().__init__(llm_manager, prompt_manager, config)
        self.rag_client = rag_client or RAGClient()
        self.analyzer = analyzer or FinancialAnalyzer()

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        query = input_data.get("query", "")
        search_results = list(input_data.get("search_results") or [])
        use_mock = input_data.get("use_mock", False)

        try:
            if use_mock and not search_results:
                search_results = _load_mock_search()

            if search_results:
                return await self._process_llm_search(query, search_results, use_mock=use_mock)
            rag_refs = []
            if not use_mock:
                rag_pack_raw = input_data.get("rag_pack")
                if rag_pack_raw and isinstance(rag_pack_raw, dict):
                    rag_pack = parse_rag_evidence_pack(rag_pack_raw)
                    rag_refs = rag_pack_to_refs(rag_pack)
                else:
                    rag_refs = await self.rag_client.retrieve(query)

            use_llm = input_data.get("use_llm", False)
            analysis = await self.analyzer.analyze(
                query=query,
                search_results=search_results,
                rag_refs=rag_refs,
                use_mock=use_mock,
                llm_callback=self.get_llm_response if use_llm else None,
                use_llm=use_llm,
            )

            source_blocks = await build_source_blocks(
                query=query,
                analysis=analysis,
                search_results=search_results,
                llm_callback=self.get_llm_response if use_llm else None,
            )
            charts = (
                [block["chart"] for block in source_blocks if block.get("chart")]
                if source_blocks
                else build_charts(analysis)
            )

            has_output = bool(
                analysis.metrics or analysis.tables or analysis.key_findings
            )
            has_real_search = bool(search_results) and not use_mock
            has_rag_refs = bool(analysis.rag_refs)

            if use_mock:
                result_status = "success"
                source_type = "mock"
                message = None
            elif has_output:
                result_status = "success"
                source_type = "web_rag"
                if not has_real_search and has_rag_refs:
                    message = "网页搜索结果为空，已基于 RAG 年报证据生成基础分析"
                elif has_real_search and not analysis.search_refs and has_rag_refs:
                    message = "网页搜索结果未通过相关性筛选，已基于 RAG 年报证据生成基础分析"
                else:
                    message = None
            else:
                result_status = "skipped"
                source_type = "web_rag"
                message = analysis.methodology or "未找到可用于金融数据分析的网页或 RAG 证据"

            result = DataAnalysisResult(
                status=result_status,
                source_type=source_type,
                message=message,
                metrics=analysis.metrics,
                tables=[table.model_dump() for table in analysis.tables],
                charts=charts,
                key_findings=analysis.key_findings,
                source_blocks=source_blocks,
                methodology=analysis.methodology,
                rag_refs=analysis.rag_refs,
                search_refs=analysis.search_refs,
            )
            return {"status": "success", "agent": self.name, "result": result.model_dump()}

        except Exception as e:
            logger.error(f"[{self.name}] 分析失败: {e}")
            return {
                "status": "error",
                "agent": self.name,
                "result": DataAnalysisResult(status="error", message=str(e)).model_dump(),
                "error": str(e),
            }

    async def _process_llm_search(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        *,
        use_mock: bool = False,
    ) -> Dict[str, Any]:
        search_refs = _build_search_refs(search_results)
        llm_out = await extract_table_from_search(
            query, search_results, self.get_llm_response
        )

        if not llm_out:
            return self._empty_result(
                f"已读取 {len(search_results)} 条搜索结果，但 LLM 未能生成数值表格",
                search_refs=[r.model_dump() for r in search_refs],
            )

        table = llm_out.table
        has_rows = bool(table.rows)

        chart = build_chart_for_table(table, chart_id="chart_da_0") if has_rows else None
        charts = [chart] if chart else []

        key_findings: List[DataFinding] = []
        if llm_out.conclusion:
            key_findings.append(
                DataFinding(
                    title="分析结论",
                    value=llm_out.conclusion[:200],
                    evidence="由 LLM 基于数值表归纳",
                )
            )

        source_blocks: List[Dict[str, Any]] = []
        if has_rows:
            source_blocks.append(
                {
                    "source_index": 0,
                    "source_title": table.title,
                    "source_url": "",
                    "table": table.model_dump(),
                    "chart": chart,
                    "conclusion": llm_out.conclusion,
                }
            )

        message = None if has_rows else (llm_out.conclusion or "未从搜索结果中抽取到相关数值")

        result = DataAnalysisResult(
            status="success",
            source_type="mock" if use_mock else "web_rag",
            message=message,
            metrics={},
            tables=[table.model_dump()] if has_rows else [],
            charts=charts,
            key_findings=key_findings,
            source_blocks=source_blocks,
            methodology=llm_out.methodology,
            rag_refs=[],
            search_refs=[r.model_dump() for r in search_refs],
            analysis_table=table.model_dump() if has_rows else None,
            analysis_conclusion=llm_out.conclusion,
        )
        return {"status": "success", "agent": self.name, "result": result.model_dump()}

    def _empty_result(
        self,
        message: str,
        search_refs: List[Dict[str, Any]] = None,
        *,
        skipped: bool = False,
    ) -> Dict[str, Any]:
        result = DataAnalysisResult(
            status="skipped" if skipped else "success",
            source_type="web_rag",
            message=message,
            methodology=message,
            search_refs=search_refs or [],
        )
        return {"status": "success", "agent": self.name, "result": result.model_dump()}


def _load_mock_search() -> List[Dict[str, Any]]:
    if not MOCK_SEARCH_PATH.exists():
        logger.warning(f"[DataAnalysisAgent] mock 搜索文件不存在: {MOCK_SEARCH_PATH}")
        return []
    return json.loads(MOCK_SEARCH_PATH.read_text(encoding="utf-8"))
