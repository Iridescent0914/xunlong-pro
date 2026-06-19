"""将 search_results 与 RAG evidence pack 统一为 AnalysisInput。"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .schemas import (
    AnalysisInput,
    EvidenceItem,
    RAGEvidencePack,
    RAGReference,
    RAGSummary,
    SearchReference,
    UnifiedEvidence,
    WebSearchEvidencePack,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MOCK_SEARCH_PATH = PROJECT_ROOT / "fixtures" / "mock_search.json"


def load_mock_search() -> List[Dict[str, Any]]:
    if not MOCK_SEARCH_PATH.exists():
        return []
    return json.loads(MOCK_SEARCH_PATH.read_text(encoding="utf-8"))


def resolve_search_results(
    search_results: List[Dict[str, Any]],
    use_mock: bool = False,
) -> List[Dict[str, Any]]:
    if use_mock or not search_results:
        logger.info("[EvidenceAdapter] 使用 mock_search.json")
        return load_mock_search()
    return search_results


def search_result_to_evidence(item: Dict[str, Any], index: int) -> EvidenceItem:
    """协调器 search_results 条目 → 统一 EvidenceItem。"""
    content = item.get("content") or item.get("snippet") or ""
    return EvidenceItem(
        evidence_id=item.get("evidence_id") or f"web_{index:03d}",
        doc_type=item.get("doc_type") or "web_article",
        title=item.get("title", ""),
        date=item.get("extracted_time") or item.get("date"),
        source=item.get("source") or "web",
        url=item.get("url"),
        content=content,
        summary=(item.get("snippet") or content)[:300],
        score=max(0.0, 1.0 - (index - 1) * 0.05),
        origin="web_search",
        metadata={
            "search_query": item.get("search_query", ""),
            "rank": item.get("rank", index),
            "has_full_content": item.get("has_full_content", False),
        },
    )


def build_web_pack(
    query: str,
    search_results: List[Dict[str, Any]],
) -> WebSearchEvidencePack:
    evidence = [
        search_result_to_evidence(item, i + 1)
        for i, item in enumerate(search_results)
    ]
    return WebSearchEvidencePack(query=query, evidence=evidence)


def parse_rag_evidence_pack(raw: Dict[str, Any]) -> RAGEvidencePack:
    """解析 RAG 组 evidence pack JSON。"""
    # 简单校验输入形状，记录缺失的关键字段
    missing = validate_rag_pack(raw)
    if missing:
        logger.warning(f"[EvidenceAdapter] RAG pack 缺失字段: {missing}")
    evidence_items: List[EvidenceItem] = []
    for i, ev in enumerate(raw.get("evidence") or []):
        evidence_items.append(
            EvidenceItem(
                evidence_id=ev.get("evidence_id") or f"rag_{i:03d}",
                doc_type=ev.get("doc_type", ""),
                title=ev.get("title", ""),
                date=ev.get("date"),
                source=ev.get("source", ""),
                url=ev.get("url"),
                content=ev.get("content", ""),
                summary=ev.get("summary", ""),
                score=float(ev.get("score") or 0.0),
                origin="financial_rag",
                metadata=ev.get("metadata") or {},
            )
        )

    summary_raw = raw.get("rag_summary") or {}
    rag_summary = RAGSummary(
        key_points=summary_raw.get("key_points") or [],
        risk_factors=summary_raw.get("risk_factors") or [],
        data_gaps=summary_raw.get("data_gaps") or [],
    )

    return RAGEvidencePack(
        source="financial_rag",
        query=raw.get("query", ""),
        normalized_query=raw.get("normalized_query", ""),
        entities=raw.get("entities") or {},
        retrieval_scope=raw.get("retrieval_scope") or {},
        evidence=evidence_items,
        rag_summary=rag_summary,
        quality=raw.get("quality") or {},
    )


def validate_rag_pack(raw: Dict[str, Any]) -> List[str]:
    """检查 RAG pack 是否包含最重要的字段，返回缺失字段列表。"""
    required = ["source", "query", "evidence", "rag_summary"]
    missing = [k for k in required if k not in (raw or {})]
    return missing


def rag_pack_to_refs(pack: RAGEvidencePack) -> List[RAGReference]:
    """evidence pack → 下游兼容 rag_refs。"""
    refs: List[RAGReference] = []
    for ev in pack.evidence:
        refs.append(
            RAGReference(
                content=ev.summary or ev.content,
                source=ev.source or ev.title,
                score=ev.score,
                doc_type=ev.doc_type,
                title=ev.title,
                evidence_id=ev.evidence_id,
            )
        )
    return refs


def build_search_refs(evidence: List[EvidenceItem], limit: int = 5) -> List[SearchReference]:
    refs: List[SearchReference] = []
    for ev in evidence[:limit]:
        refs.append(
            SearchReference(
                title=ev.title,
                url=ev.url or "",
                snippet=(ev.summary or ev.content)[:300],
            )
        )
    return refs


def build_unified_evidence(
    query: str,
    web_pack: WebSearchEvidencePack,
    rag_pack: Optional[RAGEvidencePack] = None,
) -> UnifiedEvidence:
    rag_pack = rag_pack or RAGEvidencePack()
    entities = rag_pack.entities or {}
    all_evidence = web_pack.evidence + rag_pack.evidence

    return UnifiedEvidence(
        query=query or web_pack.query or rag_pack.query,
        company_name=entities.get("company_name", ""),
        ticker=entities.get("ticker", ""),
        web_evidence=web_pack.evidence,
        rag_evidence=rag_pack.evidence,
        all_evidence=all_evidence,
        rag_summary=rag_pack.rag_summary,
    )


def build_analysis_input(
    query: str,
    search_results: List[Dict[str, Any]],
    rag_pack: Optional[RAGEvidencePack] = None,
    use_mock: bool = False,
    topic: str = "general",
) -> AnalysisInput:
    """主入口：search_results + RAG pack → AnalysisInput。"""
    resolved = resolve_search_results(search_results, use_mock)
    web_pack = build_web_pack(query, resolved)
    rag_pack = rag_pack or RAGEvidencePack()
    unified = build_unified_evidence(query, web_pack, rag_pack)

    return AnalysisInput(
        query=query,
        company=unified.company_name,
        ticker=unified.ticker,
        topic=topic,
        unified=unified,
        search_refs=build_search_refs(unified.web_evidence),
        rag_refs=rag_pack_to_refs(rag_pack),
        use_mock=use_mock or not search_results,
    )


def combine_evidence_text(unified: UnifiedEvidence, limit: int = 8) -> str:
    """合并证据正文，供规则/LLM 分析。"""
    parts: List[str] = []
    for i, ev in enumerate(unified.all_evidence[:limit], 1):
        tag = "网页" if ev.origin == "web_search" else "RAG"
        body = ev.content or ev.summary
        parts.append(f"[{i}][{tag}] {ev.title}\n{body[:1500]}")
    return "\n\n".join(parts)
