# Yahoo 数据集 RAG 使用说明

本文档说明 `financeRAG/` 下 Yahoo Finance 数据集子集 RAG 的数据来源、处理流程、建库、查询和接入主流程的方式。

## 1. 数据来源和定位

当前 Yahoo RAG 使用 Hugging Face 数据集的一部分：

```text
https://huggingface.co/datasets/defeatbeta/yahoo-finance-data/tree/main/data
```

项目没有把完整数据集全部向量化，而是取其中一部分金融文本，主要包括：

```text
stock_news                  股票新闻、市场资讯
stock_earning_call          财报电话会、业绩交流文本
```

它和 `RAG/` 的公司财报 PDF RAG 定位不同：

| 项目 | Yahoo 数据集 RAG | 公司财报 PDF RAG |
| --- | --- | --- |
| 目录 | `financeRAG/` | `RAG/` |
| 数据来源 | Hugging Face Yahoo Finance 数据集子集 | 公司公开年度报告 PDF |
| 典型内容 | 新闻、earning call、市场动态 | 年报、Form 10-K、风险因素、管理层讨论 |
| 优势 | 动态背景更丰富 | 权威性更强 |
| 风险 | 数据集是子集，文本可能为二手资料 | PDF 表格抽取可能有噪声 |
| 主流程开关 | `YAHOO_FINANCE_RAG_ENABLED` | `ANNUAL_REPORT_RAG_ENABLED` |

当前项目根目录 `.env` 中 Yahoo RAG 默认关闭：

```env
YAHOO_FINANCE_RAG_ENABLED=false
```

如果要启用，需要改为 `true`。

## 2. 目录结构

```text
financeRAG/
├── data/                              # 原始 parquet 数据，通常不提交 git
│   ├── stock_news.parquet
│   └── stock_earning_call_transcripts.parquet
├── processed_data_optimized/           # 处理后的 JSONL，通常本地生成
├── processor/
│   ├── reader.py                       # 读取 stock_news / earning call
│   ├── cleaner.py                      # 文本清洗
│   ├── chunker.py                      # 文本切块
│   ├── models.py                       # Document / metadata 模型
│   └── pipeline.py                     # parquet -> JSONL 流水线
├── scripts/
│   ├── process_finance_data.py          # parquet -> processed JSONL
│   ├── build_chroma_index.py            # processed JSONL -> Chroma
│   └── query_chroma.py                  # 单独查询 Yahoo Chroma
└── rag/
    ├── config.py                        # RAG 配置读取
    ├── embedding_client.py              # OpenAI-compatible embedding 客户端
    ├── jsonl_loader.py                  # 读取 processed JSONL
    ├── chroma_indexer.py                # 写入 Chroma
    ├── chroma_db/                       # Chroma 持久化目录
    └── company_aliases.json             # 公司别名 -> ticker
```

当前仓库中已能看到：

```text
financeRAG/rag/chroma_db/chroma.sqlite3
```

说明本地已有 Yahoo Chroma 库文件，但主流程是否使用它由 `.env` 开关决定。

## 3. 原始数据处理

处理入口：

```text
financeRAG/scripts/process_finance_data.py
```

处理流程：

```text
parquet 文件
  -> FinanceDataPipeline
  -> reader 读取 stock_news 或 stock_earning_call
  -> TextCleaner 清洗 HTML、URL、特殊字符等
  -> TextChunker 切块，默认 chunk_size=512, overlap=100
  -> 分批写出 processed_data_optimized/*_batch_*.jsonl
```

脚本默认参数：

```text
DATA_DIR=financeRAG/data
OUTPUT_DIR=financeRAG/processed_data_optimized
CHUNK_SIZE=512
CHUNK_OVERLAP=100
MAX_RECORDS_PER_BATCH=50000
```

输出 JSONL 每行大致结构：

```json
{
  "doc_id": "...",
  "content": "清洗切块后的文本",
  "metadata": {
    "source": "stock_news",
    "symbol": "AAPL",
    "title": "...",
    "publisher": "...",
    "report_date": "2025-01-01"
  },
  "chunk_index": 0,
  "chunk_size": 512,
  "chunk_overlap": 100
}
```

## 4. 构建 Chroma 索引

建库入口：

```text
financeRAG/scripts/build_chroma_index.py
```

默认 profile：

```text
news-random-call-2025-2026
```

含义：

```text
stock_news：随机抽样，默认 news_sample=10000
stock_earning_call：取 2025-2026 年数据
```

推荐命令：

```powershell
python financeRAG/scripts/build_chroma_index.py --reset --news-sample 10000 --limit 100000 --batch-size 10 --embedding-batch-size 10
```

只建 earning call：

```powershell
python financeRAG/scripts/build_chroma_index.py --reset --profile custom --source stock_earning_call --year-from 2025 --year-to 2026 --limit 100000 --batch-size 10 --embedding-batch-size 10
```

只建新闻：

```powershell
python financeRAG/scripts/build_chroma_index.py --reset --profile custom --source stock_news --random-sample 10000 --batch-size 10 --embedding-batch-size 10
```

