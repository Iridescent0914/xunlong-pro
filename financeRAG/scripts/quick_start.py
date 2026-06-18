"""快速开始指南 - 小规模测试版本"""

import os
import sys
from pathlib import Path
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from financeRAG.processor.pipeline import FinanceDataPipeline


def quick_test():
    """快速测试 - 仅处理前 1000 条记录"""
    
    logger.remove()
    logger.add(sys.stderr, format="<level>{level}</level> | {message}", level="INFO")
    
    DATA_DIR = "financeRAG/data"
    OUTPUT_DIR = "financeRAG/processed_data_quick_test"
    
    STOCK_NEWS_PATH = os.path.join(DATA_DIR, "stock_news.parquet")
    
    logger.info("=" * 80)
    logger.info("快速测试模式 - 处理 stock_news 前 1000 条记录")
    logger.info("=" * 80)
    
    pipeline = FinanceDataPipeline(
        chunk_size=512,
        chunk_overlap=100,
        output_dir=OUTPUT_DIR,
    )
    
    output_file = os.path.join(OUTPUT_DIR, "quick_test_documents.jsonl")
    
    # 仅处理前 1000 条记录用于测试
    documents = pipeline.process_stock_news(
        parquet_path=STOCK_NEWS_PATH,
        max_records=1000,
    )
    
    save_stats = pipeline.save_documents_batch(
        documents=documents,
        output_file=output_file,
    )
    
    logger.info("\n快速测试完成!")
    logger.info(f"输出文件: {output_file}")
    logger.info(f"文件大小: {save_stats['file_size_mb']:.2f} MB")
    logger.info(f"总文档数: {save_stats['total_saved']}")
    
    stats = pipeline.get_statistics()
    logger.info("\n统计信息:")
    logger.info(f"  处理记录: {stats['total_records']}")
    logger.info(f"  有效记录: {stats['valid_records']}")
    logger.info(f"  生成文档: {stats['total_documents']}")
    logger.info(f"  总切块数: {stats['total_chunks']}")


if __name__ == "__main__":
    quick_test()
