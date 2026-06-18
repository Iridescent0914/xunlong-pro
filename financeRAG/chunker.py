from typing import List
from document_schema import Document
from cleaner import clean_fin_text

def split_long_text(text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
    """
    长文本滑动窗口切块，英文按字符分割
    """
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end]
        chunks.append(chunk)
        start += (chunk_size - overlap)
    return chunks


def chunk_documents(doc_list: List[Document], chunk_size=500, overlap=80) -> List[Document]:
    """
    对原始Document二次切块：
    - earning_call：单段发言一般较短，不二次分割
    - stock_news：超长段落自动滑动切分，生成新Document
    """
    final_docs = []
    for doc in doc_list:
        # 财报电话会议：单条发言天然chunk，直接保留
        if doc.source_type == "earning_call":
            final_docs.append(doc)
            continue

        # 新闻长文本做滑动切块
        clean_text = doc.clean_text
        if len(clean_text) <= chunk_size:
            final_docs.append(doc)
            continue

        sub_texts = split_long_text(clean_text, chunk_size, overlap)
        for idx, sub_txt in enumerate(sub_texts):
            new_meta = doc.metadata.copy()
            new_meta["chunk_sub_idx"] = idx
            new_doc = Document(
                chunk_id=f"{doc.chunk_id}_sub{idx}",
                raw_text=doc.raw_text,
                clean_text=sub_txt,
                metadata=new_meta,
                source_type=doc.source_type
            )
            final_docs.append(new_doc)
    return final_docs


# 统一入口函数，一键加载+清洗+切块
def process_all_docs(call_parquet_path: str, news_parquet_path: str) -> List[Document]:
    from data_loader import load_earning_call_parquet, load_stock_news_parquet
    # 加载并清洗原始文档
    call_docs = load_earning_call_parquet(call_parquet_path)
    news_docs = load_stock_news_parquet(news_parquet_path)
    all_raw_docs = call_docs + news_docs
    # 切块
    chunked_docs = chunk_documents(all_raw_docs, chunk_size=500, overlap=80)
    return chunked_docs