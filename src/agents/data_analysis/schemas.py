"""金融数据分析智能体输出契约（与 search_analyzer 的 analysis_results 分离）。"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class DataFinding(BaseModel):
    """一条业务解读结论（由 LLM + RAG 生成，数值须引用 metrics）。"""

    title: str = Field(description="结论标题，如：营收同比增长")
    value: str = Field(description="结论值，如：23%")
    evidence: str = Field(description="依据说明")


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


class ProcessedStats(BaseModel):
    """成员 1（数据引擎）产出：仅含确定性计算结果，不含 LLM 解读。"""

    metrics: Dict[str, Any] = Field(default_factory=dict)
    tables: List[DataTable] = Field(default_factory=list)
    data_summary: str = ""


class DataAnalysisResult(BaseModel):
    """数据分析智能体最终输出，写入 state['data_analysis_results']。"""

    status: Literal["success", "error", "skipped"]
    source_type: Literal["excel", "csv", "database", "mock"] = "mock"
    metrics: Dict[str, Any] = Field(default_factory=dict)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    charts: List[Dict[str, Any]] = Field(default_factory=list)
    key_findings: List[DataFinding] = Field(default_factory=list)
    methodology: str = ""
    rag_refs: List[RAGReference] = Field(default_factory=list)
    message: Optional[str] = None
