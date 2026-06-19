"""RAG 检索客户端（骨架默认 Mock，Day 2 替换为 RAG 组真实 API）。"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .evidence_adapter import load_rag_evidence_pack, rag_pack_to_refs
from .schemas import RAGEvidencePack, RAGReference

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MOCK_RAG_PATH = PROJECT_ROOT / "fixtures" / "mock_rag.json"
LOCAL_RAG_SRC = PROJECT_ROOT / "RAG" / "src"


class RAGClient:
    def __init__(self, use_mock: Optional[bool] = None, api_url: Optional[str] = None):
        if use_mock is None:
            use_mock = os.getenv("DATA_ANALYSIS_RAG_MOCK", "true").lower() != "false"
        self.use_mock = use_mock
        self.api_url = api_url or os.getenv("FINANCIAL_RAG_API_URL", "")
        self.local_enabled = os.getenv("ANNUAL_REPORT_RAG_ENABLED", "false").lower() == "true"
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

    async def retrieve(self, query: str, top_k: int = 5) -> List[RAGReference]:
        if self.local_enabled:
            pack = await self.retrieve_pack(query, top_k=top_k)
            return rag_pack_to_refs(pack)

        if self.use_mock or not self.api_url:
            logger.info("[RAGClient] 使用 mock_rag.json（骨架模式）")
            return self._load_mock()

        # TODO: RAG 组接入真实 HTTP API
        logger.warning("[RAGClient] 真实 API 未实现，回退 mock")
        return self._load_mock()

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
        """返回完整 RAG evidence pack（mock 或未来 HTTP API）。"""
        if self.local_enabled:
            return self._query_local_annual_report_pack(query, top_k)

        if self.use_mock or not self.api_url:
            logger.info("[RAGClient] 使用 mock_rag.json（pack 模式）")
            return self._load_mock_pack(query, top_k)

        logger.warning("[RAGClient] 真实 API 未实现，回退 mock pack")
        return self._load_mock_pack(query, top_k)

    def _query_local_annual_report_pack(self, query: str, top_k: int) -> RAGEvidencePack:
        """Query local RAG/data/chroma_db and parse docs/rag输出格式.md evidence pack."""
        try:
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
            return load_rag_evidence_pack(raw_pack, query=query)
        except Exception as exc:
            logger.error(f"[RAGClient] 本地年报 RAG 查询失败，回退 mock: {exc}")
            return self._load_mock_pack(query, top_k)
