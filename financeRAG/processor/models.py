"""数据模型定义"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime


class DocumentMetadata(BaseModel):
    """文档元数据"""
    
    source: str  # "stock_news" 或 "stock_earning_call"
    symbol: str  # 股票代码
    title: Optional[str] = None
    publisher: Optional[str] = None
    report_date: Optional[str] = None
    source_type: Optional[str] = None  # STORY, REPORT等
    link: Optional[str] = None
    uuid: Optional[str] = None  # 用于 stock_news
    fiscal_year: Optional[int] = None  # 用于 earnings call
    fiscal_quarter: Optional[int] = None  # 用于 earnings call
    transcripts_id: Optional[int] = None  # 用于 earnings call
    speaker: Optional[str] = None  # 用于 earnings call
    original_index: int = 0  # 原始数据中的索引
    original_content_length: int = 0  # 清洗/切块前的正文长度
    text_segment_count: int = 0  # 段落数或转录片段数
    processed_at: str = ""  # 处理时间
    raw_record: Optional[Dict[str, Any]] = None  # 原始记录备份


class Document(BaseModel):
    """标准文档格式"""
    
    doc_id: str  # 文档唯一标识
    content: str  # 实际文本内容
    metadata: DocumentMetadata
    chunk_index: int = 0  # 切块索引 (如果是切块后的文档)
    chunk_size: int = 0  # 切块大小
    chunk_overlap: int = 0  # 切块重叠
    
    class Config:
        """Pydantic配置"""
        arbitrary_types_allowed = True
