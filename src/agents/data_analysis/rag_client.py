"""RAG 检索客户端。

默认只查询显式启用的真实 RAG 源；mock 仅用于测试和 demo。
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from loguru import logger

from .evidence_adapter import load_rag_evidence_pack, rag_pack_to_refs
from .schemas import RAGEvidencePack, RAGReference

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MOCK_RAG_PATH = PROJECT_ROOT / "fixtures" / "mock_rag.json"
LOCAL_RAG_SRC = PROJECT_ROOT / "RAG" / "src"
ANNUAL_TARGETS_PATH = PROJECT_ROOT / "RAG" / "config" / "targets.json"
DEFAULT_SYMBOL_ALIASES_PATH = PROJECT_ROOT / "financeRAG" / "rag" / "company_aliases.json"


class RAGClient:
    def __init__(
        self,
        use_mock: Optional[bool] = None,
        api_url: Optional[str] = None,
        annual_report_enabled: Optional[bool] = None,
        yahoo_enabled: Optional[bool] = None,
    ):
        # 外部传入优先，否则读环境变量
        if use_mock is None:
            use_mock = os.getenv("DATA_ANALYSIS_RAG_MOCK", "false").lower() == "true"
        self.use_mock = use_mock
        self.api_url = api_url or os.getenv("FINANCIAL_RAG_API_URL", "")
        self.local_enabled = (
            annual_report_enabled
            if annual_report_enabled is not None
            else os.getenv("ANNUAL_REPORT_RAG_ENABLED", "false").lower() == "true"
        )
        self.yahoo_enabled = (
            yahoo_enabled
            if yahoo_enabled is not None
            else os.getenv("YAHOO_FINANCE_RAG_ENABLED", "false").lower() == "true"
        )
        self.local_persist_dir = os.getenv(
            "ANNUAL_REPORT_RAG_PERSIST_DIR",
            str(PROJECT_ROOT / "RAG" / "data" / "chroma_db"),
        )
        self.local_collection = os.getenv(
            "ANNUAL_REPORT_RAG_COLLECTION",
            "annual_report_rag",
        )
        self.local_env_file = os.getenv(
            "ANNUAL_REPORT_RAG_ENV_FILE",
            str(PROJECT_ROOT / "financeRAG" / "rag" / ".env"),
        )
        self.yahoo_enabled = os.getenv("YAHOO_FINANCE_RAG_ENABLED", "false").lower() == "true"
        self.yahoo_persist_dir = os.getenv(
            "YAHOO_FINANCE_RAG_PERSIST_DIR",
            str(PROJECT_ROOT / "financeRAG" / "rag" / "chroma_db"),
        )
        self.yahoo_collection = os.getenv(
            "YAHOO_FINANCE_RAG_COLLECTION",
            "finance_rag",
        )
        self.yahoo_env_file = os.getenv(
            "YAHOO_FINANCE_RAG_ENV_FILE",
            str(PROJECT_ROOT / "financeRAG" / "rag" / ".env"),
        )
        self.symbol_aliases_file = os.getenv(
            "FINANCIAL_RAG_SYMBOL_ALIASES_FILE",
            str(DEFAULT_SYMBOL_ALIASES_PATH),
        )

    async def retrieve(self, query: str, top_k: int = 5) -> List[RAGReference]:
        if self.local_enabled or self.yahoo_enabled:
            pack = await self.retrieve_pack(query, top_k=top_k)
            return rag_pack_to_refs(pack)

        if self.use_mock:
            logger.info("[RAGClient] 使用 mock_rag.json（显式 mock 模式）")
            return self._load_mock()

        # TODO: RAG 组接入真实 HTTP API
        if self.api_url:
            logger.warning("[RAGClient] 真实 HTTP RAG API 未实现，跳过 RAG")
        else:
            logger.info("[RAGClient] 未启用 RAG 源，跳过 RAG 检索")
        return []

    def _load_mock(self) -> List[RAGReference]:
        if not MOCK_RAG_PATH.exists():
            return [
                RAGReference(
                    content="毛利率 = (营业收入 - 营业成本) / 营业收入",
                    source="指标口径.md",
                    score=0.95,
                )
            ]

        raw = json.loads(MOCK_RAG_PATH.read_text(encoding="utf-8"))
        pack = load_rag_evidence_pack(raw)
        return rag_pack_to_refs(pack)

    def _load_mock_pack(self, query: str, top_k: int = 5) -> RAGEvidencePack:
        if not MOCK_RAG_PATH.exists():
            return RAGEvidencePack(query=query)
        raw = json.loads(MOCK_RAG_PATH.read_text(encoding="utf-8"))
        pack = load_rag_evidence_pack(raw, query=query)
        if top_k and len(pack.evidence) > top_k:
            pack.evidence = pack.evidence[:top_k]
        return pack

    async def retrieve_pack(self, query: str, top_k: int = 5) -> RAGEvidencePack:
        """返回完整 RAG evidence pack。"""
        if self.local_enabled or self.yahoo_enabled:
            packs: List[RAGEvidencePack] = []
            if self.local_enabled:
                packs.append(self._query_local_annual_report_pack(query, top_k))
            if self.yahoo_enabled:
                packs.append(self._query_yahoo_finance_pack(query, top_k))

            merged = self._merge_packs(query, packs, top_k=None)
            if merged.evidence:
                return merged
            logger.warning("[RAGClient] 已启用 RAG 源，但未召回证据，返回空 RAG pack")
            return merged

        if self.use_mock:
            logger.info("[RAGClient] 使用 mock_rag.json（显式 mock pack 模式）")
            return self._load_mock_pack(query, top_k)

        if self.api_url:
            logger.warning("[RAGClient] 真实 HTTP RAG API 未实现，返回空 RAG pack")
        else:
            logger.info("[RAGClient] 未启用 RAG 源，返回空 RAG pack")
        return RAGEvidencePack(source="disabled", query=query)

    def _query_local_annual_report_pack(self, query: str, top_k: int) -> RAGEvidencePack:
        """Query local RAG/data/chroma_db and parse docs/rag输出格式.md evidence pack."""
        try:
            symbol_hint = _infer_query_symbol(query, self.symbol_aliases_file)
            annual_symbols = _annual_target_symbols()
            if symbol_hint and annual_symbols and symbol_hint not in annual_symbols:
                logger.info(
                    f"[RAGClient] 年报 RAG 未覆盖 {symbol_hint}，跳过年报库检索"
                )
                return RAGEvidencePack(source="annual_report_rag", query=query)

            if str(LOCAL_RAG_SRC) not in sys.path:
                sys.path.insert(0, str(LOCAL_RAG_SRC))
            from rag_reports.indexer import query_evidence_pack

            raw_pack = query_evidence_pack(
                query=query,
                persist_dir=self.local_persist_dir,
                collection_name=self.local_collection,
                env_file=self.local_env_file,
                top_k=top_k,
            )
            if symbol_hint:
                raw_pack["evidence"] = [
                    item
                    for item in raw_pack.get("evidence", [])
                    if _evidence_matches_symbol(item, symbol_hint)
                ]
            return load_rag_evidence_pack(raw_pack, query=query)
        except Exception as exc:
            logger.error(f"[RAGClient] 本地年报 RAG 查询失败: {exc}")
            return RAGEvidencePack(source="annual_report_rag", query=query)

    def _query_yahoo_finance_pack(self, query: str, top_k: int) -> RAGEvidencePack:
        """Query financeRAG/rag/chroma_db and normalize Yahoo Finance subset rows."""
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            from financeRAG.rag import RAGConfig, OpenAICompatibleEmbeddingClient

            config = RAGConfig.from_env(self.yahoo_env_file)
            embedding_client = OpenAICompatibleEmbeddingClient(
                api_key=config.embedding_api_key,
                base_url=config.embedding_base_url,
                model=config.embedding_model,
            )
            query_embedding = embedding_client.embed_texts([query])[0]

            chroma_client = chromadb.PersistentClient(path=self.yahoo_persist_dir)
            collection = chroma_client.get_collection(name=self.yahoo_collection)
            where = _build_yahoo_where(_infer_query_symbol(query, self.symbol_aliases_file))
            result = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )

            docs = result.get("documents", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0]
            evidence: List[Dict[str, Any]] = []
            scores: List[float] = []
            for index, (doc, metadata, distance) in enumerate(
                zip(docs, metadatas, distances),
                1,
            ):
                metadata = metadata or {}
                score = max(0.0, min(1.0, 1.0 - float(distance or 0.0)))
                scores.append(score)
                source = metadata.get("source") or "yahoo_finance_dataset"
                symbol = metadata.get("symbol") or metadata.get("ticker") or ""
                date = (
                    metadata.get("report_date")
                    or metadata.get("date")
                    or metadata.get("published_at")
                    or metadata.get("year")
                )
                evidence.append(
                    {
                        "evidence_id": metadata.get("doc_id") or f"yahoo_{index:03d}",
                        "doc_type": source,
                        "title": _yahoo_title(metadata, symbol, source, date),
                        "date": str(date) if date else None,
                        "source": "yahoo_finance_dataset",
                        "url": metadata.get("url"),
                        "ticker": symbol,
                        "content": doc or "",
                        "summary": _summarize_text(str(doc or ""), query),
                        "score": round(score, 4),
                        "metadata": metadata,
                    }
                )

            avg_score = sum(scores) / len(scores) if scores else 0.0
            return load_rag_evidence_pack(
                {
                    "source": "yahoo_finance_rag",
                    "query": query,
                    "normalized_query": query,
                    "entities": _infer_yahoo_entities(evidence),
                    "retrieval_scope": {
                        "doc_types": sorted(
                            {item["doc_type"] for item in evidence if item.get("doc_type")}
                        ),
                        "top_k": len(evidence),
                    },
                    "evidence": evidence,
                    "rag_summary": {
                        "key_points": [
                            f"{item.get('title', '')}: {item.get('summary', '')}"
                            for item in evidence[:3]
                        ],
                        "risk_factors": _extract_risk_keywords(evidence),
                        "data_gaps": [] if evidence else ["未检索到 Yahoo Finance 数据集证据。"],
                    },
                    "quality": {
                        "hit_count": len(evidence),
                        "avg_score": round(avg_score, 4),
                        "confidence": _confidence(avg_score, len(evidence)),
                        "warnings": [
                            "Yahoo Finance RAG 当前仅覆盖已选取的数据集子集，结论需结合年报和网页搜索校验。"
                        ] if evidence else [],
                    },
                },
                query=query,
            )
        except Exception as exc:
            logger.error(f"[RAGClient] Yahoo Finance RAG 查询失败: {exc}")
            return RAGEvidencePack(source="yahoo_finance_rag", query=query)

    def _merge_packs(
        self,
        query: str,
        packs: List[RAGEvidencePack],
        top_k: Optional[int] = None,
    ) -> RAGEvidencePack:
        evidence = []
        key_points = []
        risk_factors = []
        data_gaps = []
        warnings = []
        entities: Dict[str, Any] = {}
        doc_types = set()

        for pack in packs:
            if not pack:
                continue
            if pack.entities and not entities:
                entities = pack.entities
            for item in pack.evidence:
                evidence.append(item)
                if item.doc_type:
                    doc_types.add(item.doc_type)
            key_points.extend(pack.rag_summary.key_points)
            risk_factors.extend(pack.rag_summary.risk_factors)
            data_gaps.extend(pack.rag_summary.data_gaps)
            warnings.extend(pack.quality.get("warnings", []) if pack.quality else [])

        evidence.sort(key=lambda item: item.score, reverse=True)
        if top_k:
            evidence = evidence[:top_k]
        avg_score = (
            sum(item.score for item in evidence) / len(evidence)
            if evidence
            else 0.0
        )
        return RAGEvidencePack(
            source="multi_financial_rag",
            query=query,
            normalized_query=query,
            entities=entities,
            retrieval_scope={
                "doc_types": sorted(doc_types),
                "top_k": len(evidence),
                "sources": [
                    source
                    for source in [
                        "annual_report_rag" if self.local_enabled else "",
                        "yahoo_finance_rag" if self.yahoo_enabled else "",
                    ]
                    if source
                ],
            },
            evidence=evidence,
            rag_summary={
                "key_points": key_points[:6],
                "risk_factors": sorted(set(risk_factors))[:10],
                "data_gaps": data_gaps[:6],
            },
            quality={
                "hit_count": len(evidence),
                "avg_score": round(avg_score, 4),
                "confidence": _confidence(avg_score, len(evidence)),
                "warnings": list(dict.fromkeys(warnings)),
            },
        )


def _summarize_text(content: str, query: str = "", max_chars: int = 260) -> str:
    text = " ".join(content.split())
    if len(text) <= max_chars:
        return text
    anchors = [
        part.strip()
        for part in query.replace("，", " ").replace("、", " ").split()
        if len(part.strip()) >= 2
    ]
    anchors.extend(["revenue", "income", "growth", "risk", "margin", "guidance", "收入", "风险"])
    lower_text = text.lower()
    for anchor in anchors:
        pos = lower_text.find(anchor.lower())
        if pos >= 0:
            start = max(0, pos - 40)
            return text[start : start + max_chars]
    return text[:max_chars]


def _infer_query_symbol(query: str, aliases_file: Optional[str] = None) -> Optional[str]:
    text = (query or "").strip()
    lower = text.lower()

    explicit_patterns = [
        r"\bticker\s*[:=]?\s*([A-Z0-9.-]{1,10})\b",
        r"\bsymbol\s*[:=]?\s*([A-Z0-9.-]{1,10})\b",
        r"\b(?:NYSE|NASDAQ|AMEX|SSE|SZSE|HKEX)\s*[:：]\s*([A-Z0-9.-]{1,10})\b",
        r"\$([A-Z]{1,5}(?:-[A-Z]{1,2})?)\b",
    ]
    for pattern in explicit_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).upper()

    for alias, symbol in _load_symbol_aliases(aliases_file).items():
        if _alias_matches_query(alias, text, lower):
            return symbol
    return None


def _load_symbol_aliases(aliases_file: Optional[str]) -> Dict[str, str]:
    path = Path(aliases_file) if aliases_file else DEFAULT_SYMBOL_ALIASES_PATH
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(f"[RAGClient] 股票别名配置读取失败: {path} ({exc})")
        return {}

    aliases: Dict[str, str] = {}
    items = raw.get("aliases") if isinstance(raw, dict) else None
    if isinstance(items, dict):
        for symbol, names in items.items():
            symbol_text = str(symbol).upper().strip()
            if isinstance(names, str):
                names = [names]
            if not symbol_text or not isinstance(names, list):
                continue
            for name in names:
                alias = str(name).strip()
                if len(alias) >= 2:
                    aliases[alias] = symbol_text

    # Longer aliases first, so "Agilent Technologies" wins before "Agilent".
    return dict(
        sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True)
    )


def _alias_matches_query(alias: str, text: str, lower_text: str) -> bool:
    if not alias:
        return False
    if any("\u4e00" <= char <= "\u9fff" for char in alias):
        return alias in text

    escaped = re.escape(alias.lower())
    return re.search(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", lower_text) is not None


def _build_yahoo_where(symbol: Optional[str]) -> Optional[Dict[str, Any]]:
    if not symbol:
        return None
    return {"symbol": symbol}


def _annual_target_symbols() -> set:
    if not ANNUAL_TARGETS_PATH.exists():
        return set()
    try:
        raw = json.loads(ANNUAL_TARGETS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {
        str(item.get("symbol", "")).upper()
        for item in raw.get("companies", [])
        if item.get("symbol")
    }


def _evidence_matches_symbol(item: Dict[str, Any], symbol: str) -> bool:
    symbol = symbol.upper()
    metadata = item.get("metadata") or {}
    values = [
        item.get("ticker"),
        item.get("doc_id"),
        item.get("title"),
        item.get("company_name"),
        metadata.get("symbol"),
        metadata.get("ticker"),
        metadata.get("company"),
    ]
    return any(symbol in str(value).upper() for value in values if value)


def _yahoo_title(
    metadata: Dict[str, Any],
    symbol: str,
    source: str,
    date: Any,
) -> str:
    title = metadata.get("title") or metadata.get("headline")
    if title:
        return str(title)
    parts = [part for part in [symbol, source, str(date) if date else ""] if part]
    return " ".join(parts) or "Yahoo Finance dataset chunk"


def _infer_yahoo_entities(evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not evidence:
        return {}
    first = evidence[0]
    metadata = first.get("metadata") or {}
    return {
        "company_name": metadata.get("company") or metadata.get("company_name") or "",
        "ticker": first.get("ticker") or "",
        "market": metadata.get("market") or metadata.get("exchange") or "",
    }


def _extract_risk_keywords(evidence: List[Dict[str, Any]]) -> List[str]:
    keywords = ["risk", "uncertainty", "decline", "margin", "debt", "风险", "下滑", "利润率"]
    found: List[str] = []
    for item in evidence:
        text = f"{item.get('title', '')} {item.get('content', '')}".lower()
        for keyword in keywords:
            if keyword.lower() in text and keyword not in found:
                found.append(keyword)
    return found[:8]


def _confidence(avg_score: float, hit_count: int) -> str:
    if hit_count >= 8 and avg_score >= 0.7:
        return "high"
    if hit_count >= 4 and avg_score >= 0.55:
        return "medium"
    return "low"
