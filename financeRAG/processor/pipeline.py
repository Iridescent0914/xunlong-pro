"""主处理流程 - 完整的数据处理管道"""

import os
import json
import hashlib
from datetime import datetime
from typing import Generator, Optional, Dict, Any, List
from pathlib import Path
from tqdm import tqdm
from loguru import logger

from .models import Document, DocumentMetadata
from .reader import StockNewsReader, StockEarningCallReader
from .cleaner import TextCleaner
from .chunker import TextChunker


class FinanceDataPipeline:
    """金融数据完整处理管道"""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 100,
        output_dir: str = "processed_data",
        batch_size: int = 100,
    ):
        """
        初始化处理管道
        
        Args:
            chunk_size: 文本切块大小
            chunk_overlap: 切块重叠
            output_dir: 输出目录
            batch_size: 批处理大小
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.output_dir = output_dir
        self.batch_size = batch_size
        
        # 初始化组件
        self.cleaner = TextCleaner()
        self.chunker = TextChunker(chunk_size, chunk_overlap)
        self.news_reader = StockNewsReader(batch_size)
        self.earning_reader = StockEarningCallReader(batch_size)
        
        # 创建输出目录
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 统计信息
        self.stats = {
            'total_records': 0,
            'valid_records': 0,
            'invalid_records': 0,
            'total_documents': 0,
            'total_chunks': 0,
            'processing_time': 0,
        }
    
    def _generate_doc_id(self, source: str, symbol: str, record_index: int) -> str:
        """生成唯一的文档ID"""
        key = f"{source}_{symbol}_{record_index}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def process_stock_news(
        self,
        parquet_path: str,
        save_processed: bool = True,
        max_records: Optional[int] = None,
    ) -> Generator[Document, None, None]:
        """
        处理股票新闻数据
        
        流程: 读取 → 筛选 → 清洗 → 生成 Document → 切块
        
        Args:
            parquet_path: parquet 文件路径
            save_processed: 是否保存处理后的文档
            max_records: 最多处理的记录数
            
        Yields:
            Document 对象（已切块）
        """
        logger.info(f"开始处理股票新闻: {parquet_path}")
        
        record_count = 0
        document_count = 0
        chunk_count = 0
        
        # 使用进度条包装记录迭代
        for record in self.news_reader.get_records_batch(parquet_path):
            self.stats['total_records'] += 1
            record_count += 1
            
            # 检查是否达到最大记录数
            if max_records and record_count > max_records:
                break
            
            # 步骤 1: 筛选文本字段（过滤无效记录）
            content = record.get('content', '')
            if not self.cleaner.is_valid_text(content):
                self.stats['invalid_records'] += 1
                continue
            
            self.stats['valid_records'] += 1
            
            # 步骤 2: 清洗文本
            cleaned_content = self.cleaner.clean(content)
            
            if not self.cleaner.is_valid_text(cleaned_content):
                self.stats['invalid_records'] += 1
                continue
            
            # 步骤 3: 生成标准 Document
            doc_id = self._generate_doc_id(
                'stock_news',
                record.get('symbol', 'UNKNOWN'),
                record.get('original_row_index', 0)
            )
            
            metadata = DocumentMetadata(
                source='stock_news',
                symbol=record.get('symbol', ''),
                title=record.get('title'),
                publisher=record.get('publisher'),
                report_date=record.get('report_date'),
                source_type=record.get('source_type'),
                link=record.get('link'),
                original_index=record.get('original_row_index', 0),
                processed_at=datetime.now().isoformat(),
            )
            
            # 步骤 4: 切块（使用滑动窗口）
            chunks = self.chunker.chunk_text(cleaned_content, chunk_id_prefix=doc_id)
            
            for chunk_info in chunks:
                document = Document(
                    doc_id=f"{doc_id}_chunk_{chunk_info['chunk_index']}",
                    content=chunk_info['content'],
                    metadata=metadata,
                    chunk_index=chunk_info['chunk_index'],
                    chunk_size=chunk_info['chunk_size'],
                    chunk_overlap=chunk_info['overlap'],
                )
                
                document_count += 1
                chunk_count += 1
                self.stats['total_documents'] += 1
                self.stats['total_chunks'] += 1
                
                yield document
        
        logger.info(
            f"股票新闻处理完成: "
            f"读取={record_count}, "
            f"有效={self.stats['valid_records']}, "
            f"生成文档={document_count}, "
            f"切块数={chunk_count}"
        )
    
    def process_stock_earning_calls(
        self,
        parquet_path: str,
        save_processed: bool = True,
        max_records: Optional[int] = None,
    ) -> Generator[Document, None, None]:
        """
        处理股票财报电话会议
        
        流程: 读取 → 筛选 → 清洗 → 生成 Document → 切块
        
        Args:
            parquet_path: parquet 文件路径
            save_processed: 是否保存处理后的文档
            max_records: 最多处理的记录数
            
        Yields:
            Document 对象（已切块）
        """
        logger.info(f"开始处理财报电话会议: {parquet_path}")
        
        record_count = 0
        document_count = 0
        chunk_count = 0
        
        for record in self.earning_reader.get_records_batch(parquet_path):
            self.stats['total_records'] += 1
            record_count += 1
            
            # 检查是否达到最大记录数
            if max_records and record_count > max_records:
                break
            
            # 步骤 1: 筛选文本字段（过滤无效记录）
            content = record.get('content', '')
            if not self.cleaner.is_valid_text(content):
                self.stats['invalid_records'] += 1
                continue
            
            self.stats['valid_records'] += 1
            
            # 步骤 2: 清洗文本
            cleaned_content = self.cleaner.clean(content)
            
            if not self.cleaner.is_valid_text(cleaned_content):
                self.stats['invalid_records'] += 1
                continue
            
            # 步骤 3: 生成标准 Document
            doc_id = self._generate_doc_id(
                'stock_earning_call',
                record.get('symbol', 'UNKNOWN'),
                record.get('original_row_index', 0)
            )
            
            metadata = DocumentMetadata(
                source='stock_earning_call',
                symbol=record.get('symbol', ''),
                report_date=record.get('report_date'),
                original_index=record.get('original_row_index', 0),
                processed_at=datetime.now().isoformat(),
            )
            
            # 步骤 4: 切块（使用滑动窗口）
            chunks = self.chunker.chunk_text(cleaned_content, chunk_id_prefix=doc_id)
            
            for chunk_info in chunks:
                document = Document(
                    doc_id=f"{doc_id}_chunk_{chunk_info['chunk_index']}",
                    content=chunk_info['content'],
                    metadata=metadata,
                    chunk_index=chunk_info['chunk_index'],
                    chunk_size=chunk_info['chunk_size'],
                    chunk_overlap=chunk_info['overlap'],
                )
                
                document_count += 1
                chunk_count += 1
                self.stats['total_documents'] += 1
                self.stats['total_chunks'] += 1
                
                yield document
        
        logger.info(
            f"财报电话会议处理完成: "
            f"读取={record_count}, "
            f"有效={self.stats['valid_records']}, "
            f"生成文档={document_count}, "
            f"切块数={chunk_count}"
        )
    
    def process_all_datasets(
        self,
        news_path: str,
        earning_calls_path: str,
        max_records: Optional[int] = None,
    ) -> Generator[Document, None, None]:
        """
        处理所有数据集
        
        Args:
            news_path: 股票新闻 parquet 路径
            earning_calls_path: 财报电话会议 parquet 路径
            max_records: 每个数据集最多处理的记录数
            
        Yields:
            Document 对象
        """
        # 处理股票新闻
        if os.path.exists(news_path):
            logger.info("=" * 50)
            logger.info("处理 STOCK NEWS 数据集")
            logger.info("=" * 50)
            for doc in self.process_stock_news(news_path, max_records=max_records):
                yield doc
        else:
            logger.warning(f"文件不存在: {news_path}")
        
        # 处理财报电话会议
        if os.path.exists(earning_calls_path):
            logger.info("=" * 50)
            logger.info("处理 STOCK EARNING CALLS 数据集")
            logger.info("=" * 50)
            # 注意: 这个文件可能很大，使用 chunks 参数
            for doc in self.process_stock_earning_calls(
                earning_calls_path, 
                max_records=max_records
            ):
                yield doc
        else:
            logger.warning(f"文件不存在: {earning_calls_path}")
    
    def save_documents_batch(
        self,
        documents: Generator[Document, None, None],
        output_file: str,
        batch_size: int = 1000,
        save_interval: int = 1000,
    ) -> Dict[str, Any]:
        """
        批量保存处理后的文档到 JSONL 格式（流式写入，内存优化）
        
        Args:
            documents: 文档生成器
            output_file: 输出文件路径（JSONL 格式）
            batch_size: 批大小（已弃用，保留用于兼容性）
            save_interval: 每处理多少个文档后保存一次（方案3）
            
        Returns:
            处理统计信息
        """
        logger.info(f"开始保存文档到: {output_file}")
        logger.info(f"内存优化模式：每 {save_interval} 个文档保存一次")
        
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        total_saved = 0
        buffer = []
        
        # 创建进度条
        pbar = tqdm(desc="保存文档", unit="doc")
        
        # 使用 JSONL 格式（每行一个 JSON 对象）- 易于流式处理和追加
        with open(output_file, 'a', encoding='utf-8') as f:
            for doc in documents:
                doc_dict = doc.dict(exclude_unset=True)
                buffer.append(doc_dict)
                total_saved += 1
                pbar.update(1)
                
                # 每处理 save_interval 个文档，保存一次并清空缓冲区（方案3）
                if len(buffer) >= save_interval:
                    for item in buffer:
                        f.write(json.dumps(item, ensure_ascii=False) + '\n')
                    f.flush()  # 立即刷新到磁盘
                    logger.info(f"✓ 已保存 {total_saved} 个文档，内存已清空")
                    buffer = []  # 清空内存缓冲区
        
        # 保存剩余的文档
        if buffer:
            with open(output_file, 'a', encoding='utf-8') as f:
                for item in buffer:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
                f.flush()
        
        pbar.close()
        
        logger.info(f"文档保存完成: 总数={total_saved}, 文件={output_file}")
        
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024) if os.path.exists(output_file) else 0
        return {
            'total_saved': total_saved,
            'output_file': output_file,
            'file_size_mb': file_size_mb,
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return {
            **self.stats,
            'chunk_config': {
                'chunk_size': self.chunk_size,
                'chunk_overlap': self.chunk_overlap,
            }
        }
