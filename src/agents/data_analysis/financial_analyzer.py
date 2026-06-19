"""金融数据分析模块

输入：网页搜索输出（search_results）+ RAG 检索输出（rag_refs）
输出：AnalysisOutput（metrics / tables / key_findings / methodology）

默认走算法路径：结构化抽取 → 指标计算 → 建表；
LLM 仅作为可选补充（use_llm=True 时启用）。
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from loguru import logger

from .analysis_output import AnalysisOutput
from .metrics_engine import compute_analysis
from .schemas import DataFinding, DataTable, RAGReference, SearchReference
from .search_extractor import extract_from_search_results
from .search_relevance import (
    SearchSelectionMeta,
    entity_terms_from_query,
    expand_candidates_for_extraction,
    select_relevant_search_results_with_fallback,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MOCK_SEARCH_PATH = PROJECT_ROOT / "fixtures" / "mock_search.json"
MOCK_STATS_PATH = PROJECT_ROOT / "fixtures" / "mock_stats.json"

LLMCallback = Callable[[str, str], Awaitable[str]]


class FinancialAnalyzer:
    """金融数据分析：search_results + rag_refs → 算法计算 → 结构化结果。"""

    async def analyze(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        rag_refs: List[RAGReference],
        use_mock: bool = False,
        llm_callback: Optional[LLMCallback] = None,
        use_llm: Optional[bool] = None,
    ) -> AnalysisOutput:
        results = _resolve_search_results(search_results, use_mock)
        selection_meta: Optional[SearchSelectionMeta] = None
        if not use_mock and query and results:
            results, selection_meta = select_relevant_search_results_with_fallback(
                query, results
            )
            if selection_meta.selected_count == 0:
                logger.warning(
                    f"[FinancialAnalyzer] 无与 prompt 相关的搜索结果，跳过分析"
                )
                return AnalysisOutput(
                    metrics={},
                    tables=[],
                    key_findings=[],
                    methodology=selection_meta.methodology_note(),
                    search_refs=[],
                    rag_refs=rag_refs,
                )

        search_refs = _build_search_refs(results)

        if use_llm is None:
            use_llm = os.getenv("FINANCIAL_ANALYSIS_USE_LLM", "false").lower() == "true"

        search_source = "mock_search.json" if use_mock else "网页搜索"
        logger.info(
            f"[FinancialAnalyzer] 开始分析：{len(results)} 条搜索（来源={search_source}）"
            f" + {len(rag_refs)} 条 RAG（模式={'LLM' if use_llm else '算法'}）"
        )

        if use_llm and llm_callback:
            search_text = _combine_search_text(results)
            llm_output = await _analyze_with_llm(
                query, search_text, search_refs, rag_refs, llm_callback
            )
            if llm_output:
                llm_output.rag_refs = rag_refs
                llm_output.search_refs = search_refs
                return llm_output
            logger.warning("[FinancialAnalyzer] LLM 分析失败，回退算法路径")

        return _analyze_with_algorithm(
            query,
            results,
            search_refs,
            rag_refs,
            use_mock=use_mock,
            selection_meta=selection_meta,
            total_search_count=len(search_results) if not use_mock else len(results),
            raw_search_results=search_results if not use_mock else None,
        )


def _analyze_with_algorithm(
    query: str,
    search_results: List[Dict[str, Any]],
    search_refs: List[SearchReference],
    rag_refs: List[RAGReference],
    use_mock: bool = False,
    selection_meta: Optional[SearchSelectionMeta] = None,
    total_search_count: Optional[int] = None,
    raw_search_results: Optional[List[Dict[str, Any]]] = None,
) -> AnalysisOutput:
    """算法主路径：抽取 → 计算 → 建表 → 结论。"""
    if not search_results and not use_mock:
        logger.warning("[FinancialAnalyzer] 搜索结果为空，跳过分析（未启用 mock）")
        return AnalysisOutput(
            metrics={},
            tables=[],
            key_findings=[],
            methodology="未获取到网页搜索结果，无法基于搜索正文进行数据分析。",
            search_refs=[],
            rag_refs=rag_refs,
        )

    entity_terms: List[str] = []
    if selection_meta and selection_meta.entity_terms:
        entity_terms = selection_meta.entity_terms
    elif query and not use_mock:
        entity_terms = entity_terms_from_query(query)

    points = extract_from_search_results(
        search_results,
        entity_terms=entity_terms or None,
    )

    if (
        not points
        and not use_mock
        and query
        and raw_search_results
    ):
        logger.info(
            "[FinancialAnalyzer] 当前候选无可抽取数值，从全部搜索中扩展抽取导向候选"
        )
        expanded, expanded_meta = expand_candidates_for_extraction(
            query, raw_search_results, max_items=8
        )
        if expanded:
            search_results = expanded
            selection_meta = expanded_meta
            search_refs = _build_search_refs(search_results)
            points = extract_from_search_results(
                search_results,
                entity_terms=entity_terms or None,
            )

    search_count = total_search_count if total_search_count is not None else len(search_results)
    metrics, tables, findings, methodology = compute_analysis(
        points, rag_refs, search_count=search_count
    )
    if selection_meta:
        methodology = selection_meta.methodology_note() + methodology

    if not _has_analysis_output(metrics, tables):
        if use_mock:
            logger.info("[FinancialAnalyzer] 算法未抽取到有效数据，使用 mock_stats 回退")
            return _analyze_with_mock_fallback(
                search_results, search_refs, rag_refs, methodology
            )
        logger.warning("[FinancialAnalyzer] 未能从搜索正文中抽取有效数值")
        return AnalysisOutput(
            metrics={},
            tables=[],
            key_findings=[],
            methodology=methodology + "（未能从搜索正文抽取有效数值）",
            search_refs=search_refs,
            rag_refs=rag_refs,
        )

    logger.info(
        f"[FinancialAnalyzer] 算法分析完成：{len(points)} 个数据点，"
        f"{len(metrics)} 个指标，{len(tables)} 张表"
    )
    return AnalysisOutput(
        metrics=metrics,
        tables=tables,
        key_findings=findings,
        methodology=methodology,
        search_refs=search_refs,
        rag_refs=rag_refs,
    )


def _has_analysis_output(metrics: Dict[str, Any], tables: List) -> bool:
    if tables:
        return True
    by_source = metrics.get("by_source") if isinstance(metrics, dict) else None
    if isinstance(by_source, dict) and by_source:
        return True
    return bool(metrics)


def _resolve_search_results(
    search_results: List[Dict[str, Any]],
    use_mock: bool,
) -> List[Dict[str, Any]]:
    if use_mock:
        logger.info("[FinancialAnalyzer] 显式启用 mock：使用 mock_search.json")
        return _load_mock_search()
    if not search_results:
        logger.warning(
            "[FinancialAnalyzer] 搜索结果为空，未回退 mock（请检查搜索是否成功或加 --mock-search）"
        )
        return []
    return search_results


def _load_mock_search() -> List[Dict[str, Any]]:
    if not MOCK_SEARCH_PATH.exists():
        return []
    return json.loads(MOCK_SEARCH_PATH.read_text(encoding="utf-8"))


def _load_mock_stats_raw() -> Dict[str, Any]:
    if not MOCK_STATS_PATH.exists():
        return {"metrics": {}, "tables": [], "data_summary": "mock fallback"}
    return json.loads(MOCK_STATS_PATH.read_text(encoding="utf-8"))


def _analyze_with_mock_fallback(
    search_results: List[Dict[str, Any]],
    search_refs: List[SearchReference],
    rag_refs: List[RAGReference],
    base_methodology: str,
) -> AnalysisOutput:
    mock_raw = _load_mock_stats_raw()
    metrics = mock_raw.get("metrics", {})
    tables = [DataTable(**t) for t in mock_raw.get("tables", [])]
    source_hint = search_refs[0].title if search_refs else "mock_stats.json"
    findings = [
        DataFinding(
            title=k,
            value=str(v),
            evidence=f"mock 回退数据，参考来源：{source_hint}",
        )
        for k, v in list(metrics.items())[:3]
    ]
    methodology = base_methodology + "（未抽取到有效数值，回退 mock_stats）"
    return AnalysisOutput(
        metrics=metrics,
        tables=tables,
        key_findings=findings,
        methodology=methodology,
        search_refs=search_refs,
        rag_refs=rag_refs,
    )


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
        logger.warning(f"[FinancialAnalyzer] LLM 分析失败: {e}")
    return None


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
