"""金融数据分析智能体：网页搜索 → LLM 数值表 → 图表 → 报告。"""

import json
import os
import re
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
            rag_pack = await self._retrieve_rag_pack(query, use_mock=use_mock)
            rag_refs = _rag_pack_to_refs(rag_pack)
            rag_evidence = list(getattr(rag_pack, "evidence", []) or [])
            if not search_results and not rag_evidence:
                return self._empty_result("No web search results or RAG evidence; skipped data analysis", skipped=True)

            return await self._process_llm_search(
                query,
                search_results,
                rag_pack=rag_pack,
                rag_refs=rag_refs,
                use_mock=use_mock,
            )

        except Exception as e:
            logger.error(f"[{self.name}] 分析失败: {e}")
            return self._error_envelope(str(e))

    async def _retrieve_rag_pack(self, query: str, *, use_mock: bool = False) -> Optional[Any]:
        if not query:
            return None
        try:
            from .rag_client import RAGClient

            pack = await RAGClient(use_mock=use_mock).retrieve_pack(
                query,
                top_k=_rag_top_k(),
            )
            hit_count = len(getattr(pack, "evidence", []) or [])
            logger.info(f"[DataAnalysisAgent] RAG retrieved {hit_count} evidence items")
            return pack
        except Exception as exc:
            logger.warning(f"[DataAnalysisAgent] RAG retrieval failed; continuing with web search only: {exc}")
            return None

    async def _process_llm_search(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        *,
        rag_pack: Optional[Any] = None,
        rag_refs: Optional[List[Any]] = None,
        use_mock: bool = False,
    ) -> Dict[str, Any]:
        rag_evidence = list(getattr(rag_pack, "evidence", []) or [])
        llm_out = await extract_table_from_search(
            query,
            search_results,
            self.get_llm_response,
            rag_evidence=rag_evidence,
        )
        if not llm_out:
            return self._empty_result(
                f"Read {len(search_results)} web results and {len(rag_evidence)} RAG evidence items, but LLM did not produce a numeric table",
                search_refs=_refs_to_dicts(_build_search_refs(search_results)),
                rag_refs=_refs_to_dicts(rag_refs or []),
            )

        return self._success_envelope(
            _build_result_from_llm(
                llm_out,
                rag_refs=rag_refs or [],
                use_mock=use_mock,
            )
        )

    def _empty_result(
        self,
        message: str,
        search_refs: Optional[List[Dict[str, Any]]] = None,
        rag_refs: Optional[List[Dict[str, Any]]] = None,
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
                rag_refs=rag_refs or [],
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
    rag_refs: Optional[List[Any]],
    use_mock: bool,
) -> DataAnalysisResult:
    table = llm_out.table
    conclusion = llm_out.conclusion
    conclusion = _normalize_table_and_conclusion(table, conclusion)
    table_dict = table.model_dump()
    has_rows = bool(table.rows)
    refs = _refs_to_dicts(llm_out.search_refs)
    rag_ref_dicts = _refs_to_dicts(rag_refs or [])
    methodology = llm_out.methodology
    if rag_ref_dicts and "RAG" not in methodology.upper():
        methodology = f"{methodology}; also used {len(rag_ref_dicts)} RAG evidence items."

    chart = (
        build_chart_for_table(table, chart_id=_DEFAULT_CHART_ID) if has_rows else None
    )
    charts = [chart] if chart else []

    key_findings: List[DataFinding] = []
    if conclusion:
        key_findings.append(
            DataFinding(
                title="分析结论",
                value=conclusion[:200],
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
                "conclusion": conclusion,
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
        methodology=methodology,
        rag_refs=rag_ref_dicts,
        search_refs=refs,
        analysis_table=table_dict if has_rows else None,
        analysis_conclusion=conclusion,
    )




_BILLION_RE = re.compile(
    r"(?i)(?:US\$|\$)?\s*(\d+(?:\.\d+)?)\s*(?:b|bn|billion)(?:\s*(?:\u7f8e\u5143|\u7f8e\u91d1|dollars|usd))?(?=$|[^A-Za-z])"
)
_GROSS_MARGIN_CN = "\u6bdb\u5229\u7387"
_PROFIT_MARGIN_CN = "\u5229\u6da6\u7387"
_NET_MARGIN_CN = "\u51c0\u5229\u7387"
_OPERATING_MARGIN_CN = "\u8425\u4e1a\u5229\u6da6\u7387"
_OPERATING_MARGIN_ALT_CN = "\u7ecf\u8425\u5229\u6da6\u7387"
_NOT_GROSS_MARGIN_CN = "\u975e\u6bdb\u5229\u7387"
_VALUE_COL_CN = "\u6570\u503c"
_USD_100M_CN = "\u4ebf\u7f8e\u5143"
_APPROX_CN = "\u7ea6"


def _normalize_table_and_conclusion(table: Any, conclusion: str) -> str:
    replacements: List[tuple[str, str]] = []
    columns = [str(c) for c in getattr(table, "columns", []) or []]
    rows = list(getattr(table, "rows", []) or [])
    normalized_rows = []
    for row in rows:
        normalized_row, row_replacements, margin_kind = _normalize_row(columns, row)
        replacements.extend(row_replacements)
        if margin_kind == "profit_margin":
            conclusion = _replace_gross_margin_phrase(
                conclusion,
                f"{_PROFIT_MARGIN_CN}\uff08profit margin\uff0c{_NOT_GROSS_MARGIN_CN}\uff09",
            )
        elif margin_kind == "operating_margin":
            conclusion = _replace_gross_margin_phrase(
                conclusion,
                f"{_OPERATING_MARGIN_CN}\uff08operating margin\uff0c{_NOT_GROSS_MARGIN_CN}\uff09",
            )
        normalized_rows.append(normalized_row)
    table.rows = normalized_rows

    conclusion = _normalize_money_text(conclusion, replacements)
    return conclusion


def _replace_gross_margin_phrase(text: str, replacement: str) -> str:
    return re.sub(
        rf"{_GROSS_MARGIN_CN}(?=\u4e3a|\u662f|\u8fbe|\u8fbe\u5230|\u8f83|\u540c\u6bd4|\uff0c|,|\s|$)",
        replacement,
        text,
    )


def _normalize_row(columns: List[str], row: Any) -> tuple[List[Any], List[tuple[str, str]], str]:
    values = list(row or [])
    source_text = " ".join(str(cell) for cell in values)
    lower = source_text.lower()
    replacements: List[tuple[str, str]] = []
    margin_kind = ""

    metric_idx = 0 if values else -1
    if metric_idx >= 0:
        metric = str(values[metric_idx])
        if _has_profit_margin(lower) and _GROSS_MARGIN_CN in metric:
            values[metric_idx] = f"{_PROFIT_MARGIN_CN}\uff08profit margin\uff0c{_NOT_GROSS_MARGIN_CN}\uff09"
            margin_kind = "profit_margin"
        elif _has_operating_margin(lower) and _GROSS_MARGIN_CN in metric:
            values[metric_idx] = f"{_OPERATING_MARGIN_CN}\uff08operating margin\uff0c{_NOT_GROSS_MARGIN_CN}\uff09"
            margin_kind = "operating_margin"
        elif _has_gross_margin(lower) and _GROSS_MARGIN_CN not in metric:
            values[metric_idx] = f"{_GROSS_MARGIN_CN}\uff08gross margin\uff09"
            margin_kind = "gross_margin"

    value_idx = _column_index(columns, _VALUE_COL_CN, default=1)
    if 0 <= value_idx < len(values):
        normalized, money_replacements = _normalize_money_value(str(values[value_idx]))
        values[value_idx] = normalized
        replacements.extend(money_replacements)

    return values, replacements, margin_kind


def _column_index(columns: List[str], keyword: str, *, default: int = -1) -> int:
    for i, col in enumerate(columns):
        if keyword in col:
            return i
    return default


def _has_profit_margin(text: str) -> bool:
    return "profit margin" in text or "net margin" in text or _NET_MARGIN_CN in text


def _has_operating_margin(text: str) -> bool:
    return (
        "operating margin" in text
        or "operating income margin" in text
        or _OPERATING_MARGIN_CN in text
        or _OPERATING_MARGIN_ALT_CN in text
    )


def _has_gross_margin(text: str) -> bool:
    return "gross margin" in text or "gross margin percentage" in text or _GROSS_MARGIN_CN in text


def _normalize_money_value(text: str) -> tuple[str, List[tuple[str, str]]]:
    replacements: List[tuple[str, str]] = []

    def repl(match: re.Match[str]) -> str:
        raw_num = match.group(1).replace(",", "")
        num = float(raw_num)
        usd_b = raw_num
        compact_usd_b = _format_number(num)
        cny_yi = _format_number(num * 10)
        for candidate in dict.fromkeys([usd_b, compact_usd_b]):
            replacements.extend([
                (f"{candidate} {_USD_100M_CN}", f"{cny_yi} {_USD_100M_CN}"),
                (f"{candidate}{_USD_100M_CN}", f"{cny_yi}{_USD_100M_CN}"),
            ])
        return f"${usd_b}B\uff08{_APPROX_CN}{cny_yi}{_USD_100M_CN}\uff09"

    normalized = _BILLION_RE.sub(repl, text)
    return normalized, replacements


def _normalize_money_text(text: str, replacements: List[tuple[str, str]]) -> str:
    text = _normalize_money_value(text)[0]
    for wrong, right in replacements:
        text = text.replace(wrong, right)
    return text


def _format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.1f}".rstrip("0").rstrip(".")


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


def _rag_pack_to_refs(rag_pack: Optional[Any]) -> List[Any]:
    if not rag_pack:
        return []
    try:
        from .evidence_adapter import rag_pack_to_refs

        return rag_pack_to_refs(rag_pack)
    except Exception as exc:
        logger.warning(f"[DataAnalysisAgent] Failed to convert RAG refs: {exc}")
        return []


def _rag_top_k() -> int:
    raw = os.getenv("DATA_ANALYSIS_RAG_TOP_K", "5")
    try:
        return max(1, int(raw))
    except ValueError:
        return 5

