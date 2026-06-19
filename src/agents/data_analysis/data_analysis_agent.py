"""金融数据分析智能体：编排 RAG 获取、金融分析、图表生成与结果输出。"""

from typing import Any, Dict

from loguru import logger

from ..base import AgentConfig, BaseAgent
from ...llm import LLMManager, PromptManager
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
        search_results = input_data.get("search_results") or []
        use_mock = input_data.get("use_mock", False)

        try:
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
