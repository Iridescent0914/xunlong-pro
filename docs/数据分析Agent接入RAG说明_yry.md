# 数据分析 Agent 接入 RAG 说明

本文档按当前代码实现说明金融数据分析智能体如何同时使用网页搜索结果、公司财报 PDF RAG 和 Yahoo Finance 数据集 RAG。相关核心代码位于：

```text
src/agents/coordinator.py
src/agents/data_analysis/data_analysis_agent.py
src/agents/data_analysis/rag_client.py
src/agents/data_analysis/llm_search_analyzer.py
src/agents/data_analysis/evidence_adapter.py
src/agents/data_analysis/report_section.py
src/agents/data_analysis/data_analysis_context.py
src/agents/data_analysis/ppt_section.py
```

## 1. 总体链路

当前金融分析主链路是：

```text
用户 query
  -> xunlong.py analyze
  -> DeepSearchCoordinator 进入 financial_analysis 模式
  -> DeepSearcher 获取网页搜索结果 search_results
  -> DataAnalysisAgent.process()
       -> RAGClient.retrieve_pack(query)
       -> 合并/标准化 RAG evidence pack
       -> LLMSearchAnalyzer 把 web + RAG 证据交给 LLM 抽表
       -> DataAnalysisAgent 后处理金额单位和指标口径
       -> chart_builder 生成 ECharts 图表
  -> data_analysis_results
  -> ReportCoordinator / PPTCoordinator 消费结构化结果
  -> storage/{project_id}/intermediate/03_data_analysis.json
  -> FINAL_REPORT.md/html 或 PPT_DATA.json/html
```

RAG 在这里不是替代网页搜索，而是补充证据：

```text
网页搜索：最新资讯、公开网页、补充背景
公司财报 PDF RAG：年报、Form 10-K、管理层讨论、风险因素、财务报表片段
Yahoo Finance 数据集 RAG：stock_news、stock_earning_call 等动态材料
```

## 2. 两个 RAG 库

| RAG 源 | 目录 | 开关 | Collection | 典型内容 |
| --- | --- | --- | --- | --- |
| 公司财报 PDF RAG | `RAG/` | `ANNUAL_REPORT_RAG_ENABLED` | `annual_report_rag` | 年报 PDF、Form 10-K、风险因素、管理层讨论 |
| Yahoo Finance 数据集 RAG | `financeRAG/` | `YAHOO_FINANCE_RAG_ENABLED` | `finance_rag` | 新闻、earning call、市场动态 |

当前项目根目录 `.env` 中的实际配置是：

```env
DATA_ANALYSIS_RAG_MOCK=false
ANNUAL_REPORT_RAG_ENABLED=true
ANNUAL_REPORT_RAG_PERSIST_DIR=RAG/data/chroma_db
ANNUAL_REPORT_RAG_COLLECTION=annual_report_rag
ANNUAL_REPORT_RAG_ENV_FILE=financeRAG/rag/.env
YAHOO_FINANCE_RAG_ENABLED=false
YAHOO_FINANCE_RAG_PERSIST_DIR=financeRAG/rag/chroma_db
YAHOO_FINANCE_RAG_COLLECTION=finance_rag
YAHOO_FINANCE_RAG_ENV_FILE=financeRAG/rag/.env
FINANCIAL_RAG_SYMBOL_ALIASES_FILE=financeRAG/rag/company_aliases.json
```

因此当前主流程默认只查公司财报 PDF RAG，不查 Yahoo RAG。

## 3. RAGClient 的统一检索行为

入口：`src/agents/data_analysis/rag_client.py`

`DataAnalysisAgent` 调用：

```python
RAGClient(use_mock=use_mock).retrieve_pack(query, top_k=_rag_top_k())
```

`RAGClient.retrieve_pack()` 的行为：

```text
如果 ANNUAL_REPORT_RAG_ENABLED=true
  -> _query_local_annual_report_pack()
  -> 调用 RAG/src/rag_reports/indexer.py 的 query_evidence_pack()

如果 YAHOO_FINANCE_RAG_ENABLED=true
  -> _query_yahoo_finance_pack()
  -> 直接查询 financeRAG/rag/chroma_db
  -> 将 Chroma 返回结果包装成 evidence pack

如果两个都启用
  -> _merge_packs()
  -> source=multi_financial_rag

如果两个都关闭且 DATA_ANALYSIS_RAG_MOCK=false
  -> 返回 source=disabled 的空 RAGEvidencePack

如果 DATA_ANALYSIS_RAG_MOCK=true
  -> 使用 fixtures/mock_rag.json
```

合并时会：

```text
1. 汇总 evidence 列表
2. 按 score 降序排序
3. 合并 doc_types / key_points / risk_factors / data_gaps / warnings
4. 计算 hit_count / avg_score / confidence
```

## 4. 公司名和 ticker 识别

`RAGClient` 会用 `_infer_query_symbol()` 从 query 中识别股票代码。支持：

```text
$AAPL
ticker=AAPL
symbol=AAPL
NASDAQ:AAPL
Apple / Apple Inc. / 苹果 / Agilent / 安捷伦 等别名
```

别名文件：

```text
financeRAG/rag/company_aliases.json
```

作用：

```text
Yahoo RAG：识别到 symbol 后加 Chroma where={"symbol": "AAPL"} 过滤
年报 RAG：识别到 symbol 后检查 RAG/config/targets.json 是否覆盖该公司；未覆盖则跳过年报库
```

## 5. Evidence Pack 和 RAGReference

