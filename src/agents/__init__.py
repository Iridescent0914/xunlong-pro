""" - LangGraphagent"""

from .base import BaseAgent
from .query_optimizer import QueryOptimizerAgent
from .search_analyzer import SearchAnalyzerAgent
from .content_synthesizer import ContentSynthesizerAgent


def __getattr__(name):
    """Lazy-load coordinator classes to keep lightweight submodule imports cheap."""

    if name in {"AgentCoordinator", "DeepSearchCoordinator", "DeepSearchConfig"}:
        from .coordinator import AgentCoordinator, DeepSearchCoordinator, DeepSearchConfig

        values = {
            "AgentCoordinator": AgentCoordinator,
            "DeepSearchCoordinator": DeepSearchCoordinator,
            "DeepSearchConfig": DeepSearchConfig,
        }
        return values[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "BaseAgent",
    "QueryOptimizerAgent", 
    "SearchAnalyzerAgent",
    "ContentSynthesizerAgent",
    "AgentCoordinator",
    "DeepSearchCoordinator",
    "DeepSearchConfig",
]
