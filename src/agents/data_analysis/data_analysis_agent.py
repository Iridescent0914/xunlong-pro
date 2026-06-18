"""金融数据分析智能体：综合分析网页搜索输出 + RAG 输出。"""

import json
from typing import Any, Dict, List

from loguru import logger

from ..base import AgentConfig, BaseAgent
from ...llm import LLMManager, PromptManager
from .chart_builder import build_charts
from .rag_client import RAGClient
from .search_extractor import extract_from_search
from .schemas import DataAnalysisResult, DataFinding, RAGReference, SearchReference


class DataAnalysisAgent(BaseAgent):
    def __init__(
        self,
        llm_manager: LLMManager,
        prompt_manager: PromptManager = None,
        rag_client: RAGClient = None,
    ):
        config = AgentConfig(
            name="金融数据分析智能体",
            description="综合网页搜索结果与 RAG 知识库，输出结构化金融分析结论与图表",
            llm_config_name="default",
            temperature=0.3,
            max_tokens=3000,
        )
        super().__init__(llm_manager, prompt_manager, config)
        self.rag_client = rag_client or RAGClient()

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        query = input_data.get("query", "")
        search_results = input_data.get("search_results") or []
        use_mock = input_data.get("use_mock", False)

        try:
            stats = await extract_from_search(search_results, use_mock=use_mock)
            rag_refs = await self.rag_client.retrieve(query)
            charts = build_charts(stats)
            findings = await self._interpret(query, stats, rag_refs)

            has_real_search = bool(search_results) and not use_mock
            source_type = "web_rag" if has_real_search else "mock"

            result = DataAnalysisResult(
                status="success",
                source_type=source_type,
                metrics=stats.metrics,
                tables=[t.model_dump() for t in stats.tables],
                charts=charts,
                key_findings=findings,
                methodology=stats.data_summary or "基于搜索结果与 RAG 口径综合分析",
                rag_refs=rag_refs,
                search_refs=stats.search_refs,
            )
            return {"status": "success", "agent": self.name, "result": result.model_dump()}

        except Exception as e:
            logger.error(f"[{self.name}] 分析失败: {e}")
            result = DataAnalysisResult(
                status="error",
                message=str(e),
            )
            return {"status": "error", "agent": self.name, "result": result.model_dump(), "error": str(e)}

    async def _interpret(
        self,
        query: str,
        stats,
        rag_refs: List[RAGReference],
    ) -> List[DataFinding]:
        """LLM 综合搜索抽取结果与 RAG 上下文生成解读。"""
        try:
            system_prompt = (
                "你是金融数据分析助手。根据网页搜索抽取的 metrics、search_refs 与 RAG 上下文，"
                "输出 2-3 条 key_findings。不得编造 metrics 中不存在的数字；"
                "evidence 中应注明搜索来源或 RAG 口径。"
            )
            user_prompt = json.dumps(
                {
                    "query": query,
                    "metrics": stats.metrics,
                    "search_refs": [r.model_dump() for r in stats.search_refs],
                    "rag_context": [r.model_dump() for r in rag_refs],
                },
                ensure_ascii=False,
                indent=2,
            )
            response = await self.get_llm_response(user_prompt, system_prompt)
            parsed = _parse_findings(response)
            if parsed:
                return parsed
        except Exception as e:
            logger.warning(f"[{self.name}] LLM 解读失败，使用占位结论: {e}")

        return _fallback_findings(stats.metrics, stats.search_refs)


def _parse_findings(response: str) -> List[DataFinding]:
    text = response.strip()
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
    try:
        data = json.loads(text.strip())
        items = data if isinstance(data, list) else data.get("key_findings", [])
        return [DataFinding(**item) for item in items]
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


def _fallback_findings(
    metrics: Dict[str, Any],
    search_refs: List[SearchReference],
) -> List[DataFinding]:
    source_hint = search_refs[0].title if search_refs else "搜索结果"
    findings = []
    for key, value in list(metrics.items())[:3]:
        findings.append(
            DataFinding(
                title=key,
                value=str(value),
                evidence=f"来自网页搜索抽取（来源：{source_hint}）",
            )
        )
    return findings
