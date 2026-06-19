"""Parquet 文件读取器 - 支持流式处理"""

import os
import pandas as pd
import json
from typing import Generator, Dict, Any, List, Optional
from loguru import logger
from tqdm import tqdm


class ParquetReader:
    """流式读取 Parquet 文件"""
    
    def __init__(self, batch_size: int = 100):
        """
        Args:
            batch_size: 每次读取的行数
        """
        self.batch_size = batch_size
    
    def read_parquet_batches(
        self, 
        file_path: str,
        columns: Optional[List[str]] = None,
        show_progress: bool = True
    ) -> Generator[pd.DataFrame, None, None]:
        """
        流式读取 Parquet 文件，按批次返回
        
        Args:
            file_path: parquet 文件路径
            columns: 要读取的列（None表示全部）
            show_progress: 是否显示进度条
            
        Yields:
            DataFrame 批次
        """
        try:
            parquet_file = pd.read_parquet(file_path)
            total_rows = len(parquet_file)
            
            if show_progress:
                logger.info(f"开始读取: {file_path} (总行数: {total_rows})")
            
            # 使用 tqdm 显示进度
            iterator = tqdm(
                range(0, total_rows, self.batch_size),
                desc=os.path.basename(file_path),
                disable=not show_progress
            )
            
            for start_idx in iterator:
                end_idx = min(start_idx + self.batch_size, total_rows)
                batch = parquet_file.iloc[start_idx:end_idx]
                
                # 只返回指定的列
                if columns:
                    batch = batch[[col for col in columns if col in batch.columns]]
                
                yield batch
                
        except Exception as e:
            logger.error(f"读取 Parquet 文件错误 {file_path}: {str(e)}")
            raise
    
    @staticmethod
    def parse_transcript_field(transcript_data) -> List[Dict[str, Any]]:
        """
        解析 earnings call 的 transcript 结构化字段
        
        Args:
            transcript_data: 原始的 transcript 数据（可能是 list 或 json str）
            
        Returns:
            解析后的 transcript 列表
        """
        try:
            if isinstance(transcript_data, str):
                return json.loads(transcript_data)
            elif isinstance(transcript_data, list):
                return transcript_data
            else:
                return []
        except Exception as e:
            logger.warning(f"解析 transcript 字段失败: {str(e)}")
            return []
    
    @staticmethod
    def parse_news_field(news_data) -> List[Dict[str, Any]]:
        """
        解析 news 的结构化字段
        
        Args:
            news_data: 原始的 news 数据（可能是 list 或 json str）
            
        Returns:
            解析后的 news 列表
        """
        try:
            if isinstance(news_data, str):
                return json.loads(news_data)
            elif isinstance(news_data, list):
                return news_data
            else:
                return []
        except Exception as e:
            logger.warning(f"解析 news 字段失败: {str(e)}")
            return []


class StockNewsReader(ParquetReader):
    """股票新闻数据读取器"""
    
    def get_records_batch(self, file_path: str) -> Generator[Dict[str, Any], None, None]:
        """
        逐行读取股票新闻，返回规范化的记录
        
        Yields:
            规范化的新闻记录
        """
        for batch_df in self.read_parquet_batches(file_path):
            for idx, row in batch_df.iterrows():
                # 解析嵌套的 news 字段
                news_paragraphs = self.parse_news_field(row.get('news', []))
                
                # 构建文本内容
                content_parts = []
                if row.get('title'):
                    content_parts.append(f"标题: {row['title']}")
                
                for para in news_paragraphs:
                    if isinstance(para, dict):
                        paragraph_text = para.get('paragraph', '')
                        if paragraph_text:
                            content_parts.append(paragraph_text)
                
                content = "\n".join(content_parts)
                
                # 过滤无效记录
                if not content or len(content.strip()) < 10:
                    continue
                
                yield {
                    'source': 'stock_news',
                    'symbol': row.get('symbol', ''),
                    'title': row.get('title'),
                    'publisher': row.get('publisher'),
                    'report_date': row.get('report_date'),
                    'source_type': row.get('type'),
                    'link': row.get('link'),
                    'content': content,
                    'uuid': row.get('uuid'),
                    'original_row_index': idx,
                    'raw_record': row.to_dict()
                }


class StockEarningCallReader(ParquetReader):
    """股票财报电话会议记录读取器"""
    
    def get_records_batch(self, file_path: str) -> Generator[Dict[str, Any], None, None]:
        """
        逐行读取 earnings call，返回规范化的记录
        
        Yields:
            规范化的 earnings call 记录
        """
        for batch_df in self.read_parquet_batches(file_path):
            for idx, row in batch_df.iterrows():
                # 解析嵌套的 transcripts 字段
                transcripts = self.parse_transcript_field(row.get('transcripts', []))
                
                # 构建完整文本
                content_parts = []
                
                # 添加头部信息
                header_parts = []
                if row.get('symbol'):
                    header_parts.append(f"股票代码: {row['symbol']}")
                if row.get('fiscal_year'):
                    header_parts.append(f"财年: {row['fiscal_year']}")
                if row.get('fiscal_quarter'):
                    header_parts.append(f"季度: {row['fiscal_quarter']}Q")
                if row.get('report_date'):
                    header_parts.append(f"报告日期: {row['report_date']}")
                
                if header_parts:
                    content_parts.append(" | ".join(header_parts))
                    content_parts.append("")
                
                # 添加转录文本
                for transcript in transcripts:
                    if isinstance(transcript, dict):
                        speaker = transcript.get('speaker', '未知发言人')
                        text = transcript.get('content', '')
                        if text:
                            content_parts.append(f"{speaker}:")
                            content_parts.append(text)
                            content_parts.append("")
                
                content = "\n".join(content_parts)
                
                # 过滤无效记录
                if not content or len(content.strip()) < 10:
                    continue
                
                yield {
                    'source': 'stock_earning_call',
                    'symbol': row.get('symbol', ''),
                    'fiscal_year': row.get('fiscal_year'),
                    'fiscal_quarter': row.get('fiscal_quarter'),
                    'report_date': row.get('report_date'),
                    'content': content,
                    'transcripts_id': row.get('transcripts_id'),
                    'original_row_index': idx,
                    'raw_record': row.to_dict()
                }
