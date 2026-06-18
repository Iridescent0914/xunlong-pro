"""
完整的数据处理管道
工作流程：
1. 读取 parquet
2. 筛选文本字段
3. 清洗文本
4. 生成标准 Document
5. 切块
6. 保存 processed documents
"""

import os
import json
import pickle
import pandas as pd
from typing import List
from pathlib import Path

from data_loader import load_earning_call_parquet, load_stock_news_parquet
from chunker import chunk_documents
from document_schema import Document


def save_documents_json(docs: List[Document], output_path: str):
    """
    将Document列表保存为JSON格式
    """
    docs_data = []
    for doc in docs:
        docs_data.append({
            "chunk_id": doc.chunk_id,
            "raw_text": doc.raw_text,
            "clean_text": doc.clean_text,
            "metadata": doc.metadata,
            "source_type": doc.source_type
        })
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(docs_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 已保存 {len(docs)} 个文档到 JSON: {output_path}")


def save_documents_pickle(docs: List[Document], output_path: str):
    """
    将Document列表保存为pickle格式（用于Python后续处理）
    """
    with open(output_path, 'wb') as f:
        pickle.dump(docs, f)
    
    print(f"✓ 已保存 {len(docs)} 个文档到 Pickle: {output_path}")


def save_documents_csv(docs: List[Document], output_path: str):
    """
    将Document列表保存为CSV格式
    """
    rows = []
    for doc in docs:
        rows.append({
            "chunk_id": doc.chunk_id,
            "source_type": doc.source_type,
            "raw_text_len": len(doc.raw_text),
            "clean_text_len": len(doc.clean_text),
            "clean_text": doc.clean_text[:200],  # 前200字符
            "metadata_keys": str(list(doc.metadata.keys())),
        })
    
    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False, encoding='utf-8')
    
    print(f"✓ 已保存 {len(docs)} 个文档到 CSV: {output_path}")


def load_documents_pickle(pickle_path: str) -> List[Document]:
    """
    从pickle文件加载Document列表
    """
    with open(pickle_path, 'rb') as f:
        docs = pickle.load(f)
    return docs


def load_documents_json(json_path: str) -> List[Document]:
    """
    从JSON文件加载Document列表
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        docs_data = json.load(f)
    
    docs = []
    for item in docs_data:
        doc = Document(
            chunk_id=item['chunk_id'],
            raw_text=item['raw_text'],
            clean_text=item['clean_text'],
            metadata=item['metadata'],
            source_type=item['source_type']
        )
        docs.append(doc)
    return docs


def process_pipeline(
    call_parquet_path: str = None,
    news_parquet_path: str = None,
    output_dir: str = "data"
):
    """
    完整的处理管道
    
    Args:
        call_parquet_path: 电话会议 parquet 文件路径
        news_parquet_path: 股票新闻 parquet 文件路径
        output_dir: 输出目录
    """
    # 创建输出目录
    Path(output_dir).mkdir(exist_ok=True)
    
    print("=" * 60)
    print("开始处理管道...")
    print("=" * 60)
    
    # 1. 读取 parquet
    print("\n[步骤 1/6] 读取 parquet 文件...")
    docs_list = []
    
    if call_parquet_path and os.path.exists(call_parquet_path):
        print(f"  - 读取电话会议: {call_parquet_path}")
        call_docs = load_earning_call_parquet(call_parquet_path)
        docs_list.extend(call_docs)
        print(f"  ✓ 加载 {len(call_docs)} 个电话会议文档")
    
    if news_parquet_path and os.path.exists(news_parquet_path):
        print(f"  - 读取新闻: {news_parquet_path}")
        news_docs = load_stock_news_parquet(news_parquet_path)
        docs_list.extend(news_docs)
        print(f"  ✓ 加载 {len(news_docs)} 个新闻文档")
    
    if not docs_list:
        print("⚠ 没有找到可处理的文档！")
        return
    
    print(f"\n  总共加载文档数: {len(docs_list)}")
    
    # 2. 筛选文本字段 (已在 data_loader 中实现)
    print("\n[步骤 2/6] 筛选文本字段...")
    print(f"  - 已过滤无效记录和空文本")
    print(f"  - 保留文档数: {len(docs_list)}")
    
    # 3. 清洗文本 (已在 data_loader 中实现)
    print("\n[步骤 3/6] 清洗文本...")
    print(f"  - 清洗结果已存储在 Document.clean_text 中")
    
    # 4. 生成标准 Document (已在 data_loader 中实现)
    print("\n[步骤 4/6] 生成标准 Document...")
    print(f"  - Document 数量: {len(docs_list)}")
    
    # 统计信息
    call_count = sum(1 for d in docs_list if d.source_type == "earning_call")
    news_count = sum(1 for d in docs_list if d.source_type == "stock_news")
    print(f"    - 电话会议文档: {call_count}")
    print(f"    - 新闻文档: {news_count}")
    
    # 5. 切块
    print("\n[步骤 5/6] 切块处理...")
    chunked_docs = chunk_documents(docs_list, chunk_size=500, overlap=80)
    print(f"  ✓ 切块后文档数: {len(chunked_docs)}")
    
    # 统计切块结果
    original_count = len(docs_list)
    added_count = len(chunked_docs) - original_count
    if added_count > 0:
        print(f"  ✓ 新增子块数: {added_count}")
    
    # 6. 保存 processed documents
    print("\n[步骤 6/6] 保存处理后的文档...")
    
    # 分别保存电话会议和新闻数据
    call_docs = [doc for doc in chunked_docs if doc.source_type == "earning_call"]
    news_docs = [doc for doc in chunked_docs if doc.source_type == "stock_news"]
    
    output_files = []
    
    if call_docs:
        call_json_path = os.path.join(output_dir, "processed_earning_calls.json")
        save_documents_json(call_docs, call_json_path)
        output_files.append(call_json_path)
    
    if news_docs:
        news_json_path = os.path.join(output_dir, "processed_stock_news.json")
        save_documents_json(news_docs, news_json_path)
        output_files.append(news_json_path)
    
    print("\n" + "=" * 60)
    print("处理管道完成！")
    print("=" * 60)
    print(f"\n✓ 已保存 processed documents 到:")
    for file_path in output_files:
        print(f"  - {file_path}")
    
    return chunked_docs


if __name__ == "__main__":
    import sys
    
    # 设置默认路径
    call_path = 'data/stock_earning_call_transcripts.parquet'
    news_path = 'data/stock_news.parquet'
    output_path = 'data'  # 输出到 data 文件夹
    
    # 接受命令行参数
    if len(sys.argv) > 1:
        call_path = sys.argv[1]
    if len(sys.argv) > 2:
        news_path = sys.argv[2]
    if len(sys.argv) > 3:
        output_path = sys.argv[3]
    
    # 运行管道
    docs = process_pipeline(call_path, news_path, output_path)
