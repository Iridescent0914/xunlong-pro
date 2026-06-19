from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

import chromadb
from dotenv import load_dotenv

from financeRAG.rag.embedding_client import OpenAICompatibleEmbeddingClient
from financeRAG.rag.jsonl_loader import ProcessedDocument, iter_processed_documents


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def make_embedding_client(env_file: str | None = None) -> OpenAICompatibleEmbeddingClient:
    if env_file and Path(env_file).exists():
        load_dotenv(env_file, override=False)
    return OpenAICompatibleEmbeddingClient(
        api_key=_env("EMBEDDING_API_KEY", os.getenv("DASHSCOPE_API_KEY")),
        base_url=_env(
            "EMBEDDING_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        model=_env("EMBEDDING_MODEL", "text-embedding-v4").replace(" ", ""),
    )


def build_index(
    jsonl_path: str,
    persist_dir: str,
    collection_name: str,
    env_file: str | None = None,
    reset: bool = False,
    batch_size: int = 10,
    resume: bool = True,
) -> Dict[str, int]:
    client = make_embedding_client(env_file)
    chroma_client = chromadb.PersistentClient(path=persist_dir)
    if reset:
        try:
            chroma_client.delete_collection(collection_name)
        except Exception:
            pass
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    existing_ids = _load_existing_ids(collection) if resume and not reset else set()
    indexed = 0
    skipped = 0
    total = 0
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    docs = iter_processed_documents(jsonl_path, pattern="*.jsonl")
    for batch in _batched_unindexed(docs, batch_size, existing_ids):
        total += len(batch)
        skipped += sum(1 for doc in batch if doc.doc_id in existing_ids)
        batch = [doc for doc in batch if doc.doc_id not in existing_ids]
        if not batch:
            continue

        embeddings = client.embed_texts([doc.content for doc in batch])
        collection.upsert(
            ids=[doc.doc_id for doc in batch],
            documents=[doc.content for doc in batch],
            embeddings=embeddings,
            metadatas=[doc.metadata for doc in batch],
        )
        indexed += len(batch)
        existing_ids.update(doc.doc_id for doc in batch)

    return {
        "indexed_documents": indexed,
        "skipped_existing_documents": skipped,
        "seen_documents": total,
        "collection_count": collection.count(),
    }


def _batched_unindexed(
    docs: Iterable[ProcessedDocument],
    batch_size: int,
    existing_ids: Set[str],
) -> Iterable[List[ProcessedDocument]]:
    batch: List[ProcessedDocument] = []
    for doc in docs:
        batch.append(doc)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def _load_existing_ids(collection, page_size: int = 5000) -> Set[str]:
    ids: Set[str] = set()
    offset = 0
    while True:
        result = collection.get(limit=page_size, offset=offset, include=[])
        page_ids = result.get("ids", [])
        if not page_ids:
            break
        ids.update(str(item) for item in page_ids)
        if len(page_ids) < page_size:
            break
        offset += page_size
    return ids


def query_index(
    query: str,
    persist_dir: str,
    collection_name: str,
    env_file: str | None = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    client = make_embedding_client(env_file)
    chroma_client = chromadb.PersistentClient(path=persist_dir)
    collection = chroma_client.get_collection(collection_name)
    query_embedding = client.embed_texts([query])[0]
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    rows: List[Dict[str, Any]] = []
    for index, doc in enumerate(result.get("documents", [[]])[0]):
        rows.append(
            {
                "content": doc,
                "metadata": result.get("metadatas", [[]])[0][index],
                "distance": result.get("distances", [[]])[0][index],
            }
        )
    return rows


def build_evidence_pack(
    query: str,
    rows: List[Dict[str, Any]],
    normalized_query: str = "",
    entities: Optional[Dict[str, Any]] = None,
    top_k: Optional[int] = None,
) -> Dict[str, Any]:
    """Convert Chroma query rows to docs/rag输出格式.md evidence pack."""

    entities = entities or _infer_entities(rows)
    evidence: List[Dict[str, Any]] = []
    scores: List[float] = []

    selected_rows = rows[:top_k] if top_k else rows
    for index, row in enumerate(selected_rows, 1):
        metadata = row.get("metadata") or {}
        distance = float(row.get("distance") or 0.0)
        score = max(0.0, min(1.0, 1.0 - distance))
        scores.append(score)
        symbol = metadata.get("symbol", "")
        year = metadata.get("report_year", "")
        chunk_index = metadata.get("chunk_index", index)
        page_start = metadata.get("page_start", "")
        page_end = metadata.get("page_end", page_start)
        evidence.append(
            {
                "evidence_id": f"rag_{symbol}_{year}_{chunk_index}",
                "doc_id": f"{symbol}_annual_report_{year}",
                "doc_type": metadata.get("report_type") or "annual_report",
                "title": metadata.get("title") or f"{metadata.get('company', '')} {year} Annual Report",
                "date": str(year) if year != "" else None,
                "source": metadata.get("source") or "annual_report_pdf",
                "url": metadata.get("source_url"),
                "ticker": symbol,
                "company_name": metadata.get("company", ""),
                "chunk_id": chunk_index,
                "content": row.get("content", ""),
                "summary": _summarize_chunk(str(row.get("content", "")), query),
                "score": round(score, 4),
                "metadata": {
                    "country": metadata.get("country"),
                    "page_start": page_start,
                    "page_end": page_end,
                    "local_pdf": metadata.get("local_pdf"),
                    "jsonl_file": metadata.get("jsonl_file"),
                    "jsonl_line": metadata.get("jsonl_line"),
                    "language": _infer_language(str(row.get("content", ""))),
                },
            }
        )

    avg_score = sum(scores) / len(scores) if scores else 0.0
    return {
        "source": "financial_rag",
        "query": query,
        "normalized_query": normalized_query or query,
        "entities": entities,
        "retrieval_scope": {
            "doc_types": ["annual_report"],
            "top_k": len(selected_rows),
        },
        "evidence": evidence,
        "rag_summary": {
            "key_points": _extract_key_points(evidence),
            "risk_factors": _extract_risk_factors(evidence),
            "data_gaps": _detect_data_gaps(evidence),
        },
        "quality": {
            "hit_count": len(evidence),
            "avg_score": round(avg_score, 4),
            "confidence": _confidence(avg_score, len(evidence)),
            "warnings": _quality_warnings(evidence),
        },
    }


def query_evidence_pack(
    query: str,
    persist_dir: str,
    collection_name: str,
    env_file: str | None = None,
    top_k: int = 5,
    normalized_query: str = "",
    entities: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    rows = query_index(
        query=query,
        persist_dir=persist_dir,
        collection_name=collection_name,
        env_file=env_file,
        top_k=top_k,
    )
    return build_evidence_pack(
        query=query,
        rows=rows,
        normalized_query=normalized_query,
        entities=entities,
        top_k=top_k,
    )


def print_query_results(rows: List[Dict[str, Any]]) -> None:
    for index, row in enumerate(rows, 1):
        metadata = row["metadata"]
        print("=" * 80)
        print(
            f"{index}. {metadata.get('company')} {metadata.get('report_year')} "
            f"p.{metadata.get('page_start')}-{metadata.get('page_end')} "
            f"distance={row['distance']:.4f}"
        )
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
        print(str(row["content"])[:900])


def _infer_entities(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {}
    metadata = rows[0].get("metadata") or {}
    return {
        "company_name": metadata.get("company", ""),
        "ticker": metadata.get("symbol", ""),
        "market": metadata.get("country", ""),
    }


def _summarize_chunk(content: str, query: str = "", max_chars: int = 260) -> str:
    text = " ".join(content.split())
    if len(text) <= max_chars:
        return text

    anchors = _summary_anchors(query)
    lower_text = text.lower()
    positions = [
        lower_text.find(anchor.lower())
        for anchor in anchors
        if anchor and lower_text.find(anchor.lower()) >= 0
    ]
    if positions:
        start = max(0, min(positions) - 40)
        return text[start : start + max_chars]
    return text[:max_chars]


def _summary_anchors(query: str) -> List[str]:
    anchors = [part.strip() for part in query.replace("，", " ").replace("、", " ").split()]
    anchors.extend(
        [
            "行业格局",
            "趋势",
            "竞争优势",
            "核心竞争力",
            "经营风险",
            "风险",
            "营业收入",
            "收入",
        ]
    )
    seen: Set[str] = set()
    result: List[str] = []
    for anchor in anchors:
        if len(anchor) < 2 or anchor in seen:
            continue
        seen.add(anchor)
        result.append(anchor)
    return result


def _infer_language(content: str) -> str:
    zh_chars = sum(1 for char in content[:500] if "\u4e00" <= char <= "\u9fff")
    return "zh" if zh_chars >= 10 else "en"


def _extract_key_points(evidence: List[Dict[str, Any]], limit: int = 3) -> List[str]:
    points: List[str] = []
    for item in evidence[:limit]:
        title = item.get("title", "")
        page = item.get("metadata", {}).get("page_start", "")
        summary = item.get("summary", "")
        points.append(f"{title} 第{page}页：{summary}")
    return points


def _extract_risk_factors(evidence: List[Dict[str, Any]]) -> List[str]:
    keywords = ["风险", "竞争", "需求", "监管", "汇率", "流动性", "信用", "supply", "regulation", "risk"]
    factors: List[str] = []
    for item in evidence:
        text = f"{item.get('title', '')} {item.get('content', '')}".lower()
        for keyword in keywords:
            if keyword.lower() in text and keyword not in factors:
                factors.append(keyword)
    return factors[:8]


def _detect_data_gaps(evidence: List[Dict[str, Any]]) -> List[str]:
    if not evidence:
        return ["未检索到匹配的年报证据。"]
    years = sorted({str(item.get("date")) for item in evidence if item.get("date")})
    if len(years) < 2:
        return ["当前检索结果覆盖年份较少，趋势判断需要更多年份证据。"]
    return []


def _confidence(avg_score: float, hit_count: int) -> str:
    if hit_count >= 5 and avg_score >= 0.7:
        return "high"
    if hit_count >= 3 and avg_score >= 0.55:
        return "medium"
    return "low"


def _quality_warnings(evidence: List[Dict[str, Any]]) -> List[str]:
    warnings: List[str] = []
    if evidence:
        warnings.append("PDF 文本由自动抽取生成，表格和页眉页脚可能存在噪声。")
    return warnings
