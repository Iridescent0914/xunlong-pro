import os
from __init__ import (
    Document,
    clean_fin_text,
    load_earning_call_parquet,
    load_stock_news_parquet,
    chunk_documents,
    process_all_docs
)

def test_clean_text():
    """测试文本清洗函数"""
    print("===== 1. 测试文本清洗 clean_fin_text =====")
    raw = """
    Q3 revenue grew 15% year over year.
    
    The CEO said demand remains strong.
    """
    res = clean_fin_text(raw)
    print("原始文本：\n", raw)
    print("清洗后：\n", res)
    print("清洗后长度：", len(res))
    print("-" * 50)


def test_load_single_dataset():
    """分别测试加载电话会议、新闻数据集"""
    print("===== 2. 测试单数据集加载 =====")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    call_path = os.path.join(current_dir, "data", "stock_earning_call_transcripts.parquet")
    news_path = os.path.join(current_dir, "data", "stock_news.parquet")

    # 电话会议
    if os.path.exists(call_path):
        call_docs = load_earning_call_parquet(call_path)
        print(f"财报电话会议原始文档数：{len(call_docs)}")
        if call_docs:
            print("电话会议样本示例：")
            print(f"chunk_id: {call_docs[0].chunk_id}")
            print(f"clean_text: {call_docs[0].clean_text[:200]}...")
            print(f"metadata: {call_docs[0].metadata}")
    else:
        print("未找到 stock_earning_call_transcripts.parquet 文件，跳过")

    # 新闻  
    if os.path.exists(news_path):
        news_docs = load_stock_news_parquet(news_path)
        print(f"\n财经新闻原始文档数：{len(news_docs)}")
        if news_docs:
            print("新闻样本示例：")
            print(f"chunk_id: {news_docs[0].chunk_id}")
            print(f"clean_text: {news_docs[0].clean_text[:200]}...")
            print(f"metadata: {news_docs[0].metadata}")
    else:
        print("未找到 stock_news.parquet 文件，跳过")
    print("-" * 50)


def test_chunk_split():
    """测试切块逻辑，区分电话会议/新闻长文本分割"""
    print("===== 3. 测试文本切块 chunk_documents =====")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    call_path = os.path.join(current_dir, "data", "stock_earning_call_transcripts.parquet")
    news_path = os.path.join(current_dir, "data", "stock_news.parquet")

    if os.path.exists(call_path) and os.path.exists(news_path):
        all_raw = process_all_docs(call_path, news_path)
        print(f"切块后总分片数量：{len(all_raw)}")

        # 分别统计两种数据源数量
        call_cnt = sum(1 for d in all_raw if d.source_type == "earning_call")
        news_cnt = sum(1 for d in all_raw if d.source_type == "stock_news")
        print(f"电话会议分片：{call_cnt}")
        print(f"新闻分片：{news_cnt}")

        # 打印一条切块后的新闻子分片
        news_sample = next((d for d in all_raw if d.source_type == "stock_news"), None)
        if news_sample:
            print("\n切块后新闻样本：")
            print(f"chunk_id: {news_sample.chunk_id}")
            print(f"文本长度：{len(news_sample.clean_text)}")
            print(f"内容：{news_sample.clean_text[:300]}...")
    else:
        print("缺少数据集文件夹，跳过切块完整测试")
    print("-" * 50)


def run_all_test():
    """执行全部测试用例"""
    print("===== 开始执行全流程测试 =====")
    test_clean_text()
    test_load_single_dataset()
    test_chunk_split()
    print("\n===== 全部测试执行完成 =====")


if __name__ == "__main__":
    run_all_test()