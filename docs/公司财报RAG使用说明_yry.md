# 公司财报 PDF RAG 使用说明

本文档说明项目中 `RAG/` 目录下的公司财报 PDF RAG。它只处理公司公开年度报告 PDF，用于给金融数据分析智能体提供年报证据；它不同于 `financeRAG/` 中基于 Yahoo Finance 数据集构建的 RAG。

## 1. 定位

公司财报 PDF RAG 的作用是：

```text
公开年度报告 PDF
  -> 文本抽取
  -> 文本清洗
  -> 文档切块
  -> JSONL
  -> Chroma 向量索引
  -> RAGClient 检索
  -> DataAnalysisAgent / FinancialAnalyzer 使用证据
```

它适合回答或增强以下问题：

- 公司年报中的收入、毛利率、利润、现金流等指标；
- 管理层讨论与经营情况；
- 风险因素、竞争格局、地区/业务分部表现；
- 金融数据分析报告中的权威证据引用。

当前默认覆盖公司见 `RAG/config/targets.json`：

| Symbol | 公司 | 来源 |
| --- | --- | --- |
| `AAPL` | Apple Inc. | 年报 PDF 链接 / IR 页面 |
| `MSFT` | Microsoft Corporation | 年报 PDF 链接 / IR 页面 |
| `NVDA` | NVIDIA Corporation | IR 页面 |
| `600519` | 贵州茅台 | 巨潮资讯 `cninfo` |
| `002594` | 比亚迪 | 巨潮资讯 `cninfo` |

默认年份范围为 `2024/2023/2022`。

## 2. 目录结构

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
    └── indexer.py                # embedding + Chroma 检索
```

## 3. 环境准备

建议使用项目虚拟环境：

```powershell
conda activate xunlong
```

年报 RAG 的索引构建和查询需要 embedding 配置，默认读取：

```text
financeRAG/rag/.env
```

至少需要：

```env
EMBEDDING_API_KEY=你的 embedding key
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4
```

如果 embedding 服务限制单批输入数量，构建索引时使用 `--batch-size 10`。

## 4. 主系统开关配置

在项目根目录 `.env` 中，只启用公司财报 PDF RAG，关闭 Yahoo 数据集 RAG：

```env
DATA_ANALYSIS_RAG_MOCK=false

ANNUAL_REPORT_RAG_ENABLED=true
ANNUAL_REPORT_RAG_PERSIST_DIR=RAG/data/chroma_db
ANNUAL_REPORT_RAG_COLLECTION=annual_report_rag
ANNUAL_REPORT_RAG_ENV_FILE=financeRAG/rag/.env

YAHOO_FINANCE_RAG_ENABLED=false

FINANCIAL_RAG_SYMBOL_ALIASES_FILE=financeRAG/rag/company_aliases.json
```

含义：

- `DATA_ANALYSIS_RAG_MOCK=false`：不混入 `fixtures/mock_rag.json`；
- `ANNUAL_REPORT_RAG_ENABLED=true`：启用 `RAG/` 下的年报 Chroma；
- `YAHOO_FINANCE_RAG_ENABLED=false`：暂时不使用 `financeRAG/` 的 Yahoo 数据集 RAG；
- `FINANCIAL_RAG_SYMBOL_ALIASES_FILE`：用于把 Apple、AAPL、微软等名称映射到 ticker，辅助检索过滤。

## 5. 构建年报 RAG

### 5.1 检查可发现的报告

```powershell
python RAG/scripts/crawl_reports.py --dry-run
```

### 5.2 只下载 PDF

下载全部目标公司：

```powershell
python RAG/scripts/download_reports.py
```

建议调试时先下载 Apple 的 1 份报告：

```powershell
python RAG/scripts/download_reports.py --company AAPL --limit-reports 1
```

### 5.3 从 PDF 生成 JSONL

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

如果中途超时，可以按公司或年份补跑：

```powershell
python RAG/scripts/extract_pdfs.py --company 600519 --year 2022 --append
python RAG/scripts/extract_pdfs.py --company 002594 --append
```

生成文件：

```text
RAG/data/jsonl/annual_reports.jsonl
RAG/data/jsonl/annual_reports.manifest.json
```

### 5.4 一步完成下载和抽取

```powershell
python RAG/scripts/crawl_reports.py
```

调试阶段建议优先分步执行，便于定位是下载、PDF 解析还是索引构建出了问题。

### 5.5 构建 Chroma 索引

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

## 6. 单独测试年报 RAG

### 6.1 查询普通检索结果

```powershell
python RAG/scripts/query_index.py "AAPL 2024 Form 10-K net sales gross margin risk factors" --top-k 5
```

### 6.2 查询 evidence pack

`DataAnalysisAgent` 更适合消费 evidence pack 格式：

```powershell
python RAG/scripts/query_pack.py "AAPL 2024 Form 10-K net sales gross margin risk factors" --top-k 5
```

保存到文件：

```powershell
python RAG/scripts/query_pack.py "AAPL 2024 Form 10-K net sales gross margin risk factors" --top-k 8 --output RAG/data/jsonl/aapl_rag_pack.json
```

如果输出中 `evidence` 非空，说明年报 RAG 可以正常召回。

## 7. 接入金融数据分析全链路

命令行全链路推荐使用 `xunlong.py analyze`：

```powershell
python xunlong.py analyze "AAPL 2024 Form 10-K net sales gross margin risk factors financial analysis" --depth deep -m 8 -o html -v
```

中文 query 也可以：

```powershell
python xunlong.py analyze "分析 Apple 2024 年报中的收入、毛利率和风险因素，并结合网页资料给出金融数据分析报告" --depth deep -m 8 -o html -v
```

该命令会经过：

```text
DeepSearchAgent
  -> Coordinator
  -> 网页搜索
  -> RAGClient 查询公司年报 RAG
  -> DataAnalysisAgent / FinancialAnalyzer
  -> ReportCoordinator 生成报告