默认写入：

```text
financeRAG/rag/chroma_db
collection=finance_rag
```

## 5. Embedding 配置

Yahoo RAG 默认读取：

```text
financeRAG/rag/.env
```

常用配置：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MAX_BATCH_SIZE=10
CHROMA_PERSIST_DIR=financeRAG/rag/chroma_db
CHROMA_COLLECTION=finance_rag
```

注意：`financeRAG/rag/.env` 中的 API key 不要提交到 git。

## 6. 单独查询 Yahoo RAG

不经过主流程时，可以直接查 Chroma：

```powershell
python financeRAG/scripts/query_chroma.py "Agilent 2025 revenue growth" --top-k 5
```

按 ticker 过滤：

```powershell
python financeRAG/scripts/query_chroma.py "2025 earnings call revenue growth" --symbol A --top-k 5
```

只查 earning call：

```powershell
python financeRAG/scripts/query_chroma.py "2025 earnings call margin guidance" --source stock_earning_call --symbol A --top-k 5
```

只查新闻：

```powershell
python financeRAG/scripts/query_chroma.py "Agilent recent acquisition news" --source stock_news --top-k 5
```

## 7. 接入主流程

主流程入口在：

```text
src/agents/data_analysis/rag_client.py
```

启用 Yahoo RAG：

```env
DATA_ANALYSIS_RAG_MOCK=false
YAHOO_FINANCE_RAG_ENABLED=true
YAHOO_FINANCE_RAG_PERSIST_DIR=financeRAG/rag/chroma_db
YAHOO_FINANCE_RAG_COLLECTION=finance_rag
YAHOO_FINANCE_RAG_ENV_FILE=financeRAG/rag/.env
FINANCIAL_RAG_SYMBOL_ALIASES_FILE=financeRAG/rag/company_aliases.json
```

如果只想测试 Yahoo RAG、暂时不使用年报 RAG：

```env
ANNUAL_REPORT_RAG_ENABLED=false
YAHOO_FINANCE_RAG_ENABLED=true
```

如果两个库都启用，`RAGClient` 会分别检索并合并成：

```text
source=multi_financial_rag
```

## 8. Yahoo RAG 在 RAGClient 中的具体行为

`RAGClient._query_yahoo_finance_pack()` 会：

```text
1. 读取 financeRAG/rag/.env
2. 使用 OpenAICompatibleEmbeddingClient 生成 query embedding
3. 打开 financeRAG/rag/chroma_db 的 finance_rag collection
4. 尝试从 query 中识别 symbol
5. 如果识别到 symbol，则 where={"symbol": symbol}
6. 查询 Chroma documents / metadatas / distances
7. 将结果包装成 RAGEvidencePack
```

每条 evidence 会保留：

```text
evidence_id
doc_type，例如 stock_news / stock_earning_call
title
source=yahoo_finance_dataset
url
ticker
content
summary
score
metadata
```

之后 `evidence_adapter.rag_pack_to_refs()` 会进一步转成 `rag_refs`，供报告展示标题、链接、日期、ticker 等信息。

## 9. 公司名和 ticker 映射

别名文件：

```text
financeRAG/rag/company_aliases.json
```

示例：

```json
{
  "aliases": {
    "AAPL": ["Apple", "Apple Inc.", "苹果"],
    "A": ["Agilent", "Agilent Technologies", "安捷伦"]
  }
}
```

自然语言 query 写公司名时，主流程会尽量映射到 ticker，再用于 Chroma 过滤。

显式 ticker 也支持：

```text
$AAPL
ticker=AAPL
symbol=AAPL
NASDAQ:AAPL
```

## 10. 端到端测试

启用 Yahoo RAG 后运行：

```powershell
python xunlong.py analyze "Agilent 2025 earnings call revenue growth and margin guidance" --depth deep -m 8 -o html -v
```

中文 query：

```powershell
python xunlong.py analyze "分析 Agilent 2025 年 earnings call 中的收入增长、利润率指引和风险因素，并结合网页搜索资料" --depth deep -m 8 -o html -v
```

运行时关注日志：

```text
[RAGClient] Yahoo Finance RAG ...
[DataAnalysisAgent] RAG retrieved N evidence items
[LLMSearchAnalyzer] 抽取完成：N 行数值，来源 N 条
```

输出重点看：

```text
storage/{project_id}/intermediate/03_data_analysis.json
```

其中 `rag_refs` 应包含 Yahoo 证据来源。

## 11. 注意事项

- Yahoo RAG 当前只覆盖已抽取的数据集子集，不代表完整 Yahoo Finance 数据。
- earning call 和新闻可能包含二手描述，建议结合年报 RAG 和网页搜索交叉验证。
- 如果 query 不能识别 ticker，检索会退化为不加 symbol 过滤，召回可能更杂。
- 如果 `.env` 中 `YAHOO_FINANCE_RAG_ENABLED=false`，主流程不会使用该库。
- `DATA_ANALYSIS_RAG_MOCK=true` 只用于 demo 或测试，不建议真实分析时打开。
