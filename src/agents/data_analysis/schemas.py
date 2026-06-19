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
    source_type: Literal["web_rag", "mock", "excel", "csv", "database", "text"] = "web_rag"
    metrics: Dict[str, Any] = Field(default_factory=dict)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    charts: List[Dict[str, Any]] = Field(default_factory=list)
    key_findings: List[DataFinding] = Field(default_factory=list)
    methodology: str = ""
    rag_refs: List[RAGReference] = Field(default_factory=list)
    search_refs: List[SearchReference] = Field(default_factory=list)
    message: Optional[str] = None


class EvidenceItem(BaseModel):
    evidence_id: str = Field(default="", description="证据唯一ID")
    doc_type: str = Field(default="", description="文档类型，如 news/sec_filing")
    title: str = Field(default="")
    date: Optional[str] = Field(default=None)
    source: str = Field(default="")
    url: Optional[str] = Field(default=None)
    content: Optional[str] = Field(default=None)
    summary: Optional[str] = Field(default=None)
    score: float = Field(default=0.0)
    origin: str = Field(default="")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RAGSummary(BaseModel):
    key_points: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    data_gaps: List[str] = Field(default_factory=list)


class RAGEvidencePack(BaseModel):
    source: str = Field(default="financial_rag")
    query: str = Field(default="")
    normalized_query: Optional[str] = Field(default=None)
    entities: Dict[str, Any] = Field(default_factory=dict)
    retrieval_scope: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    rag_summary: RAGSummary = Field(default_factory=RAGSummary)
    quality: Dict[str, Any] = Field(default_factory=dict)


class WebSearchEvidencePack(BaseModel):
    query: str = Field(default="")
    evidence: List[EvidenceItem] = Field(default_factory=list)


class UnifiedEvidence(BaseModel):
    query: str = Field(default="")
    company_name: Optional[str] = Field(default="")
    ticker: Optional[str] = Field(default="")
    web_evidence: List[EvidenceItem] = Field(default_factory=list)
    rag_evidence: List[EvidenceItem] = Field(default_factory=list)
    all_evidence: List[EvidenceItem] = Field(default_factory=list)
    rag_summary: RAGSummary = Field(default_factory=RAGSummary)


class AnalysisInput(BaseModel):
    query: str = Field(default="")
    company: Optional[str] = Field(default=None)
    ticker: Optional[str] = Field(default=None)
    topic: str = Field(default="general")
    unified: UnifiedEvidence = Field(default_factory=UnifiedEvidence)
    search_refs: List[SearchReference] = Field(default_factory=list)
    rag_refs: List[RAGReference] = Field(default_factory=list)
    use_mock: bool = Field(default=False)
