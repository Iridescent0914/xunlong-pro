# 公司财报 PDF RAG 使用说明

本文档说明项目中 `RAG/` 目录下的公司财报 PDF RAG。它只处理公司公开年度报告 PDF，用于给金融数据分析智能体提供年报级别证据；它不同于 `financeRAG/` 中基于 Yahoo Finance 数据集子集构建的 RAG。

## 1. 定位

公司财报 PDF RAG 的作用是：

```text
公开年度报告 PDF
  -> 文本抽取
  -> 文本清洗
  -> 文档切块
  -> JSONL
  -> Chroma 向量索引
  -> evidence pack
  -> RAGClient
  -> DataAnalysisAgent
```

它适合增强以下问题：

```text
公司年报中的收入、利润、毛利率、现金流等指标
管理层讨论与经营情况
风险因素、竞争格局、地区/业务分部表现
金融数据分析报告中的权威证据引用
```

与 Yahoo RAG 的区别：

| 项目 | 公司财报 PDF RAG | Yahoo 数据集 RAG |
| --- | --- | --- |
| 目录 | `RAG/` | `financeRAG/` |
| 数据来源 | 公司公开年度报告 PDF | Hugging Face Yahoo Finance 数据集子集 |
| 典型内容 | 年报、Form 10-K、风险因素、财务报表、管理层讨论 | 新闻、earning call、市场动态 |
| 优势 | 权威、可追溯、适合财报指标 | 更新、更贴近市场动态 |
| 开关 | `ANNUAL_REPORT_RAG_ENABLED` | `YAHOO_FINANCE_RAG_ENABLED` |

## 2. 当前覆盖范围

配置文件：

```text
RAG/config/targets.json
```

当前默认年份：

```text
2024 / 2023 / 2022
```

当前公司：

| Symbol | 公司 | 来源方式 |
| --- | --- | --- |
| `AAPL` | Apple Inc. | `known_reports` + IR 页面 |
| `MSFT` | Microsoft Corporation | `known_reports` + IR 页面 |
| `NVDA` | NVIDIA Corporation | IR 页面 |
| `600519` | 贵州茅台 | 巨潮资讯 cninfo |
| `002594` | 比亚迪 | 巨潮资讯 cninfo |

`RAGClient` 会读取这个配置。如果 query 识别出某个 ticker，但 `targets.json` 不覆盖该 ticker，则会跳过年报 RAG，避免误召回。

## 3. 目录结构

```text
RAG/
├── config/
│   └── targets.json              # 公司、年份、下载来源配置
├── data/
│   ├── pdfs/                     # 下载后的年报 PDF
│   ├── jsonl/                    # 抽取清洗切块后的 JSONL
│   └── chroma_db/                # Chroma 向量库持久化目录
├── scripts/
│   ├── download_reports.py       # 只下载 PDF
│   ├── extract_pdfs.py           # 从已有 PDF 抽取并生成 JSONL
│   ├── crawl_reports.py          # 发现/下载/抽取的端到端脚本
│   ├── build_index.py            # 构建 Chroma 向量索引
│   ├── query_index.py            # 查询索引
│   └── query_pack.py             # 输出 evidence pack
└── src/rag_reports/
    ├── sources.py                # IR PDF / CNINFO 来源适配
    ├── pdf_parser.py             # PDF 文本抽取
    ├── cleaner.py                # 文本清洗
    ├── chunker.py                # 切块
    ├── pipeline.py               # 处理流程
    ├── indexer.py                # embedding + Chroma 检索 + evidence pack
    └── models.py                 # 配置和报告记录模型
```

## 4. 处理流水线

核心流程在：

```text
RAG/src/rag_reports/pipeline.py
```

链路如下：

```text
run_pdf_rag_pipeline()
  -> discover_reports_only()     # dry-run，只发现报告并写 manifest
  -> download_reports_only()     # 下载 PDF
  -> extract_existing_pdfs()     # 解析本地 PDF，写 annual_reports.jsonl
```

`extract_existing_pdfs()` 会：

