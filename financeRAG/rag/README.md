# FinanceRAG RAG 使用说明

这个目录负责 RAG 的向量化、Chroma 向量库写入和检索查询。当前流程是：

```text
processed JSONL documents
  -> 读取并筛选文档
  -> 调用 embedding 模型生成向量
  -> 写入 Chroma
  -> 查询 Chroma
  -> 可选：调用 LLM 基于召回内容生成回答
```

## 目录说明

```text
financeRAG/rag/
  .env                  本地 RAG 配置，包含 API key，不提交 git
  config.py             读取 RAG 配置
  embedding_client.py   OpenAI-compatible embedding 客户端
  jsonl_loader.py       流式读取 processed JSONL 文档
  chroma_indexer.py     写入 Chroma 向量库
  chroma_db/            本地 Chroma 数据库目录
```

相关脚本在：

```text
financeRAG/scripts/build_chroma_index.py   构建 Chroma 索引
financeRAG/scripts/query_chroma.py         查询 Chroma
```

## 配置

先确保存在：

```text
financeRAG/rag/.env
```

可以从模板复制：

```powershell
Copy-Item financeRAG\rag\.env.example financeRAG\rag\.env
```

主要配置项：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here

LLM_MODEL=qwen3.6-plus
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MAX_BATCH_SIZE=10

CHROMA_PERSIST_DIR=financeRAG/rag/chroma_db
CHROMA_COLLECTION=finance_rag
```

注意：

- `.env` 只放在 `financeRAG/rag/` 里面，不和全局配置混在一起。
- `DASHSCOPE_API_KEY` 不要提交到 git。
- `text-embedding-v3` 单次 embedding batch 建议保持 `10`，否则可能报 batch size 超限。

## 输入数据

默认读取已经处理好的 JSONL：

```text
financeRAG/processed_data_optimized/*_batch_*.jsonl
```

每条 processed document 大致结构：

```json
{
  "doc_id": "xxx_chunk_0",
  "content": "正文内容...",
  "metadata": {
    "source": "stock_news",
    "symbol": "A",
    "report_date": "2025-12-20"
  },
  "chunk_index": 0,
  "chunk_size": 512,
  "chunk_overlap": 100
}
```

RAG 建库时真正进入向量库的是 `content`，`metadata` 会作为过滤和溯源信息一起写入 Chroma。

## 快速测试

先用很小的数据量测试 embedding、Chroma 写入和查询是否正常：

```powershell
python financeRAG/scripts/build_chroma_index.py --reset --profile custom --source stock_news --limit 100 --batch-size 10 --embedding-batch-size 10
```

测试查询：

```powershell
python financeRAG/scripts/query_chroma.py "Agilent 2025 revenue growth" --top-k 5
```

如果要让 LLM 根据召回内容生成回答：

```powershell
python financeRAG/scripts/query_chroma.py "Agilent 2025 revenue growth" --top-k 5 --answer
```

## 当前推荐建库方式

现在推荐先建立一个较小但可用的子集：

```powershell
python financeRAG/scripts/build_chroma_index.py --reset --news-sample 10000 --limit 100000 --batch-size 10 --embedding-batch-size 10
```

这个命令使用默认 profile：

```text
news-random-call-2025-2026
```

含义是：

```text
stock_news: 从 news 中随机抽取 10,000 条
stock_earning_call: 只取 2025-2026 年，最多 100,000 条
总量: 约 110,000 条 chunk/document
```

和全部 processed documents 约 34,522,692 条相比，当前建库量大约是：

```text
110,000 / 34,522,692 ~= 0.32%
```

## 自定义建库示例

只建 2025-2026 年 earning call：

```powershell
python financeRAG/scripts/build_chroma_index.py --reset --profile custom --source stock_earning_call --year-from 2025 --year-to 2026 --limit 100000 --batch-size 10 --embedding-batch-size 10
```

只建随机 news：

```powershell
python financeRAG/scripts/build_chroma_index.py --reset --profile custom --source stock_news --random-sample 10000 --batch-size 10 --embedding-batch-size 10
```

追加写入而不是重建：

```powershell
python financeRAG/scripts/build_chroma_index.py --profile custom --source stock_earning_call --year-from 2025 --year-to 2026 --limit 10000 --batch-size 10 --embedding-batch-size 10
```

注意：去掉 `--reset` 就不会删除已有 collection，会继续 upsert 到同一个 Chroma collection。

## 查询示例

按股票代码过滤：

```powershell
python financeRAG/scripts/query_chroma.py "2025 earnings call revenue growth" --symbol A --top-k 5
```

只查 earning call：

```powershell
python financeRAG/scripts/query_chroma.py "2025 earnings call margin guidance" --source stock_earning_call --top-k 5
```

只查 news：

```powershell
python financeRAG/scripts/query_chroma.py "Agilent recent acquisition news" --source stock_news --top-k 5
```

召回后生成中文回答：

```powershell
python financeRAG/scripts/query_chroma.py "Agilent 2025 年 earnings call 提到了哪些增长点？" --source stock_earning_call --symbol A --top-k 5 --answer
```

## 常用参数

| 参数 | 作用 |
| --- | --- |
| `--reset` | 删除并重建 Chroma collection |
| `--profile custom` | 使用自定义过滤逻辑 |
| `--profile news-random-call-2025-2026` | 默认 profile：news 随机抽样 + call 取 2025-2026 |
| `--news-sample 10000` | 默认 profile 中 news 随机抽样数量 |
| `--limit 100000` | 限制写入数量；在默认 profile 中用于 call 部分 |
| `--source stock_news` | 只处理 news |
| `--source stock_earning_call` | 只处理 earning call |
| `--year-from 2025` | 最小年份 |
| `--year-to 2026` | 最大年份 |
| `--batch-size 10` | 每批写入 Chroma 的文档数 |
| `--embedding-batch-size 10` | 每次请求 embedding API 的文本条数 |
| `--persist-dir` | 指定 Chroma 存储目录 |
| `--collection` | 指定 Chroma collection 名称 |


## 推荐流程

1. 先确认 `financeRAG/rag/.env` 配置正确。
2. 用 `--limit 100` 做快速测试。
3. 测试查询能召回内容。
4. 再运行推荐的 110,000 条左右子集建库命令。
5. 用 `query_chroma.py` 做检索测试。
6. 需要自然语言答案时加 `--answer`。

## 接入金融数据分析智能体

当前主流程已经支持同时检索两套 RAG：

```text
RAG/data/chroma_db           公开公司年报 PDF RAG
financeRAG/rag/chroma_db     Yahoo Finance 数据集子集 RAG
```

在项目根目录 `.env` 中开启：

```env
ANNUAL_REPORT_RAG_ENABLED=true
ANNUAL_REPORT_RAG_PERSIST_DIR=RAG/data/chroma_db
ANNUAL_REPORT_RAG_COLLECTION=annual_report_rag
ANNUAL_REPORT_RAG_ENV_FILE=financeRAG/rag/.env

YAHOO_FINANCE_RAG_ENABLED=true
YAHOO_FINANCE_RAG_PERSIST_DIR=financeRAG/rag/chroma_db
YAHOO_FINANCE_RAG_COLLECTION=finance_rag
YAHOO_FINANCE_RAG_ENV_FILE=financeRAG/rag/.env
```

接入点在：

```text
src/agents/data_analysis/rag_client.py
```

`DataAnalysisAgent` 会调用 `RAGClient.retrieve()`，该客户端会分别查询年报 PDF RAG 和 Yahoo Finance RAG，再合并为统一的 `RAGReference` 证据列表传给金融数据分析模块。

