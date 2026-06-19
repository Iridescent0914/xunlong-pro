"""金融数据分析智能体：编排 RAG 获取、金融分析、图表生成与结果输出。"""

from typing import Any, Dict

from loguru import logger

from ..base import AgentConfig, BaseAgent
from ...llm import LLMManager, PromptManager
from .chart_builder import build_charts
from .financial_analyzer import FinancialAnalyzer
from .rag_client import RAGClient
from .schemas import DataAnalysisResult
from .evidence_adapter import parse_rag_evidence_pack, rag_pack_to_refs


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
            # 支持两种 RAG 输入：1) 外部传入的 rag_pack JSON（优先） 2) 通过 RAGClient 检索
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
            charts = build_charts(analysis)

            has_output = bool(
                analysis.metrics or analysis.tables or analysis.key_findings
            )
            has_real_search = bool(search_results) and not use_mock
            if not has_real_search and not use_mock:
                result_status = "skipped"
                source_type = "web_rag"
                message = "无网页搜索结果，已跳过基于搜索的数据分析"
            elif has_real_search and not has_output:
                result_status = "skipped"
                source_type = "web_rag"
                message = analysis.methodology or "未找到与用户查询密切相关的搜索结果"
            elif use_mock:
                result_status = "success"
                source_type = "mock"
                message = None
            else:
                result_status = "success"
                source_type = "web_rag"
                message = None

            result = DataAnalysisResult(
                status=result_status,
                source_type=source_type,
                message=message,
                metrics=analysis.metrics,
                tables=[t.model_dump() for t in analysis.tables],
                charts=charts,
                key_findings=analysis.key_findings,
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
