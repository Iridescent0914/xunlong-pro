"""
Search Manager - 统一搜索入口，支持 DuckDuckGo（httpx 模式，无需浏览器）。
"""

import asyncio
from typing import List, Optional
from loguru import logger

from ..searcher.duckduckgo import DuckDuckGoSearcher
from ..models import SearchLink


class SearchManager:
    """
    统一搜索管理器，对外提供 search() 接口。
    底层使用 DuckDuckGo（httpx 模式，Windows 友好）。
    """

    def __init__(self):
        self._engine = DuckDuckGoSearcher(topk=10)

    async def search(
        self,
        query: str,
        topk: int = 10,
        depth: str = "deep",
        time_filter: Optional[str] = None,
        region: str = "cn-zh",
    ) -> List[SearchLink]:
        """
        执行搜索。

        Args:
            query: 搜索关键词
            topk: 最大返回结果数（默认 10）
            depth: 搜索深度（surface/medium/deep），目前统一传给 time_filter
            time_filter: 时间过滤（day/week/month/year）
            region: 地区（默认 cn-zh）

        Returns:
            List[SearchLink]
        """
        # depth 参数可扩展，目前仅影响 time_filter 映射
        depth_filter_map = {
            "surface": "day",
            "medium": "week",
            "deep": None,
        }
        filter_to_use = time_filter or depth_filter_map.get(depth)

        logger.info(f"[SearchManager] query={query}, topk={topk}, depth={depth}, filter={filter_to_use}")

        try:
            results: List[SearchLink] = await self._engine.search_with_httpx(
                query=query,
                max_results=topk,
                time_filter=filter_to_use,
                region=region,
            )
            logger.info(f"[SearchManager] 搜索完成，返回 {len(results)} 条结果")
            return results
        except Exception as e:
            logger.error(f"[SearchManager] 搜索异常: {e}")
            return []
