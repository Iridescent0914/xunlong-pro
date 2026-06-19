"""完整的数据处理示例 - 已优化内存占用"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from financeRAG.processor.pipeline import FinanceDataPipeline
from financeRAG.processor.cleaner import TextCleaner
from financeRAG.processor.chunker import TextChunker


def setup_logger():
    """配置日志"""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        level="INFO"
    )
    logger.add(
        "processing.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO"
    )


def process_single_dataset(
    pipeline: FinanceDataPipeline,
    parquet_path: str,
    output_base_dir: str,
    data_source: str,
    max_records_per_batch: int = 50000,
    max_total_records: int = None,
) -> Dict[str, Any]:
    """
    分片处理单个数据集
    
    Args:
        pipeline: 处理管道
        parquet_path: parquet 文件路径
        output_base_dir: 输出目录
        data_source: 数据来源名称
        max_records_per_batch: 每个分片的最大记录数（方案2）
        max_total_records: 总共最多处理的记录数
        
    Returns:
        处理统计信息
    """
    if not os.path.exists(parquet_path):
        logger.warning(f"文件不存在: {parquet_path}")
        return None
    
    logger.info("=" * 80)
    logger.info(f"处理 {data_source} 数据集")
    logger.info(f"分片模式：每个分片最多 {max_records_per_batch:,} 条记录（方案2）")
    logger.info("=" * 80)
    
    batch_num = 0
    total_records_processed = 0
    all_stats = {
        'total_records': 0,
        'total_valid_records': 0,
        'total_invalid_records': 0,
        'total_documents': 0,
        'total_chunks': 0,
        'batch_outputs': []
    }
    
    # 持续处理，直到达到 max_records_per_batch 或文件结束
    while True:
        batch_num += 1
        max_records_in_batch = max_records_per_batch
        
        # 如果设定了总记录数限制，调整本批次的最大记录数
        if max_total_records:
            remaining = max_total_records - total_records_processed
            if remaining <= 0:
                logger.info(f"已达到总记录数限制 {max_total_records}，停止处理")
                break
            max_records_in_batch = min(max_records_per_batch, remaining)
        
        # 创建新的管道实例用于本批次（重置统计信息）
        batch_pipeline = FinanceDataPipeline(
            chunk_size=pipeline.chunk_size,
            chunk_overlap=pipeline.chunk_overlap,
            output_dir=output_base_dir,
            batch_size=10,  # 减小批处理大小
        )
        
        # 生成输出文件名
        output_file = os.path.join(
            output_base_dir,
            f"{data_source}_batch_{batch_num:03d}.jsonl"
        )
        
        logger.info(f"\n 处理第 {batch_num} 个分片...")
        logger.info(f"最多处理 {max_records_in_batch:,} 条记录")
        
        # 处理数据（方案3：每1000个文档保存一次）
        if data_source == 'stock_news':
            documents = batch_pipeline.process_stock_news(
                parquet_path=parquet_path,
                max_records=max_records_in_batch,
            )
        else:  # stock_earning_call
            documents = batch_pipeline.process_stock_earning_calls(
                parquet_path=parquet_path,
                max_records=max_records_in_batch,
            )
        
        # 保存文档（使用流式保存，内存优化）
        save_stats = batch_pipeline.save_documents_batch(
            documents=documents,
            output_file=output_file,
            save_interval=1000,  # 每1000个文档保存一次
        )
        
        if not save_stats['total_saved']:
            logger.info(f"第 {batch_num} 个分片处理完成：无有效文档，停止处理")
            break
        
        # 累计统计信息
        batch_stats = batch_pipeline.get_statistics()
        all_stats['total_records'] += batch_stats['total_records']
        all_stats['total_valid_records'] += batch_stats['valid_records']
        all_stats['total_invalid_records'] += batch_stats['invalid_records']
        all_stats['total_documents'] += batch_stats['total_documents']
        all_stats['total_chunks'] += batch_stats['total_chunks']
        all_stats['batch_outputs'].append({
            'batch_num': batch_num,
            'output_file': output_file,
            'file_size_mb': save_stats['file_size_mb'],
            'documents': save_stats['total_saved'],
            'records': batch_stats['total_records'],
        })
        
        total_records_processed += batch_stats['total_records']
        
        logger.info(f"✓ 第 {batch_num} 个分片完成")
        logger.info(f"  - 输入记录: {batch_stats['total_records']:,}")
        logger.info(f"  - 有效记录: {batch_stats['valid_records']:,}")
        logger.info(f"  - 生成文档: {save_stats['total_saved']:,}")
        logger.info(f"  - 文件大小: {save_stats['file_size_mb']:.2f} MB")
        logger.info(f"  - 累计记录: {total_records_processed:,}")
        
        # 内存优化：检查是否处理完所有记录
        if batch_stats['total_records'] < max_records_in_batch:
            logger.info(f"数据集处理完成（共 {batch_num} 个分片）")
            break
    
    return all_stats


def merge_jsonl_files(output_files: list, merged_output_file: str):
    """
    合并多个 JSONL 文件为一个（方案2的后续处理）
    
    Args:
        output_files: 要合并的文件列表
        merged_output_file: 合并后的输出文件
    """
    logger.info(f"\n📦 合并 {len(output_files)} 个文件到: {merged_output_file}")
    
    total_lines = 0
    with open(merged_output_file, 'w', encoding='utf-8') as out_f:
        for input_file in output_files:
            if os.path.exists(input_file):
                with open(input_file, 'r', encoding='utf-8') as in_f:
                    for line in in_f:
                        out_f.write(line)
                        total_lines += 1
                logger.info(f"  ✓ 已合并: {input_file}")
    
    logger.info(f"合并完成: 共 {total_lines:,} 行")


def main():
    """主函数"""
    setup_logger()
    
    # 配置参数
    DATA_DIR = "financeRAG/data"
    OUTPUT_DIR = "financeRAG/processed_data_optimized"
    
    STOCK_NEWS_PATH = os.path.join(DATA_DIR, "stock_news.parquet")
    STOCK_EARNING_CALLS_PATH = os.path.join(DATA_DIR, "stock_earning_call_transcripts.parquet")
    
    # 处理参数
    CHUNK_SIZE = 512  # 每个切块的字符数
    CHUNK_OVERLAP = 100  # 相邻切块的重叠
    MAX_RECORDS_PER_BATCH = 50000  # 方案2：每个分片处理的记录数
    MAX_TOTAL_RECORDS = None  # None 表示处理全部，可设为某个数字用于测试
    
    logger.info("=" * 80)
    logger.info("金融数据处理管道启动 - 内存优化版")
    logger.info("=" * 80)
    logger.info(f"输出目录: {OUTPUT_DIR}")
    logger.info(f"块大小: {CHUNK_SIZE}, 重叠: {CHUNK_OVERLAP}")
    logger.info(f"方案1 - 批处理大小: 10（从 100 减小）")
    logger.info(f"方案2 - 分片处理: 每 {MAX_RECORDS_PER_BATCH:,} 条记录为一个分片")
    logger.info(f"方案3 - 流式保存: 每 1,000 个文档保存一次，清空内存")
    logger.info(f"最大总记录数: {MAX_TOTAL_RECORDS or '无限制'}")
    logger.info("=" * 80)
    
    try:
        # 初始化处理管道（主要用于配置）
        main_pipeline = FinanceDataPipeline(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            output_dir=OUTPUT_DIR,
            batch_size=10,  # 方案1：减小批处理大小
        )
        
        batch_output_files = []
        
        # 处理股票新闻
        news_stats = process_single_dataset(
            pipeline=main_pipeline,
            parquet_path=STOCK_NEWS_PATH,
            output_base_dir=OUTPUT_DIR,
            data_source="stock_news",
            max_records_per_batch=MAX_RECORDS_PER_BATCH,
            max_total_records=MAX_TOTAL_RECORDS,
        )
        
        if news_stats:
            for batch_info in news_stats['batch_outputs']:
                batch_output_files.append(batch_info['output_file'])
        
        # 处理财报电话会议
        earning_stats = process_single_dataset(
            pipeline=main_pipeline,
            parquet_path=STOCK_EARNING_CALLS_PATH,
            output_base_dir=OUTPUT_DIR,
            data_source="stock_earning_call",
            max_records_per_batch=MAX_RECORDS_PER_BATCH,
            max_total_records=MAX_TOTAL_RECORDS,
        )
        
        if earning_stats:
            for batch_info in earning_stats['batch_outputs']:
                batch_output_files.append(batch_info['output_file'])
        
        # 合并所有批次文件
        if batch_output_files:
            final_output_file = os.path.join(OUTPUT_DIR, "combined_documents.jsonl")
            merge_jsonl_files(batch_output_files, final_output_file)
        
        # 打印最终统计信息
        logger.info("=" * 80)
        logger.info("处理完成 - 最终统计")
        logger.info("=" * 80)
        
        total_records = 0
        total_valid = 0
        total_invalid = 0
        total_docs = 0
        total_chunks = 0
        
        if news_stats:
            logger.info("\n📰 股票新闻统计:")
            logger.info(f"  总记录数: {news_stats['total_records']:,}")
            logger.info(f"  有效记录数: {news_stats['total_valid_records']:,}")
            logger.info(f"  无效记录数: {news_stats['total_invalid_records']:,}")
            logger.info(f"  生成文档数: {news_stats['total_documents']:,}")
            logger.info(f"  总切块数: {news_stats['total_chunks']:,}")
            logger.info(f"  分片数: {len(news_stats['batch_outputs'])}")
            total_records += news_stats['total_records']
            total_valid += news_stats['total_valid_records']
            total_invalid += news_stats['total_invalid_records']
            total_docs += news_stats['total_documents']
            total_chunks += news_stats['total_chunks']
        
        if earning_stats:
            logger.info("\n💬 财报电话会议统计:")
            logger.info(f"  总记录数: {earning_stats['total_records']:,}")
            logger.info(f"  有效记录数: {earning_stats['total_valid_records']:,}")
            logger.info(f"  无效记录数: {earning_stats['total_invalid_records']:,}")
            logger.info(f"  生成文档数: {earning_stats['total_documents']:,}")
            logger.info(f"  总切块数: {earning_stats['total_chunks']:,}")
            logger.info(f"  分片数: {len(earning_stats['batch_outputs'])}")
            total_records += earning_stats['total_records']
            total_valid += earning_stats['total_valid_records']
            total_invalid += earning_stats['total_invalid_records']
            total_docs += earning_stats['total_documents']
            total_chunks += earning_stats['total_chunks']
        
        logger.info("\n📊 整体统计:")
        logger.info(f"  总记录数: {total_records:,}")
        logger.info(f"  有效记录数: {total_valid:,}")
        logger.info(f"  无效记录数: {total_invalid:,}")
        logger.info(f"  生成文档数: {total_docs:,}")
        logger.info(f"  总切块数: {total_chunks:,}")
        
        if total_records > 0:
            valid_rate = (total_valid / total_records) * 100
            logger.info(f"  数据有效率: {valid_rate:.2f}%")
        
        logger.info("=" * 80)
        logger.info("✅ 处理成功完成！")
        logger.info("=" * 80)
        
        return 0
    
    except Exception as e:
        logger.error(f"处理过程中出错: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
