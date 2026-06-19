"""金融数据分析智能体内部：分析阶段产出（尚未含 charts）。"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from .schemas import DataFinding, DataTable, RAGReference, SearchReference


class AnalysisOutput(BaseModel):
    """FinancialAnalyzer.analyze() 的返回值（分析阶段，不含 charts）。

    由 search_results + rag_refs 经算法或 LLM 分析后产出，
    供 chart_builder 画图，再由 DataAnalysisAgent 包装为 DataAnalysisResult。
    """

    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="核心数值指标，键为指标名（如 revenue_yoy），值为数字；"
        "比率类为小数（0.23 表示 23%），绝对值类带业务单位（万元/亿元等）",
    )
    tables: List[DataTable] = Field(
        default_factory=list,
        description="结构化汇总表，如分季度营收、抽取指标明细；"
        "供报告展示，并作为 chart_builder 画折线/柱状图的输入",
    )
    key_findings: List[DataFinding] = Field(
        default_factory=list,
        description="分析结论列表，每条含 title/value/evidence；"
        "evidence 须能追溯到 search_refs 或 rag_refs",
    )
    methodology: str = Field(
        default="",
        description="分析口径与数据来源说明，如算法路径、抽取条数、RAG 参考文档",
    )
    search_refs: List[SearchReference] = Field(
        default_factory=list,
        description="分析所依据的网页搜索来源（title/url/snippet），"
        "通常取 Top-5 搜索结果",
    )
    rag_refs: List[RAGReference] = Field(
        default_factory=list,
        description="分析所参考的 RAG 知识库片段（指标定义、术语口径等），"
        "用于校验解读，不替代搜索中的事实数据",
    )
