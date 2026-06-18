"""金融数据分析模块

输入：网页搜索输出（search_results）+ RAG 检索输出（rag_refs）
输出：AnalysisOutput（metrics / tables / key_findings / methodology）
"""

import json
import re
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from loguru import logger

from .analysis_output import AnalysisOutput
from .schemas import DataFinding, DataTable, RAGReference, SearchReference

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MOCK_SEARCH_PATH = PROJECT_ROOT / "fixtures" / "mock_search.json"
MOCK_STATS_PATH = PROJECT_ROOT / "fixtures" / "mock_stats.json"

LLMCallback = Callable[[str, str], Awaitable[str]]


class FinancialAnalyzer:
    """金融数据分析：综合 search_results 与 rag_refs 产出结构化分析结果。"""

    async def analyze(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        rag_refs: List[RAGReference],
        use_mock: bool = False,
        llm_callback: Optional[LLMCallback] = None,
    ) -> AnalysisOutput:
        results = _resolve_search_results(search_results, use_mock)
        search_refs = _build_search_refs(results)
        search_text = _combine_search_text(results)

        logger.info(
            f"[FinancialAnalyzer] 开始分析：{len(results)} 条搜索 + {len(rag_refs)} 条 RAG"
        )

        if llm_callback:
            llm_output = await _analyze_with_llm(
                query, search_text, search_refs, rag_refs, llm_callback
            )
            if llm_output:
                llm_output.rag_refs = rag_refs
                llm_output.search_refs = search_refs
                return llm_output

        return _analyze_with_rules(results, search_refs, rag_refs, search_text)


def _resolve_search_results(
    search_results: List[Dict[str, Any]],
    use_mock: bool,
) -> List[Dict[str, Any]]:
    if use_mock or not search_results:
        logger.info("[FinancialAnalyzer] 使用 mock_search.json")
        return _load_mock_search()
    return search_results


def _load_mock_search() -> List[Dict[str, Any]]:
    if not MOCK_SEARCH_PATH.exists():
        return []
    return json.loads(MOCK_SEARCH_PATH.read_text(encoding="utf-8"))


def _load_mock_stats_raw() -> Dict[str, Any]:
    if not MOCK_STATS_PATH.exists():
        return {"metrics": {}, "tables": [], "data_summary": "mock fallback"}
    return json.loads(MOCK_STATS_PATH.read_text(encoding="utf-8"))


def _build_search_refs(search_results: List[Dict[str, Any]]) -> List[SearchReference]:
    refs = []
    for item in search_results[:5]:
        snippet = item.get("snippet") or item.get("content") or ""
        refs.append(
            SearchReference(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=snippet[:300] if snippet else "",
            )
        )
    return refs


def _combine_search_text(search_results: List[Dict[str, Any]]) -> str:
    parts = []
    for i, r in enumerate(search_results[:5], 1):
        title = r.get("title", "")
        body = r.get("content") or r.get("snippet") or ""
        parts.append(f"[{i}] {title}\n{body[:1500]}")
    return "\n\n".join(parts)


async def _analyze_with_llm(
    query: str,
    search_text: str,
    search_refs: List[SearchReference],
    rag_refs: List[RAGReference],
    llm_callback: LLMCallback,
) -> Optional[AnalysisOutput]:
    try:
        system_prompt = (
            "你是金融数据分析专家。请综合「网页搜索内容」与「RAG 知识库片段」完成分析。\n"
            "要求：\n"
            "1. metrics 中的数字必须来自搜索正文，不得编造\n"
            "2. 使用 RAG 片段校验指标口径与解读是否合理\n"
            "3. key_findings 的 evidence 须引用搜索来源标题或 RAG 来源\n"
            "4. 严格输出 JSON，字段：metrics, tables, key_findings, methodology"
        )
        user_prompt = json.dumps(
            {
                "query": query,
                "search_content": search_text,
                "search_refs": [r.model_dump() for r in search_refs],
                "rag_context": [r.model_dump() for r in rag_refs],
                "output_schema": {
                    "metrics": {"revenue_yoy": 0.23},
                    "tables": [
                        {
                            "title": "表名",
                            "columns": ["列1", "列2"],
                            "rows": [["值1", "值2"]],
                        }
                    ],
                    "key_findings": [
                        {"title": "结论", "value": "23%", "evidence": "依据"}
                    ],
                    "methodology": "分析口径说明",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        response = await llm_callback(user_prompt, system_prompt)
        parsed = _parse_analysis_response(response)
        if parsed:
            logger.info("[FinancialAnalyzer] LLM 分析完成")
            return parsed
    except Exception as e:
        logger.warning(f"[FinancialAnalyzer] LLM 分析失败，回退规则分析: {e}")
    return None


def _analyze_with_rules(
    search_results: List[Dict[str, Any]],
    search_refs: List[SearchReference],
    rag_refs: List[RAGReference],
    search_text: str,
) -> AnalysisOutput:
    metrics = _extract_metrics_from_text(search_text)
    mock_raw = _load_mock_stats_raw()
    tables = [DataTable(**t) for t in mock_raw.get("tables", [])]

    if not metrics:
        metrics = mock_raw.get("metrics", {})

    source_hint = search_refs[0].title if search_refs else "搜索结果"
    findings = [
        DataFinding(
            title=k,
            value=str(v),
            evidence=f"从搜索正文抽取，来源：{source_hint}",
        )
        for k, v in list(metrics.items())[:3]
    ]

    methodology = (
        f"基于 {len(search_results)} 条搜索结果与 {len(rag_refs)} 条 RAG 片段分析"
        f"（规则回退模式）"
    )
    return AnalysisOutput(
        metrics=metrics,
        tables=tables,
        key_findings=findings,
        methodology=methodology,
        search_refs=search_refs,
        rag_refs=rag_refs,
    )


def _extract_metrics_from_text(text: str) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {}
    patterns = [
        (r"同比增长\s*(\d+(?:\.\d+)?)\s*%", "revenue_yoy", 100),
        (r"毛利率\s*(\d+(?:\.\d+)?)\s*%", "gross_margin", 100),
        (r"资产负债率\s*(\d+(?:\.\d+)?)\s*%", "debt_ratio", 100),
    ]
    for pattern, key, divisor in patterns:
        match = re.search(pattern, text)
        if match:
            metrics[key] = float(match.group(1)) / divisor
    return metrics


def _parse_analysis_response(response: str) -> Optional[AnalysisOutput]:
    text = response.strip()
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:]
    try:
        data = json.loads(text.strip())
        tables = [DataTable(**t) for t in data.get("tables", [])]
        findings = [DataFinding(**f) for f in data.get("key_findings", [])]
        return AnalysisOutput(
            metrics=data.get("metrics", {}),
            tables=tables,
            key_findings=findings,
            methodology=data.get("methodology", ""),
        )
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
