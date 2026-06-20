"""
Mock Search Loader - 用于离线测试，返回预设的假搜索结果。
"""

import json
from pathlib import Path
from typing import List, Optional
from loguru import logger

from ..models import SearchLink


class MockSearchLoader:
    """
    提供离线测试用的假搜索结果。
    目前返回空列表（需要时可在 mock_data/ 目录下放置 JSON 文件扩展）。
    """

    def __init__(self, mock_dir: Optional[Path] = None):
        self.mock_dir = mock_dir or Path(__file__).parent.parent.parent / "mock_data"
        self._cache: dict = {}

    def load(self, query: str, topk: int = 10) -> List[SearchLink]:
        """
        根据 query 返回假搜索结果。

        目前实现：优先从 mock_data/<normalized_query>.json 加载，
        若文件不存在则返回空列表（不影响主流程）。

        Args:
            query: 搜索关键词
            topk: 最大返回条数

        Returns:
            List[SearchLink]
        """
        cache_key = f"{query}:{topk}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        mock_file = self.mock_dir / f"{self._normalize(query)}.json"
        results: List[SearchLink] = []

        if mock_file.exists():
            try:
                with open(mock_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data.get("results", [])[:topk]:
                    results.append(SearchLink(**item))
                logger.info(f"[MockSearchLoader] 从 {mock_file.name} 加载 {len(results)} 条结果")
            except Exception as e:
                logger.warning(f"[MockSearchLoader] 加载 mock 文件失败: {e}")
        else:
            logger.debug(f"[MockSearchLoader] 无对应 mock 文件，返回空列表: {query}")

        self._cache[cache_key] = results
        return results

    @staticmethod
    def _normalize(text: str) -> str:
        """将 query 规范化为文件名（仅作 debug 用途）。"""
        import re
        return re.sub(r"[^\w]", "_", text.lower())[:40]
