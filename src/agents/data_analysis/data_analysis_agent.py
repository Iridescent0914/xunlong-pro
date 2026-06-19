"""金融数据分析智能体：网页搜索 → LLM 数值表 → 图表 → 报告。"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from ..base import AgentConfig, BaseAgent
from ...llm import LLMManager, PromptManager
from .chart_builder import build_chart_for_table
from .llm_search_analyzer import (
    LLMSearchAnalysis,
    _build_search_refs,
    extract_table_from_search,
)
from .schemas import DataAnalysisResult, DataFinding

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MOCK_SEARCH_PATH = PROJECT_ROOT / "fixtures" / "mock_search.json"
_DEFAULT_CHART_ID = "chart_da_0"


class DataAnalysisAgent(BaseAgent):
    """智能体入口：将搜索结果交 LLM 抽取数值表，并组装最终输出。"""

    def __init__(
        self,
        llm_manager: LLMManager,
        prompt_manager: PromptManager = None,
    ):
        config = AgentConfig(
            name="金融数据分析智能体",
            description="基于网页搜索结果，由 LLM 抽取数值表格并可视化",
            llm_config_name="default",
            temperature=0.2,
            max_tokens=6000,
        )
        super().__init__(llm_manager, prompt_manager, config)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        query = input_data.get("query", "")
        use_mock = bool(input_data.get("use_mock", False))

        try:
            search_results = _resolve_search_results(
                input_data.get("search_results"), use_mock=use_mock
            )
            if not search_results:
                return self._empty_result("无网页搜索结果，已跳过数据分析", skipped=True)

            return await self._process_llm_search(query, search_results, use_mock=use_mock)

        except Exception as e:
            logger.error(f"[{self.name}] 分析失败: {e}")
            return self._error_envelope(str(e))

    async def _process_llm_search(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        *,
        use_mock: bool = False,
    ) -> Dict[str, Any]:
        llm_out = await extract_table_from_search(
            query, search_results, self.get_llm_response
        )
        if not llm_out:
            return self._empty_result(
                f"已读取 {len(search_results)} 条搜索结果，但 LLM 未能生成数值表格",
                search_refs=_refs_to_dicts(_build_search_refs(search_results)),
            )

        return self._success_envelope(
            _build_result_from_llm(llm_out, use_mock=use_mock)
        )

    def _empty_result(
        self,
        message: str,
        search_refs: Optional[List[Dict[str, Any]]] = None,
        *,
        skipped: bool = False,
    ) -> Dict[str, Any]:
        return self._success_envelope(
            DataAnalysisResult(
                status="skipped" if skipped else "success",
                source_type="web_rag",
                message=message,
                methodology=message,
                search_refs=search_refs or [],
            )
        )

    def _success_envelope(self, result: DataAnalysisResult) -> Dict[str, Any]:
        return {"status": "success", "agent": self.name, "result": result.model_dump()}

    def _error_envelope(self, message: str) -> Dict[str, Any]:
        return {
            "status": "error",
            "agent": self.name,
            "result": DataAnalysisResult(status="error", message=message).model_dump(),
            "error": message,
        }


def _resolve_search_results(
    search_results: Any,
    *,
    use_mock: bool,
) -> List[Dict[str, Any]]:
    results = list(search_results or [])
    if use_mock and not results:
        results = _load_mock_search()
    return results


def _build_result_from_llm(
    llm_out: LLMSearchAnalysis,
    *,
    use_mock: bool,
) -> DataAnalysisResult:
    table = llm_out.table
    table_dict = table.model_dump()
    has_rows = bool(table.rows)
    refs = _refs_to_dicts(llm_out.search_refs)

    chart = (
        build_chart_for_table(table, chart_id=_DEFAULT_CHART_ID) if has_rows else None
    )
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
                "table": table_dict,
                "chart": chart,
                "conclusion": llm_out.conclusion,
            }
        )

    message = None
    if not has_rows:
        message = llm_out.conclusion or "未从搜索结果中抽取到相关数值"

    return DataAnalysisResult(
        status="success",
        source_type="mock" if use_mock else "web_rag",
        message=message,
        metrics={},
        tables=[table_dict] if has_rows else [],
        charts=charts,
        key_findings=key_findings,
        source_blocks=source_blocks,
        methodology=llm_out.methodology,
        rag_refs=[],
        search_refs=refs,
        analysis_table=table_dict if has_rows else None,
        analysis_conclusion=llm_out.conclusion,
    )


def _refs_to_dicts(refs: List[Any]) -> List[Dict[str, Any]]:
    dumped: List[Dict[str, Any]] = []
    for ref in refs:
        if hasattr(ref, "model_dump"):
            dumped.append(ref.model_dump())
        elif isinstance(ref, dict):
            dumped.append(ref)
    return dumped


def _load_mock_search() -> List[Dict[str, Any]]:
    if not MOCK_SEARCH_PATH.exists():
        logger.warning(f"[DataAnalysisAgent] mock 搜索文件不存在: {MOCK_SEARCH_PATH}")
        return []
    return json.loads(MOCK_SEARCH_PATH.read_text(encoding="utf-8"))
