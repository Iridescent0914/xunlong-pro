"""DuckDuckGo"""

import asyncio
import os
import re
from typing import List, Optional
from playwright.async_api import Page
from loguru import logger
from urllib.parse import quote_plus, urljoin

import httpcore
import httpx
from bs4 import BeautifulSoup

from .base import BaseSearcher
from ..models import SearchLink


class DuckDuckGoSearcher(BaseSearcher):
    """DuckDuckGo - supports both Playwright and httpx"""

    @property
    def name(self) -> str:
        return "duckduckgo"

    async def search(
        self,
        page: Page,
        query: str,
        time_filter: Optional[str] = None,
        region: str = "cn-zh"
    ) -> List[SearchLink]:
        """
        DuckDuckGo (Playwright mode - kept for backward compat).

        Args:
            page: Playwright Page
            query:
            time_filter:
            region:

        Returns:

        """
        try:
            logger.info(f"DuckDuckGo: {query}")

            mapped_filter = None
            filter_map = {"day": "d", "week": "w", "month": "m", "year": "y"}
            if time_filter:
                mapped_filter = filter_map.get(time_filter.lower())

            params = f"?q={quote_plus(query)}&ia=web&kl={region}"
            if mapped_filter:
                params += f"&df={mapped_filter}"

            search_url = f"https://duckduckgo.com/{params}"

            await page.goto(search_url, wait_until="domcontentloaded")
            await asyncio.sleep(4)

            possible_selectors = [
                '[data-testid="result"]', 'article[data-testid="result"]',
                '.result', '.web-result', '[data-layout="organic"]',
                'article', '.result__body', 'div[data-domain]', 'h3 a[href]'
            ]

            result_selector = None
            result_count = 0
            for selector in possible_selectors:
                try:
                    count = await page.locator(selector).count()
                    if count > 0:
                        result_selector = selector
                        result_count = count
                        logger.debug(f": {selector}, : {count}")
                        break
                except Exception as e:
                    logger.debug(f" {selector} : {e}")
                    continue

            if result_count == 0:
                page_content = await page.content()
                logger.debug(f": {len(page_content)}")
                logger.debug(f": {await page.title()}")
                raise Exception("")

            results = []
            result_elements = await page.locator(result_selector).all()
            for i, element in enumerate(result_elements[:self.topk]):
                try:
                    title_element = element.locator('a[data-testid="result-title-a"]')
                    if await title_element.count() == 0:
                        title_element = element.locator('h2 a, h3 a, .result__a')

                    title = await title_element.inner_text()
                    url = await title_element.get_attribute('href')

                    snippet = ""
                    for snippet_selector in ['[data-result="snippet"]', '.result__snippet',
                                             '[data-testid="result-snippet"]', '.result-snippet']:
                        snippet_element = element.locator(snippet_selector)
                        if await snippet_element.count() > 0:
                            snippet = await snippet_element.inner_text()
                            break

                    if url and title:
                        results.append(SearchLink(
                            url=url, title=title.strip(),
                            snippet=snippet.strip() if snippet else None))
                        logger.debug(f" {i+1}: {title[:50]}...")

                except Exception as e:
                    logger.warning(f" {i+1} : {e}")
                    continue

            logger.info(f" {len(results)} ")
            return results

        except Exception as e:
            logger.error(f"DuckDuckGo: {e}")
            return []

    PROXY_ERROR_TYPES = frozenset({
        "EndOfStream",
        "ProxyError",
        "ConnectTimeout",
        "ConnectError",
        "RemoteProtocolError",
        "TLSUpgradeError",
    })

    def _is_proxy_failure(self, exc: Exception) -> bool:
        """判断异常是否由代理问题引起（可尝试直连兜底）。"""
        exc_name = type(exc).__name__
        if exc_name in self.PROXY_ERROR_TYPES:
            return True
        # httpx/httpcore 系的代理错误
        if isinstance(exc, httpx.HTTPError):
            return True
        # anyio 底层网络错误（代理封站时最常见）
        exc_module = getattr(type(exc), "__module__", "")
        if "anyio" in exc_module or "httpcore" in exc_module:
            return True
        # 空消息 + 网络关键字
        if not str(exc).strip():
            keywords = ("Stream", "Connect", "Proxy", "TLS", "SSL", "Socket")
            if any(kw in exc_name for kw in keywords):
                return True
        return False

    async def search_with_httpx(
        self,
        query: str,
        max_results: int = 10,
        time_filter: Optional[str] = None,
        region: str = "cn-zh"
    ) -> List[SearchLink]:
        """
        DuckDuckGo - httpx-only (no browser needed, works on Windows).
        Uses html.duckduckgo.com which returns a simple, scrape-friendly HTML page.
        Falls back to direct connection if proxy fails.
        """
        try:
            return await self._search_httpx_impl(query, max_results, time_filter, region)
        except Exception as primary_exc:
            if self._is_proxy_failure(primary_exc):
                logger.warning(
                    f"[{self.name}] Proxy failed ({type(primary_exc).__name__}), "
                    "trying direct connection..."
                )
                try:
                    return await self._search_httpx_impl(
                        query, max_results, time_filter, region, use_proxy=False
                    )
                except Exception:
                    pass  # 兜底也失败，放弃
            return []

    async def _search_httpx_impl(
        self,
        query: str,
        max_results: int = 10,
        time_filter: Optional[str] = None,
        region: str = "cn-zh",
        use_proxy: bool = True,
    ) -> List[SearchLink]:
        """搜索实现：支持是否使用代理。"""

        logger.info(f"DuckDuckGo(httpx){'(proxy)' if use_proxy else '(direct)'}: {query}")

        mapped_filter = None
        filter_map = {"day": "d", "week": "w", "month": "m", "year": "y"}
        if time_filter:
            mapped_filter = filter_map.get(time_filter.lower())

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1",
            "Connection": "keep-alive",
        }

        proxy = None
        if use_proxy:
            for env_key in ["HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"]:
                val = os.environ.get(env_key)
                if val:
                    proxy = val
                    break

        httpx_kwargs: dict = {
            "headers": headers,
            "follow_redirects": True,
            "timeout": httpx.Timeout(30.0, connect=10.0),
        }
        if proxy:
            httpx_kwargs["proxy"] = proxy

        results: List[SearchLink] = []

        async with httpx.AsyncClient(**httpx_kwargs) as client:
            # Try html.duckduckgo.com lite endpoint first (simple HTML, no JS needed)
            lite_params = [("q", query)]
            if mapped_filter:
                lite_params.append(("df", mapped_filter))

            r = await client.get(
                "https://html.duckduckgo.com/html/",
                params=lite_params
            )
            r.raise_for_status()
            html = r.text

        soup = BeautifulSoup(html, "lxml")

        # html.duckduckgo.com uses class="result" and class="result__a"
        for result_div in soup.select(".result"):
            if len(results) >= max_results:
                break

            a_tag = result_div.select_one(".result__a")
            if not a_tag:
                continue

            href = a_tag.get("href", "")
            if not href:
                continue

            # href is //duckduckgo.com/l/?uddg=<real_url>&rut=...
            real_url = ""
            if "uddg=" in href:
                from urllib.parse import unquote, parse_qs, urlparse
                parsed = urlparse(href)
                qs = parse_qs(parsed.query)
                real_url = qs.get("uddg", [""])[0]
                real_url = unquote(real_url)
            elif href.startswith("http"):
                real_url = href

            if not real_url:
                continue

            title = a_tag.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            # snippet: second <a> tag or .result__snippet inside same result div
            snippet = ""
            snippet_el = result_div.select_one(".result__snippet")
            if snippet_el:
                snippet = snippet_el.get_text(strip=True)
            if not snippet:
                snippet_a_tags = result_div.select("a")
                for sa in snippet_a_tags[1:2]:
                    text = sa.get_text(strip=True)
                    if 20 < len(text) < 400:
                        snippet = text
                        break

            results.append(SearchLink(
                url=real_url,
                title=title,
                snippet=snippet if snippet else None
            ))
            logger.debug(f"  {len(results)}: {title[:50]}...")

        # If html.duckduckgo.com returns nothing, try main duckduckgo.com as fallback
        if not results:
            async with httpx.AsyncClient(**httpx_kwargs) as client:
                main_params = [("q", query), ("ia", "web"), ("kl", region)]
                if mapped_filter:
                    main_params.append(("df", mapped_filter))
                r = await client.get("https://duckduckgo.com/", params=main_params)
                r.raise_for_status()
                html = r.text

            soup = BeautifulSoup(html, "lxml")
            for a_tag in soup.select("a[href]"):
                if len(results) >= max_results:
                    break
                href = a_tag.get("href", "")
                if not href or "duckduckgo" in href or href.startswith("/"):
                    continue
                if any(x in href for x in ["privacy=", "about:", "mailto:", "#"]):
                    continue

                title = a_tag.get_text(strip=True)
                if not title or len(title) < 5:
                    continue

                results.append(SearchLink(
                    url=href, title=title, snippet=None
                ))

        logger.info(f"DuckDuckGo(httpx): {len(results)} ")
        return results
