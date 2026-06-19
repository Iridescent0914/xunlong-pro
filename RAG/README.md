# Annual Report PDF RAG

这个目录是一条独立实验路线：只处理公开年度报告 PDF，先做小样本 RAG 检索，不直接做完整财务数据库。

## 目标范围

- 公司数量：5 家国内外知名公司
- 时间范围：近 3 年年度报告，默认 `2024/2023/2022`
- 文件类型：PDF 年度报告
- 第一阶段产物：PDF 文本抽取、清洗、切块、JSONL、Chroma 检索

## 目录结构

```text
RAG/
├── config/targets.json          # 公司和爬取源配置
├── data/
│   ├── pdfs/                    # 下载的年度报告 PDF
│   ├── jsonl/                   # 抽取后的 RAG chunks
│   └── chroma_db/               # Chroma 持久化目录
├── scripts/
│   ├── crawl_reports.py         # 发现并下载 PDF，抽取文本，生成 JSONL
│   ├── build_index.py           # 构建 Chroma 向量索引
│   └── query_index.py           # 查询索引
└── src/rag_reports/
    ├── sources.py               # IR PDF / CNINFO 爬虫适配
    ├── pdf_parser.py            # PDF 文本抽取
    ├── cleaner.py               # 文本清洗
    ├── chunker.py               # 切块
    ├── pipeline.py              # 端到端处理流程
    └── indexer.py               # embedding + Chroma 检索
```

## 使用方式

先检查能发现哪些报告：

```bash
python RAG/scripts/crawl_reports.py --dry-run
```

只下载 PDF：

```bash
python RAG/scripts/download_reports.py
```

只从已有 PDF 生成 JSONL：

```bash
python RAG/scripts/extract_pdfs.py
```

也可以使用端到端脚本一次完成下载和抽取：

```bash
python RAG/scripts/crawl_reports.py
```

建议先分批验证，例如只下载 Apple 的 1 份报告：

```bash
python RAG/scripts/download_reports.py --company AAPL --limit-reports 1
python RAG/scripts/extract_pdfs.py --company AAPL --limit-reports 1
```

多家公司分批追加：

```bash
python RAG/scripts/extract_pdfs.py --company AAPL
python RAG/scripts/extract_pdfs.py --company MSFT --append
```

如果某次超时，可以按年份补跑，避免重复写入：

```bash
python RAG/scripts/extract_pdfs.py --company 600519 --year 2022 --append
python RAG/scripts/extract_pdfs.py --company 002594 --append
```

输出文件：

```text
RAG/data/jsonl/annual_reports.jsonl
RAG/data/jsonl/annual_reports.manifest.json
```

构建 Chroma 索引：

```bash
python RAG/scripts/build_index.py --reset
```

中断后续跑时不要加 `--reset`，脚本会默认跳过 Chroma 中已有的 chunk：

```bash
python RAG/scripts/build_index.py
```

如果 embedding 服务限制单次输入条数，可以调整批大小。部分 DashScope embedding 模型单批最多 10 条，脚本默认已经按 10 处理：

```bash
python RAG/scripts/build_index.py --reset --batch-size 10
```

查询：

```bash
python RAG/scripts/query_index.py "公司的主要风险因素有哪些？" --top-k 5
```

输出给金融数据分析智能体的 evidence pack：

```bash
python RAG/scripts/query_pack.py "贵州茅台行业格局 趋势 竞争优势" --top-k 8 --output RAG/data/jsonl/rag_pack.json
```

或者：

```bash
python RAG/scripts/query_index.py "贵州茅台行业格局 趋势 竞争优势" --top-k 8 --pack-json
```

主系统 `DataAnalysisAgent` 也可以直接接入本地年报 RAG。设置：

```env
ANNUAL_REPORT_RAG_ENABLED=true
ANNUAL_REPORT_RAG_PERSIST_DIR=RAG/data/chroma_db
ANNUAL_REPORT_RAG_COLLECTION=annual_report_rag
ANNUAL_REPORT_RAG_ENV_FILE=financeRAG/rag/.env
```

之后 `DataAnalysisAgent` 在未显式传入 `rag_pack` 时，会通过 `RAGClient.retrieve_pack()` 查询本地年报 Chroma，并转换为 `docs/rag输出格式.md` 里的 evidence pack。

## 环境变量

索引和查询复用 `financeRAG/rag/embedding_client.py` 的 OpenAI-compatible embedding 客户端。默认读取：

```text
financeRAG/rag/.env
```

需要配置：

```text
EMBEDDING_API_KEY=...
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4
```

也可以通过脚本参数指定其它 env 文件：

```bash
python RAG/scripts/build_index.py --env-file .env --reset
```

## 说明

国外公司的投资者关系页面经常由 JavaScript 渲染，通用 PDF 链接发现器可能抓不到全部报告。遇到这种情况时，可以在 `RAG/config/targets.json` 的公司配置里添加 `known_reports`：

```json
"known_reports": [
  {
    "year": 2025,
    "title": "Example 2025 Annual Report",
    "url": "https://example.com/annual-report-2025.pdf"
  }
]
```

国内 A 股年度报告走 `cninfo` 适配器，会从巨潮公告接口筛选年度报告 PDF。
