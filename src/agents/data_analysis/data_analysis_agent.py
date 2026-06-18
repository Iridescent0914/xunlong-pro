"""金融数据分析智能体（骨架：Mock 数据引擎 + Mock RAG + 可选 LLM 解读）。"""

import json
from typing import Any, Dict, List

from loguru import logger

from ..base import AgentConfig, BaseAgent
from ...llm import LLMManager, PromptManager
from .chart_builder import build_charts
from .data_engine import analyze
from .rag_client import RAGClient
from .schemas import DataAnalysisResult, DataFinding, RAGReference


class DataAnalysisAgent(BaseAgent):
    def __init__(
        self,
        llm_manager: LLMManager,
        prompt_manager: PromptManager = None,
        rag_client: RAGClient = None,
    ):
        config = AgentConfig(
            name="金融数据分析智能体",
            description="Excel/DB 金融数据分析，RAG 增强解读，输出结构化结论与图表",
            llm_config_name="default",
            temperature=0.3,
            max_tokens=3000,
        )
        super().__init__(llm_manager, prompt_manager, config)
        self.rag_client = rag_client or RAGClient()

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        query = input_data.get("query", "")
        data_sources = input_data.get("data_sources") or {}

        try:
            stats = await analyze(data_sources)
            rag_refs = await self.rag_client.retrieve(query)
            charts = build_charts(stats)
            findings = await self._interpret(query, stats, rag_refs)

            source_type = "mock" if data_sources.get("use_mock", True) else _detect_source_type(data_sources)
            result = DataAnalysisResult(
                status="success",
                source_type=source_type,
                metrics=stats.metrics,
                tables=[t.model_dump() for t in stats.tables],
                charts=charts,
                key_findings=findings,
                methodology=stats.data_summary or "骨架模式：mock 数据",
                rag_refs=rag_refs,
            )
            return {"status": "success", "agent": self.name, "result": result.model_dump()}

        except Exception as e:
            logger.error(f"[{self.name}] 分析失败: {e}")
            result = DataAnalysisResult(
                status="error",
                message=str(e),
            )
            return {"status": "error", "agent": self.name, "result": result.model_dump(), "error": str(e)}

    async def _interpret(self, query: str, stats, rag_refs: List[RAGReference]) -> List[DataFinding]:
        """LLM 解读；骨架阶段失败时返回基于 metrics 的占位结论。"""
        try:
            system_prompt = (
                "你是金融数据分析助手。根据给定的统计指标和 RAG 上下文，"
                "输出 2-3 条 key_findings。不得编造 metrics 中不存在的数字。"
            )
            user_prompt = json.dumps(
                {
                    "query": query,
                    "metrics": stats.metrics,
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

        return _fallback_findings(stats.metrics)


def _detect_source_type(data_sources: Dict[str, Any]) -> str:
    if data_sources.get("excel_path"):
        return "excel"
    if data_sources.get("csv_path"):
        return "csv"
    if data_sources.get("db_config"):
        return "database"
    return "mock"


def _parse_findings(response: str) -> List[DataFinding]:
    text = response.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text.strip())
        items = data if isinstance(data, list) else data.get("key_findings", [])
        return [DataFinding(**item) for item in items]
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


def _fallback_findings(metrics: Dict[str, Any]) -> List[DataFinding]:
    findings = []
    for key, value in list(metrics.items())[:3]:
        findings.append(
            DataFinding(
                title=key,
                value=str(value),
                evidence="来自数据引擎计算结果（骨架占位）",
            )
        )
    return findings
