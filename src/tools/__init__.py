"""

"""
from .time_tool import time_tool, TimeTool


def __getattr__(name):
    """Lazy-load network tools so lightweight imports do not initialize aiohttp."""

    if name == "WebSearcher":
        from .web_searcher import WebSearcher

        return WebSearcher
    if name == "ContentExtractor":
        from .content_extractor import ContentExtractor

        return ContentExtractor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "time_tool",
    "TimeTool", 
    "WebSearcher",
    "ContentExtractor"
]