```text
1. 从 targets.json 选择公司和年份
2. 查找 RAG/data/pdfs/{symbol}_{year}_annual_report.pdf
3. pdf_parser.extract_pdf_pages() 抽取页面文本
4. chunker.chunk_pages() 按 chunk_size / overlap 切块
5. 写入 RAG/data/jsonl/annual_reports.jsonl
6. 写入 RAG/data/jsonl/annual_reports.manifest.json
```

当前已修复一个 dry-run 细节：`discover_reports_only()` 现在显式接收 `append: bool = False`，`run_pdf_rag_pipeline(..., dry_run=True, append=True)` 不会再因为未声明 `append` 触发 `NameError`。

## 5. 环境准备

建议使用项目虚拟环境：

```powershell
conda activate SmartFin
```

年报 RAG 的索引构建和查询复用：

```text
financeRAG/rag/embedding_client.py
```

默认读取：

```text
financeRAG/rag/.env
```

至少需要：

```env
EMBEDDING_API_KEY=你的 embedding key
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4
```

如果服务限制单批输入数量，构建索引时使用 `--batch-size 10`。

## 6. 主系统开关配置

只启用公司财报 PDF RAG，关闭 Yahoo RAG：

```env
DATA_ANALYSIS_RAG_MOCK=false
ANNUAL_REPORT_RAG_ENABLED=true
ANNUAL_REPORT_RAG_PERSIST_DIR=RAG/data/chroma_db
ANNUAL_REPORT_RAG_COLLECTION=annual_report_rag
ANNUAL_REPORT_RAG_ENV_FILE=financeRAG/rag/.env
YAHOO_FINANCE_RAG_ENABLED=false
FINANCIAL_RAG_SYMBOL_ALIASES_FILE=financeRAG/rag/company_aliases.json
```

当前项目根目录 `.env` 就是这种配置。

## 7. 构建年报 RAG

### 7.1 dry-run 检查可发现报告

```powershell
python RAG/scripts/crawl_reports.py --dry-run
```

### 7.2 只下载 PDF

下载全部目标公司：

```powershell
python RAG/scripts/download_reports.py
```

调试时先下载 Apple 的 1 份报告：

```powershell
python RAG/scripts/download_reports.py --company AAPL --limit-reports 1
```

### 7.3 从 PDF 生成 JSONL

```powershell
python RAG/scripts/extract_pdfs.py
```

只处理 Apple 的 1 份报告：

```powershell
python RAG/scripts/extract_pdfs.py --company AAPL --limit-reports 1
```

多家公司分批追加：

```powershell
python RAG/scripts/extract_pdfs.py --company AAPL
python RAG/scripts/extract_pdfs.py --company MSFT --append
```

按公司或年份补跑：

```powershell
python RAG/scripts/extract_pdfs.py --company 600519 --year 2022 --append
python RAG/scripts/extract_pdfs.py --company 002594 --append
```

生成文件：

```text
RAG/data/jsonl/annual_reports.jsonl
RAG/data/jsonl/annual_reports.manifest.json
```

### 7.4 一步完成下载和抽取

```powershell
python RAG/scripts/crawl_reports.py
```

调试阶段建议优先分步执行，便于定位是下载、PDF 解析还是索引构建出了问题。

### 7.5 构建 Chroma 索引

首次构建或需要清空重建：

```powershell
python RAG/scripts/build_index.py --reset --batch-size 10
```

中断后续跑，不要加 `--reset`，脚本会默认跳过 Chroma 中已有 chunk：

```powershell
python RAG/scripts/build_index.py --batch-size 10
```

默认索引目录：

```text
RAG/data/chroma_db
```

默认 collection：

```text
annual_report_rag
```

## 8. 查询和 evidence pack

普通查询：

```powershell
python RAG/scripts/query_index.py "AAPL 2024 Form 10-K net sales gross margin risk factors" --top-k 5
```

输出 evidence pack：

```powershell
python RAG/scripts/query_pack.py "AAPL 2024 Form 10-K net sales gross margin risk factors" --top-k 5
```

保存到文件：

```powershell
python RAG/scripts/query_pack.py "AAPL 2024 Form 10-K net sales gross margin risk factors" --top-k 8 --output RAG/data/jsonl/aapl_rag_pack.json
```