```

运行完成后重点查看：

```text
storage/{project_id}/intermediate/02_search_results.json
storage/{project_id}/intermediate/03_data_analysis.json
storage/{project_id}/reports/FINAL_REPORT.html
storage/{project_id}/reports/FINAL_REPORT.md
```

其中：

- `02_search_results.json`：网页搜索结果；
- `03_data_analysis.json`：金融数据分析智能体输出，包含 `rag_refs` 和 `search_refs`；
- `FINAL_REPORT.html/md`：最终报告。

## 8. 与 Yahoo 数据集 RAG 的区别

| 项目 | 公司财报 PDF RAG | Yahoo 数据集 RAG |
| --- | --- | --- |
| 目录 | `RAG/` | `financeRAG/` |
| 数据来源 | 公司公开年度报告 PDF | Hugging Face Yahoo Finance 数据集子集 |
| 典型内容 | 年报、Form 10-K、风险因素、财务报表、管理层讨论 | 新闻、earning call、市场动态等 |
| 主要用途 | 提供权威年报证据 | 补充市场资讯和动态背景 |
| 开关 | `ANNUAL_REPORT_RAG_ENABLED` | `YAHOO_FINANCE_RAG_ENABLED` |

如果只测试公司财报 RAG，请保持：

```env
ANNUAL_REPORT_RAG_ENABLED=true
YAHOO_FINANCE_RAG_ENABLED=false
```

## 9. 常见问题

### 9.1 RAG 没有召回证据

检查：

1. `RAG/data/chroma_db` 是否存在；
2. `RAG/data/jsonl/annual_reports.jsonl` 是否存在且非空；
3. `financeRAG/rag/.env` 是否配置 embedding；
4. query 是否包含目标公司名称或 ticker，例如 `AAPL`、`Apple`；
5. `ANNUAL_REPORT_RAG_COLLECTION` 是否为 `annual_report_rag`。

可以先跑：

```powershell
python RAG/scripts/query_pack.py "AAPL 2024 annual report revenue gross margin" --top-k 5
```

### 9.2 网页搜索有结果，但数据分析只用了 RAG

这通常说明网页结果没有通过相关性筛选，常见原因是搜索结果不是财务网页，或者网页正文中没有收入、毛利率、风险因素等财务信号。

建议使用更明确的英文 query：

```powershell
python xunlong.py analyze "AAPL 2024 Form 10-K net sales gross margin risk factors financial analysis" --depth deep -m 8 -o html -v
```

### 9.3 出现 mock RAG 证据

确认 `.env` 中：

```env
DATA_ANALYSIS_RAG_MOCK=false
```

只有显式设置 `DATA_ANALYSIS_RAG_MOCK=true` 时，系统才会读取 `fixtures/mock_rag.json`。

### 9.4 前端数据分析按钮不可用

当前静态前端中的数据分析模块请求 `/api/v1/tasks/analysis`，但后端任务接口暂未实现该路由。完整链路建议先使用命令行 `python xunlong.py analyze ...`。

`/api/v1/data_analysis/charts` 只会消费传入的 `search_results` 并查询 RAG，本身不会自动发起网页搜索。