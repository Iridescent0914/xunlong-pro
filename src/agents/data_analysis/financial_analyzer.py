"""金融数据分析模块

输入：网页搜索输出（search_results）+ RAG 检索输出（rag_refs）
输出：AnalysisOutput（metrics / tables / key_findings / methodology）

默认走算法路径：结构化抽取 -> 指标计算 -> 建表；
LLM 仅作为可选补充（use_llm=True 时启用）。
"""

import json
import os
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
    select_relevant_search_results_with_fallback,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MOCK_SEARCH_PATH = PROJECT_ROOT / "fixtures" / "mock_search.json"
MOCK_STATS_PATH = PROJECT_ROOT / "fixtures" / "mock_stats.json"

LLMCallback = Callable[[str, str], Awaitable[str]]


class FinancialAnalyzer:
    """金融数据分析：search_results + rag_refs -> 算法计算 -> 结构化结果。"""

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
                    "[FinancialAnalyzer] 无与 prompt 匹配的搜索结果，尝试使用 RAG 证据"
                )
                if rag_refs:
                    rag_output = _analyze_with_rag_only(query, rag_refs)
                    rag_output.methodology = (
                        selection_meta.methodology_note() + rag_output.methodology
                    )
                    return rag_output
                results = []

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
        )


def _analyze_with_algorithm(
    query: str,
    search_results: List[Dict[str, Any]],
    search_refs: List[SearchReference],
    rag_refs: List[RAGReference],
    use_mock: bool = False,
    selection_meta: Optional[SearchSelectionMeta] = None,
    total_search_count: Optional[int] = None,
) -> AnalysisOutput:
    """算法主路径：抽取 -> 计算 -> 建表 -> 结论。"""
    if not search_results and not use_mock:
        if rag_refs:
            logger.info("[FinancialAnalyzer] 搜索结果为空，使用 RAG 证据生成基础分析")
            return _analyze_with_rag_only(query, rag_refs)
        logger.warning("[FinancialAnalyzer] 搜索结果为空，无法基于搜索正文进行数据分析")
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


def _analyze_with_rag_only(query: str, rag_refs: List[RAGReference]) -> AnalysisOutput:
    findings: List[DataFinding] = []
    for index, ref in enumerate(rag_refs[:5], 1):
        content = " ".join((ref.content or "").split())
        if not content:
            continue
        findings.append(
            DataFinding(
                title=f"RAG 年报证据 {index}",
                value=_classify_rag_evidence(content),
                evidence=f"{content[:260]}（来源：{ref.source}，相关度：{ref.score:.2f}）",
            )
        )

    methodology = (
        "网页搜索结果为空或未通过相关性筛选；"
        "本次金融数据分析基于本地年报 RAG 检索片段生成基础结论。"
        "由于缺少可用网页搜索正文，未执行网页数值抽取和趋势图表生成。"
    )
    return AnalysisOutput(
        metrics={
            "rag_evidence_count": len(rag_refs),
            "avg_rag_score": round(
                sum(ref.score for ref in rag_refs) / len(rag_refs),
                4,
            ) if rag_refs else 0.0,
        },
        tables=[
            DataTable(
                title="RAG 年报证据摘要",
                columns=["序号", "来源", "相关度", "片段摘要"],
                rows=[
                    [
                        i + 1,
                        ref.source,
                        round(ref.score, 4),
                        " ".join((ref.content or "").split())[:180],
                    ]
                    for i, ref in enumerate(rag_refs[:8])
                ],
            )
        ] if rag_refs else [],
        key_findings=findings,
        methodology=methodology,
        search_refs=[],
        rag_refs=rag_refs,
    )


def _classify_rag_evidence(content: str) -> str:
    if any(term in content for term in ["营业收入", "收入", "营收"]):
        return "收入变化证据"
    if any(term in content for term in ["风险", "流动性", "信用", "汇率"]):
        return "风险因素证据"
    if any(term in content for term in ["行业格局", "竞争优势", "核心竞争力"]):
        return "行业与竞争证据"
    return "年报证据"


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
    tables = [DataTable(**table) for table in mock_raw.get("tables", [])]
    source_hint = search_refs[0].title if search_refs else "mock_stats.json"
    findings = [
        DataFinding(
            title=key,
            value=str(value),
            evidence=f"mock 回退数据，参考来源：{source_hint}",
        )
        for key, value in list(metrics.items())[:3]
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
    for index, result in enumerate(search_results[:5], 1):
        title = result.get("title", "")
        body = result.get("content") or result.get("snippet") or ""
        parts.append(f"[{index}] {title}\n{body[:1500]}")
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
                "search_refs": [ref.model_dump() for ref in search_refs],
                "rag_context": [ref.model_dump() for ref in rag_refs],
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
        tables = [DataTable(**table) for table in data.get("tables", [])]
        findings = [DataFinding(**finding) for finding in data.get("key_findings", [])]
        return AnalysisOutput(
            metrics=data.get("metrics", {}),
            tables=tables,
            key_findings=findings,
            methodology=data.get("methodology", ""),
        )
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
