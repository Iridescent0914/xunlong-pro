from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class Document:
    """RAG统一文档结构，适配电话会议、新闻两类数据"""
    chunk_id: str               # 唯一分片ID
    raw_text: str               # 原始文本
    clean_text: str             # 清洗后文本（用于向量化）
    metadata: Dict[str, Any]    # 金融元数据：symbol/时间/类型/发言人等
    source_type: str            # 数据源标识：earning_call / stock_news