"""金融数据分析智能体输出契约（与 search_analyzer 的 analysis_results 分离）。"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class DataFinding(BaseModel):
    """一条业务解读结论（由 LLM + 搜索 + RAG 生成，数值须可追溯）。"""

    title: str = Field(description="结论标题，如：营收同比增长")
    value: str = Field(description="结论值，如：23%")
    evidence: str = Field(description="依据说明，引用搜索来源或 RAG 口径")


class DataTable(BaseModel):
    """汇总表。"""

    title: str
    columns: List[str]
    rows: List[List[Any]]


class DataChart(BaseModel):
    """图表 spec，供 ECharts 渲染。"""

    type: Literal["bar", "line", "pie"]
    title: str
    spec: Dict[str, Any]


class RAGReference(BaseModel):
    """RAG 检索引用片段。"""

    content: str
    source: str
    score: float = 0.0


class SearchReference(BaseModel):
    """网页搜索来源引用。"""

    title: str
    url: str
    snippet: str = ""


class ProcessedStats(BaseModel):
    """搜索内容抽取产出：结构化指标与来源引用。"""

    metrics: Dict[str, Any] = Field(default_factory=dict)
    tables: List[DataTable] = Field(default_factory=list)
    data_summary: str = ""
    search_refs: List[SearchReference] = Field(default_factory=list)


class DataAnalysisResult(BaseModel):
    """数据分析智能体最终输出，写入 state['data_analysis_results']。"""

    status: Literal["success", "error", "skipped"]
    source_type: Literal["web_rag", "mock", "excel", "csv", "database"] = "web_rag"
    metrics: Dict[str, Any] = Field(default_factory=dict)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    charts: List[Dict[str, Any]] = Field(default_factory=list)
    key_findings: List[DataFinding] = Field(default_factory=list)
    methodology: str = ""
    rag_refs: List[RAGReference] = Field(default_factory=list)
    search_refs: List[SearchReference] = Field(default_factory=list)
    message: Optional[str] = None
