"""测试数据处理各个模块"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from financeRAG.processor.cleaner import TextCleaner
from financeRAG.processor.chunker import TextChunker


def test_text_cleaner():
    """测试文本清洗模块"""
    print("\n" + "=" * 60)
    print("测试 1: 文本清洗模块")
    print("=" * 60)
    
    cleaner = TextCleaner()
    
    # 测试样本
    samples = [
        "   这是一个  <span>测试</span>  文本   \n\n\n 有很多空格",
        "Check this link: https://example.com 和邮箱 test@example.com",
        "包含HTML&nbsp;实体&lt;test&gt;的文本",
        "Some\t\ttabs\tand\nnewlines\n\nin\ntext",
    ]
    
    for i, text in enumerate(samples, 1):
        print(f"\n示例 {i}:")
        print(f"原始: {repr(text[:50])}...")
        cleaned = cleaner.clean(text)
        print(f"清洗后: {repr(cleaned[:50])}...")
        stats = cleaner.get_text_stats(cleaned)
        print(f"统计: {stats}")


def test_text_chunker():
    """测试文本切块模块"""
    print("\n" + "=" * 60)
    print("测试 2: 文本切块模块")
    print("=" * 60)
    
    chunker = TextChunker(chunk_size=200, overlap=50)
    
    # 构造测试文本
    long_text = "这是一个很长的文本。" * 50  # 约 350 字
    
    print(f"\n文本长度: {len(long_text)} 字符")
    print(f"块大小: 200, 重叠: 50")
    
    # 使用滑动窗口切块
    chunks = chunker.chunk_text(long_text)
    print(f"\n滑动窗口切块结果:")
    print(f"总块数: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"  块 {chunk['chunk_index']}: {chunk['start_char']}-{chunk['end_char']} "
              f"({len(chunk['content'])} 字符)")
    
    # 按句子切块
    sentence_text = "这是第一句。这是第二句。这是第三句。" * 10
    sentence_chunks = chunker.chunk_by_sentences(sentence_text, max_chars=100)
    
    print(f"\n按句子切块结果 (max_chars=100):")
    print(f"总块数: {len(sentence_chunks)}")
    for i, chunk in enumerate(sentence_chunks[:3]):  # 只显示前3个
        print(f"  块 {chunk['chunk_index']}: {len(chunk['content'])} 字符")
    
    # 估计块数
    estimated = chunker.estimate_chunks_count(long_text, chunk_size=200, overlap=50)
    print(f"\n估计的块数: {estimated}, 实际块数: {len(chunks)}")


def test_end_to_end():
    """端到端测试"""
    print("\n" + "=" * 60)
    print("测试 3: 端到端处理流程（完整数据处理）")
    print("=" * 60)
    
    from financeRAG.processor.pipeline import FinanceDataPipeline
    import os
    
    # 创建测试数据
    test_data_dir = "financeRAG/test_processed_data"
    Path(test_data_dir).mkdir(exist_ok=True, parents=True)
    
    pipeline = FinanceDataPipeline(
        chunk_size=256,
        chunk_overlap=50,
        output_dir=test_data_dir,
    )
    
    print(f"\n管道已初始化:")
    print(f"  块大小: {pipeline.chunk_size}")
    print(f"  重叠: {pipeline.chunk_overlap}")
    print(f"  输出目录: {pipeline.output_dir}")
    
    # 实际处理数据（前100条新闻作为测试）
    data_path = "financeRAG/data/stock_news.parquet"
    
    if os.path.exists(data_path):
        print(f"\n正在处理测试数据: {data_path}")
        
        # 处理前100条记录
        documents = pipeline.process_stock_news(
            parquet_path=data_path,
            max_records=100  # 只处理前100条用于测试
        )
        
        # 保存到输出文件
        output_file = os.path.join(test_data_dir, "test_documents.jsonl")
        save_stats = pipeline.save_documents_batch(documents, output_file)
        
        print(f"\n处理结果:")
        print(f"  输出文件: {output_file}")
        print(f"  文件大小: {save_stats['file_size_mb']:.2f} MB")
        print(f"  保存文档数: {save_stats['total_saved']}")
    else:
        print(f"\n⚠️ 数据文件不存在: {data_path}")
    
    # 获取最终统计信息
    stats = pipeline.get_statistics()
    print(f"\n最终统计信息:")
    print(f"  总记录数: {stats['total_records']}")
    print(f"  有效记录: {stats['valid_records']}")
    print(f"  无效记录: {stats['invalid_records']}")
    print(f"  生成文档: {stats['total_documents']}")
    print(f"  总切块数: {stats['total_chunks']}")
    print(f"  数据有效率: {(stats['valid_records']/max(stats['total_records'], 1)*100):.1f}%")


if __name__ == "__main__":
    test_text_cleaner()
    test_text_chunker()
    test_end_to_end()
    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)
