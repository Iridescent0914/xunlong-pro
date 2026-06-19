"""Parquet 文件读取器 - 支持流式处理"""

import os
import pandas as pd
import json
from collections.abc import Mapping
from typing import Generator, Dict, Any, List, Optional
from loguru import logger
from tqdm import tqdm

try:
    import pyarrow.parquet as pq
except ImportError:  # pragma: no cover - pandas fallback handles this.
    pq = None


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
        show_progress: bool = True,
        start_row: int = 0,
        max_rows: Optional[int] = None,
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
            start_row = max(0, start_row)

            if pq is not None:
                parquet_file = pq.ParquetFile(file_path)
                total_rows = parquet_file.metadata.num_rows
                end_row = total_rows if max_rows is None else min(total_rows, start_row + max_rows)

                if start_row >= total_rows or end_row <= start_row:
                    if show_progress:
                        logger.info(f"Start row {start_row} is outside {file_path} (total rows: {total_rows})")
                    return

                available_columns = None
                if columns:
                    schema_names = set(parquet_file.schema.names)
                    available_columns = [col for col in columns if col in schema_names]

                if show_progress:
                    logger.info(
                        f"Reading {file_path} rows {start_row}-{end_row - 1} "
                        f"(total rows: {total_rows})"
                    )

                pbar = tqdm(
                    total=end_row - start_row,
                    desc=os.path.basename(file_path),
                    disable=not show_progress,
                )

                current_row = 0
                try:
                    for record_batch in parquet_file.iter_batches(
                        batch_size=self.batch_size,
                        columns=available_columns,
                    ):
                        batch_start = current_row
                        batch_end = current_row + record_batch.num_rows
                        current_row = batch_end

                        if batch_end <= start_row:
                            continue
                        if batch_start >= end_row:
                            break

                        slice_start = max(start_row - batch_start, 0)
                        slice_end = min(end_row - batch_start, record_batch.num_rows)
                        sliced_batch = record_batch.slice(slice_start, slice_end - slice_start)
                        batch = sliced_batch.to_pandas()
                        batch.index = range(batch_start + slice_start, batch_start + slice_end)

                        pbar.update(len(batch))
                        yield batch
                finally:
                    pbar.close()
                return

            parquet_file = pd.read_parquet(file_path)
            total_rows = len(parquet_file)
            end_row = total_rows if max_rows is None else min(total_rows, start_row + max_rows)
            
            if show_progress:
                logger.info(f"开始读取: {file_path} (总行数: {total_rows})")
            
            # 使用 tqdm 显示进度
            iterator = tqdm(
                range(start_row, end_row, self.batch_size),
                desc=os.path.basename(file_path),
                disable=not show_progress
            )
            
            for start_idx in iterator:
                end_idx = min(start_idx + self.batch_size, end_row)
                batch = parquet_file.iloc[start_idx:end_idx]
                
                # 只返回指定的列
                if columns:
                    batch = batch[[col for col in columns if col in batch.columns]]
                
                yield batch
                
        except Exception as e:
            logger.error(f"读取 Parquet 文件错误 {file_path}: {str(e)}")
            raise

    @staticmethod
    def get_row_count(file_path: str) -> int:
        """Return parquet row count from metadata when available."""
        if pq is not None:
            return pq.ParquetFile(file_path).metadata.num_rows
        return len(pd.read_parquet(file_path))

    @staticmethod
    def _coerce_nested_records(nested_data, field_name: str) -> List[Dict[str, Any]]:
        """Normalize nested parquet/json fields into a list of dict records."""
        try:
            if nested_data is None:
                return []

            if hasattr(nested_data, "as_py"):
                nested_data = nested_data.as_py()
            if isinstance(nested_data, str):
                nested_data = json.loads(nested_data)
            elif hasattr(nested_data, "tolist"):
                nested_data = nested_data.tolist()
            elif isinstance(nested_data, tuple):
                nested_data = list(nested_data)

            if isinstance(nested_data, Mapping):
                return [dict(nested_data)]
            if isinstance(nested_data, list):
                records = []
                for item in nested_data:
                    if hasattr(item, "as_py"):
                        item = item.as_py()
                    if isinstance(item, Mapping):
                        records.append(dict(item))
                return records

            return []
        except Exception as e:
            logger.warning(f"解析 {field_name} 字段失败: {str(e)}")
            return []

    @staticmethod
    def _to_text(value) -> str:
        """Convert parquet/pandas scalar values into clean text."""
        if value is None:
            return ""
        if hasattr(value, "as_py"):
            value = value.as_py()
        if not isinstance(value, (list, dict, tuple)) and pd.isna(value):
            return ""
        text = str(value).strip()
        if text.lower() in {"nan", "none", "null"}:
            return ""
        return text

    @staticmethod
    def _to_int(value) -> Optional[int]:
        """Convert parquet/pandas numeric values into optional ints."""
        if value is None:
            return None
        if hasattr(value, "as_py"):
            value = value.as_py()
        if not isinstance(value, (list, dict, tuple)) and pd.isna(value):
            return None
        return int(value)

    @staticmethod
    def parse_transcript_field(transcript_data) -> List[Dict[str, Any]]:
        """
        解析 earnings call 的 transcript 结构化字段
        
        Args:
            transcript_data: 原始的 transcript 数据（可能是 list 或 json str）
            
        Returns:
            解析后的 transcript 列表
        """
        return ParquetReader._coerce_nested_records(transcript_data, "transcript")
    
    @staticmethod
    def parse_news_field(news_data) -> List[Dict[str, Any]]:
        """
        解析 news 的结构化字段
        
        Args:
            news_data: 原始的 news 数据（可能是 list 或 json str）
            
        Returns:
            解析后的 news 列表
        """
        return ParquetReader._coerce_nested_records(news_data, "news")