统一 evidence pack 结构由 `src/agents/data_analysis/schemas.py` 定义，核心是：

```text
RAGEvidencePack
  source
  query
  normalized_query
  entities
  retrieval_scope
  evidence: List[EvidenceItem]
  rag_summary
  quality
```

`EvidenceItem` 保留完整证据信息：

```text
evidence_id / doc_type / title / date / source / url / content / summary / score / metadata
```

`evidence_adapter.rag_pack_to_refs()` 会把 evidence 转成下游使用的 `rag_refs`。当前 `RAGReference` 已保留：

```text
content
source
score
title
url
date
doc_type
ticker
evidence_id
page_start
page_end
metadata
```

这样最终报告中的 RAG 来源可以展示标题、链接、日期、ticker 和页码，而不是只显示 source。

## 6. LLMSearchAnalyzer 如何使用 RAG

入口：`src/agents/data_analysis/llm_search_analyzer.py`

`extract_table_from_search()` 接收：

```python
extract_table_from_search(
    query,
    search_results,
    llm_callback,
    rag_evidence=rag_pack.evidence,
)
```

它把来源格式化为两组：

```text
网页搜索：W1, W2, W3 ...
RAG 证据：R1, R2, R3 ...
```

LLM prompt 要求：

```text
- 只抽取有来源依据的数值
- 每行必须在“来源”列标注 [W1] / [W2] 或 [R1] / [R2]
- 不使用无前缀 [1]
- 保留单位和期间
- 冲突数字分多行列出
- 不把 profit margin / operating margin 误写成 gross margin
- 英文金额 B / bn / billion 要按“亿美元”口径正确换算
```

输出 JSON 结构：

```json
{
  "table": {
    "title": "表标题",
    "columns": ["指标", "数值", "期间", "来源", "原文依据"],
    "rows": [
      ["2024年营业收入", "8621亿元", "2024", "[W1]", "销售收入8,621亿"]
    ]
  },
  "conclusion": "基于表格的中文结论",
  "methodology": "抽取口径说明"
}
```

## 7. DataAnalysisAgent 后处理

`src/agents/data_analysis/data_analysis_agent.py` 在 LLM 抽表后会做轻量后处理：

### 金额单位

识别：

```text
$391.0B
391.0 billion
391.0 bn
```

转换为：

```text
$391.0B（约3910亿美元）
```

同时修正结论中类似 `391.0 亿美元` 这种少乘 10 的表达。

### margin 口径

防止 LLM 把不同 margin 混写为毛利率：

```text
gross margin      毛利率
profit margin     利润率/净利率，非毛利率
operating margin  营业利润率，非毛利率
```

如果表格中出现 `Profit margin` 但中文写成“毛利率”，会修正为：

```text
利润率（profit margin，非毛利率）
```

## 8. 报告和 PPT 接入

### 报告

`ReportCoordinator` 会把 `data_analysis_results` 注入：

```text
src/agents/report/report_coordinator.py
src/agents/data_analysis/report_section.py
```

最终生成独立章节：

```text
金融数据分析
  -> 分析结果：表格 + 结论
  -> 分析图表：ECharts
  -> 分析来源：W/R 引用来源
```

`report_section.py` 会从表格“来源”列解析 `[W3]`、`[R1]`，再回到 `search_refs` / `rag_refs` 找标题、URL、日期和页码。

如果 LLM 漏写来源编号，但 refs 存在，会兜底展示前几条来源，避免报告中出现误导性的“暂无引用来源”。

### PPT

`PPTCoordinator` 会通过：

```text
src/agents/data_analysis/ppt_section.py
```

在 PPT 中插入分析结果、图表和来源页。

## 9. 输出文件

运行：

```powershell
python xunlong.py analyze "分析 Apple 2024 年报中的收入、毛利率和风险因素" -o html -v
```

重点查看：

```text
storage/{project_id}/intermediate/02_search_results.json
storage/{project_id}/intermediate/03_data_analysis.json
storage/{project_id}/intermediate/04_search_analysis.json
storage/{project_id}/reports/FINAL_REPORT.md
storage/{project_id}/reports/FINAL_REPORT.html
```

其中 `03_data_analysis.json` 是 RAG 和网页搜索共同参与后的结构化分析结果。

## 10. 验证命令

语法检查：

```powershell
python -m py_compile src/agents/data_analysis/data_analysis_agent.py src/agents/data_analysis/llm_search_analyzer.py src/agents/data_analysis/rag_client.py src/agents/data_analysis/evidence_adapter.py src/agents/data_analysis/report_section.py src/agents/data_analysis/data_analysis_context.py RAG/src/rag_reports/pipeline.py
```

只测试年报 RAG：

```powershell
python RAG/scripts/query_pack.py "AAPL 2024 annual report revenue gross margin risk factors" --top-k 5
```

测试主链路：

```powershell
python xunlong.py analyze "分析 Apple 2024 年报中的收入、毛利率和风险因素，并结合网页资料" --depth deep -m 8 -o html -v
```

## 11. 当前限制

- RAG 证据进入 LLM prompt 后，最终是否被采用取决于证据相关性和 LLM 抽表结果。
- Yahoo RAG 当前只覆盖抽取的数据集子集，不代表完整 Yahoo Finance 数据。
- 年报 PDF 抽取可能受表格、页眉页脚、双栏排版影响。
- `FINANCIAL_RAG_API_URL` 目前是预留配置，真实 HTTP RAG API 尚未实现。
