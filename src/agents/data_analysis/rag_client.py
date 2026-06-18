"""RAG 检索客户端（骨架默认 Mock，Day 2 替换为 RAG 组真实 API）。"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .schemas import RAGReference

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MOCK_RAG_PATH = PROJECT_ROOT / "fixtures" / "mock_rag.json"


class RAGClient:
    def __init__(self, use_mock: Optional[bool] = None, api_url: Optional[str] = None):
        if use_mock is None:
            use_mock = os.getenv("DATA_ANALYSIS_RAG_MOCK", "true").lower() != "false"
        self.use_mock = use_mock
        self.api_url = api_url or os.getenv("FINANCIAL_RAG_API_URL", "")

    async def retrieve(self, query: str, top_k: int = 5) -> List[RAGReference]:
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
        return [RAGReference(**item) for item in raw]