`RAG/src/rag_reports/indexer.py` 的 `build_evidence_pack()` 会生成：

```text
source=financial_rag
query
normalized_query
entities
retrieval_scope
  doc_types=[annual_report]
  top_k
evidence[]
rag_summary
quality
```

年报 evidence 每条包含：

```text
evidence_id
doc_id
doc_type=annual_report
title
date/source/url
ticker/company_name
chunk_id
content/summary
score
metadata.page_start / metadata.page_end / metadata.local_pdf / metadata.language
```

这些字段会被 `evidence_adapter.rag_pack_to_refs()` 保留下来，用于最终报告展示 RAG 来源标题、URL、日期和页码。

## 9. 接入金融数据分析全链路

命令行入口：

```powershell
python SmartFin.py analyze "AAPL 2024 Form 10-K net sales gross margin risk factors financial analysis" --depth deep -m 8 -o html -v
```

中文 query：

```powershell
python SmartFin.py analyze "分析 Apple 2024 年报中的收入、毛利率和风险因素，并结合网页资料给出金融数据分析报告" --depth deep -m 8 -o html -v
```

运行链路：

```text
SmartFin.py analyze
  -> DeepSearchCoordinator financial_analysis
  -> DeepSearcher 获取网页搜索结果
  -> DataAnalysisAgent
  -> RAGClient._query_local_annual_report_pack()
  -> RAG/src/rag_reports/indexer.py query_evidence_pack()
  -> LLMSearchAnalyzer 抽取 [W]/[R] 来源表格
  -> ReportCoordinator / PPTCoordinator 输出
```

运行完成后重点查看：

```text
storage/{project_id}/intermediate/02_search_results.json
storage/{project_id}/intermediate/03_data_analysis.json
storage/{project_id}/reports/FINAL_REPORT.html
storage/{project_id}/reports/FINAL_REPORT.md
```

`03_data_analysis.json` 中的 `rag_refs` 应包含年报来源、日期和页码信息。

## 10. 常见问题

### 10.1 RAG 没有召回证据

检查：

```text
1. RAG/data/chroma_db 是否存在
2. RAG/data/jsonl/annual_reports.jsonl 是否存在且非空
3. financeRAG/rag/.env 是否配置 embedding
4. query 是否包含目标公司名称或 ticker，例如 AAPL、Apple
5. ANNUAL_REPORT_RAG_COLLECTION 是否为 annual_report_rag
6. 目标公司是否在 RAG/config/targets.json 中
```

先跑：

```powershell
python RAG/scripts/query_pack.py "AAPL 2024 annual report revenue gross margin" --top-k 5
```

### 10.2 网页搜索有结果，但数据分析只用了 RAG

通常说明网页结果没有通过相关性筛选，或者网页正文没有明确财务数值。可以使用更明确的英文 query：

```powershell
python SmartFin.py analyze "AAPL 2024 Form 10-K net sales gross margin risk factors financial analysis" --depth deep -m 8 -o html -v
```

### 10.3 出现 mock RAG 证据

确认：

```env
DATA_ANALYSIS_RAG_MOCK=false
```

只有显式设置 `DATA_ANALYSIS_RAG_MOCK=true` 时，系统才读取 `fixtures/mock_rag.json`。

### 10.4 前端数据分析按钮不可用

当前静态前端中的数据分析模块请求 `/api/v1/tasks/analysis`，但后端任务接口暂未实现该路由。完整链路建议先使用：

```powershell
python SmartFin.py analyze ...
```

`/api/v1/data_analysis/charts` 只消费传入的 `search_results` 并查询 RAG，本身不会自动发起网页搜索。

## 11. 验证命令

语法检查：

```powershell
python -m py_compile RAG/src/rag_reports/pipeline.py RAG/src/rag_reports/indexer.py src/agents/data_analysis/rag_client.py src/agents/data_analysis/evidence_adapter.py src/agents/data_analysis/report_section.py src/agents/data_analysis/data_analysis_agent.py
```

年报 RAG 单测式验证：

```powershell
python RAG/scripts/query_pack.py "AAPL 2024 annual report revenue gross margin risk factors" --top-k 5
```