class StockNewsReader(ParquetReader):
    """股票新闻数据读取器"""
    
    def get_records_batch(
        self,
        file_path: str,
        start_row: int = 0,
        max_rows: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        逐行读取股票新闻，返回规范化的记录
        
        Yields:
            规范化的新闻记录
        """
        for batch_df in self.read_parquet_batches(
            file_path,
            start_row=start_row,
            max_rows=max_rows,
        ):
            for idx, row in batch_df.iterrows():
                # 解析嵌套的 news 字段
                news_paragraphs = self.parse_news_field(row.get('news', []))
                
                # 构建文本内容
                content_parts = []
                title = self._to_text(row.get('title'))
                if title:
                    content_parts.append(f"标题: {title}")
                
                paragraph_count = 0
                for para in news_paragraphs:
                    highlight = self._to_text(para.get('highlight'))
                    paragraph_text = self._to_text(para.get('paragraph'))
                    if not paragraph_text:
                        continue
                    if highlight:
                        content_parts.append(f"小标题: {highlight}")
                    content_parts.append(paragraph_text)
                    paragraph_count += 1
                
                content = "\n".join(content_parts)
                
                # 过滤无正文记录，避免只把标题写入 RAG 文件
                if paragraph_count == 0 or not content or len(content.strip()) < 10:
                    continue
                
                yield {
                    'source': 'stock_news',
                    'symbol': row.get('symbol', ''),
                    'title': title,
                    'publisher': row.get('publisher'),
                    'report_date': row.get('report_date'),
                    'source_type': row.get('type'),
                    'link': row.get('link'),
                    'content': content,
                    'uuid': row.get('uuid'),
                    'content_length': len(content),
                    'text_segment_count': paragraph_count,
                    'original_row_index': idx,
                    'raw_record': row.to_dict()
                }


class StockEarningCallReader(ParquetReader):
    """股票财报电话会议记录读取器"""
    
    def get_records_batch(
        self,
        file_path: str,
        start_row: int = 0,
        max_rows: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        逐行读取 earnings call，返回规范化的记录
        
        Yields:
            规范化的 earnings call 记录
        """
        for batch_df in self.read_parquet_batches(
            file_path,
            start_row=start_row,
            max_rows=max_rows,
        ):
            for idx, row in batch_df.iterrows():
                # 解析嵌套的 transcripts 字段
                transcripts = self.parse_transcript_field(row.get('transcripts', []))
                
                # 构建完整文本
                content_parts = []
                
                # 添加头部信息
                header_parts = []
                symbol = self._to_text(row.get('symbol'))
                fiscal_year = self._to_int(row.get('fiscal_year'))
                fiscal_quarter = self._to_int(row.get('fiscal_quarter'))
                report_date = self._to_text(row.get('report_date'))
                if symbol:
                    header_parts.append(f"股票代码: {symbol}")
                if fiscal_year is not None:
                    header_parts.append(f"财年: {fiscal_year}")
                if fiscal_quarter is not None:
                    header_parts.append(f"季度: {fiscal_quarter}Q")
                if report_date:
                    header_parts.append(f"报告日期: {report_date}")
                
                if header_parts:
                    content_parts.append(" | ".join(header_parts))
                    content_parts.append("")
                
                # 添加转录文本
                transcript_count = 0
                for transcript in transcripts:
                    speaker = self._to_text(transcript.get('speaker')) or '未知发言人'
                    text = self._to_text(transcript.get('content'))
                    if not text:
                        continue
                    content_parts.append(f"{speaker}:")
                    content_parts.append(text)
                    content_parts.append("")
                    transcript_count += 1
                
                content = "\n".join(content_parts)
                
                # 过滤无正文记录，避免只把会议头写入 RAG 文件
                if transcript_count == 0 or not content or len(content.strip()) < 10:
                    continue
                
                yield {
                    'source': 'stock_earning_call',
                    'symbol': symbol,
                    'fiscal_year': fiscal_year,
                    'fiscal_quarter': fiscal_quarter,
                    'report_date': report_date,
                    'content': content,
                    'transcripts_id': self._to_int(row.get('transcripts_id')),
                    'content_length': len(content),
                    'text_segment_count': transcript_count,
                    'original_row_index': idx,
                    'raw_record': row.to_dict()
                }
