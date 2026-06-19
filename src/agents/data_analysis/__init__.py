"""金融数据分析智能体模块。"""

from .data_analysis_agent import DataAnalysisAgent
from .file_analyzer import FileDataAnalyzer
from .schemas import DataAnalysisResult, SearchReference


def __getattr__(name):
    """Lazy-load optional/heavy analysis classes."""

    if name == "DataAnalysisAgent":
        from .data_analysis_agent import DataAnalysisAgent

        return DataAnalysisAgent
    if name == "FinancialAnalyzer":
        from .financial_analyzer import FinancialAnalyzer

        return FinancialAnalyzer
    if name == "FileDataAnalyzer":
        from .file_analyzer import FileDataAnalyzer

        return FileDataAnalyzer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "DataAnalysisAgent",
    "DataAnalysisResult",
    "FileDataAnalyzer",
    "SearchReference",
]
