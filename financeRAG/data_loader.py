import pandas as pd
import pyarrow.parquet as pq
from typing import List
from document_schema import Document
from cleaner import clean_fin_text

def load_earning_call_parquet(parquet_path: str) -> List[Document]:
    """
    读取 stock_earning_call_transcripts parquet，展开嵌套字段，生成Document列表
    支持大型文件的分批读取
    """
    docs = []
    
    try:
        # 使用 pyarrow 分批读取大型文件
        parquet_file = pq.ParquetFile(parquet_path)
        
        # 分批读取各个 row groups
        for i in range(parquet_file.num_row_groups):
            # 读取单个 row group
            table = parquet_file.read_row_group(i)
            df = table.to_pandas()
            
            # 展开嵌套transcripts数组
            df_explode = df.explode("transcripts", ignore_index=True)
            
            for _, row in df_explode.iterrows():
                trans_item = row["transcripts"]
                
                # 跳过无效的记录（NaN、空值等）
                if not trans_item or not isinstance(trans_item, dict):
                    continue

                raw_content = trans_item.get("content", "")
                speaker = trans_item.get("speaker", "")
                clean_txt = clean_fin_text(raw_content)
                if not clean_txt:
                    continue

                # 组装元数据
                meta = {
                    "symbol": row["symbol"],
                    "fiscal_year": row["fiscal_year"],
                    "fiscal_quarter": row["fiscal_quarter"],
                    "report_date": row["report_date"],
                    "transcripts_id": row["transcripts_id"],
                    "speaker": speaker,
                    "paragraph_number": trans_item.get("paragraph_number", -1)
                }

                doc = Document(
                    chunk_id=f"call_{row['transcripts_id']}_{trans_item.get('paragraph_number', 0)}",
                    raw_text=f"Speaker:{speaker}, Content:{raw_content}",
                    clean_text=clean_txt,
                    metadata=meta,
                    source_type="earning_call"
                )
                docs.append(doc)
    except Exception as e:
        print(f"Warning: Error reading {parquet_path}: {e}")
    
    return docs


def load_stock_news_parquet(parquet_path: str) -> List[Document]:
    """
    读取 stock_news parquet，展开嵌套news数组，生成Document列表
    支持大型文件的分批读取
    """
    docs = []
    
    try:
        # 使用 pyarrow 分批读取大型文件
        parquet_file = pq.ParquetFile(parquet_path)
        
        # 分批读取各个 row groups
        for i in range(parquet_file.num_row_groups):
            # 读取单个 row group
            table = parquet_file.read_row_group(i)
            df = table.to_pandas()
            
            # 展开嵌套news数组
            df_explode = df.explode("news", ignore_index=True)
            for _, row in df_explode.iterrows():
                news_item = row["news"]
                
                # 跳过无效的记录（NaN、空值等）
                if not news_item or not isinstance(news_item, dict):
                    continue

                title = row["title"] if pd.notna(row["title"]) else ""
                highlight = news_item.get("highlight", "")
                paragraph = news_item.get("paragraph", "")
                raw_full = f"Title:{title}, Highlight:{highlight}, Paragraph:{paragraph}"
                clean_txt = clean_fin_text(raw_full)
                if not clean_txt:
                    continue

                # 组装元数据
                meta = {
                    "symbol": row["symbol"],
                    "uuid": row["uuid"],
                    "publisher": row["publisher"] if pd.notna(row["publisher"]) else "",
                    "report_date": row["report_date"],
                    "news_type": row["type"] if pd.notna(row["type"]) else "",
                    "link": row["link"] if pd.notna(row["link"]) else ""
                }

                doc = Document(
                    chunk_id=f"news_{row['uuid']}_{news_item.get('paragraph_number', 0)}",
                    raw_text=raw_full,
                    clean_text=clean_txt,
                    metadata=meta,
                    source_type="stock_news"
                )
                docs.append(doc)
    except Exception as e:
        print(f"Warning: Error reading {parquet_path}: {e}")
    
    return docs