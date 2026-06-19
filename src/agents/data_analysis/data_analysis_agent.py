"""金融数据分析智能体：网页搜索 → LLM 数值表 → 图表 → 报告。"""

from typing import Any, Dict, List

from loguru import logger

from ..base import AgentConfig, BaseAgent
from ...llm import LLMManager, PromptManager
from .chart_builder import build_chart_for_table, build_charts
from .financial_analyzer import FinancialAnalyzer
from .llm_search_analyzer import _build_search_refs, extract_table_from_search
from .schemas import DataAnalysisResult, DataFinding
from .source_report_builder import build_source_blocks


class DataAnalysisAgent(BaseAgent):
    """智能体入口：将搜索结果交 LLM 抽取数值表，并组装最终输出。"""

    def __init__(
        self,
        llm_manager: LLMManager,
        prompt_manager: PromptManager = None,
        rag_client=None,
        analyzer: FinancialAnalyzer = None,
    ):
        config = AgentConfig(
            name="金融数据分析智能体",
            description="基于网页搜索结果，由 LLM 抽取数值表格并可视化",
            llm_config_name="default",
            temperature=0.2,
            max_tokens=6000,
        )
        super().__init__(llm_manager, prompt_manager, config)
        self.analyzer = analyzer or FinancialAnalyzer()

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        query = input_data.get("query", "")
        search_results = input_data.get("search_results") or []
        use_mock = input_data.get("use_mock", False)

        try:
            has_real_search = bool(search_results) and not use_mock

            if has_real_search:
                return await self._process_llm_search(query, search_results)

            if use_mock:
                return await self._process_mock(query, search_results)

            return self._empty_result("无网页搜索结果，已跳过数据分析", skipped=True)

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
            source_type="web_rag",
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

    async def _process_mock(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        analysis = await self.analyzer.analyze(
            query=query,
            search_results=search_results,
            rag_refs=[],
            use_mock=True,
        )
        source_blocks = await build_source_blocks(
            query=query,
            analysis=analysis,
            search_results=search_results,
            llm_callback=self.get_llm_response,
        )
        charts = (
            [b["chart"] for b in source_blocks if b.get("chart")]
            if source_blocks
            else build_charts(analysis)
        )
        main_table = None
        conclusion = ""
        if source_blocks and source_blocks[0].get("table"):
            main_table = source_blocks[0]["table"]
            conclusion = source_blocks[0].get("conclusion", "")
        elif analysis.tables:
            main_table = analysis.tables[0].model_dump()

        result = DataAnalysisResult(
            status="success",
            source_type="mock",
            metrics=analysis.metrics,
            tables=[t.model_dump() for t in analysis.tables],
            charts=charts,
            key_findings=analysis.key_findings,
            source_blocks=source_blocks,
            methodology=analysis.methodology,
            rag_refs=[],
            search_refs=[r.model_dump() for r in analysis.search_refs],
            analysis_table=main_table,
            analysis_conclusion=conclusion,
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
