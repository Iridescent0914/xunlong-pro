"""金融数据分析智能体内部：分析阶段产出（尚未含 charts）。"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from .schemas import DataFinding, DataTable, RAGReference, SearchReference


class AnalysisOutput(BaseModel):
    """智能体 analyze() 方法的输出：分析结果（图表在 process 中另行生成）。"""

    metrics: Dict[str, Any] = Field(default_factory=dict)
    tables: List[DataTable] = Field(default_factory=list)
    key_findings: List[DataFinding] = Field(default_factory=list)
    methodology: str = ""
    search_refs: List[SearchReference] = Field(default_factory=list)
    rag_refs: List[RAGReference] = Field(default_factory=list)
