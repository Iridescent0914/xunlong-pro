# `data_analysis_results` 接口形状说明

> **来源智能体**：`data_analyzer`（金融数据分析智能体）  
> **写入位置**：协调器 `state["data_analysis_results"]`  
> **代码模型**：`DataAnalysisResult`（`src/agents/data_analysis/schemas.py`）  
> **持久化路径**：`storage/{project_id}/intermediate/03_data_analysis.json`

---

## 概览

`data_analysis_results` 是金融数据分析智能体写入协调器 state 的完整输出。核心由五块组成：

| 字段 | 一句话 |
|------|--------|
| `metrics` | 算出来的 KPI 数字 |
| `tables` | 算出来的明细表 |
| `charts` | 由数字生成的图（ECharts 配置） |
| `key_findings` | 用自然语言说清的结论（数字必须来自 metrics） |
| `rag_refs` | 解释这些数字时参考的知识库片段 |

---

## 整体结构

```json
{
  "status": "success",
  "source_type": "mock",
  "methodology": "...",
  "message": null,
  "metrics": { },
  "tables": [ ],
  "charts": [ ],
  "key_findings": [ ],
  "rag_refs": [ ]
}
```

| 区块 | 字段 | 说明 |
|------|------|------|
| 元信息 | `status` | `success` \| `error` \| `skipped` |
| 元信息 | `source_type` | `mock` \| `excel` \| `csv` \| `database` |
| 元信息 | `methodology` | 分析口径 / 数据说明 |
| 元信息 | `message` | 仅 `error` 时有错误信息 |
| 核心数据 | `metrics` ~ `rag_refs` | 见下文各节 |

---

## 1. `metrics` — 核心数值指标

### 是什么

从 Excel / CSV / DB **算出来的标量指标**，结构为「指标名 → 数值」的字典。

### 谁产生

成员 1 的 `data_engine.analyze()`（代码计算，**不让 LLM 编数字**）。

### 示例

```json
{
  "revenue_yoy": 0.23,
  "gross_margin": 0.41,
  "net_profit": 8500,
  "debt_ratio": 0.38
}
```

### 字段说明

| 字段示例 | 含义 | 类型说明 |
|---------|------|---------|
| `revenue_yoy` | 营收同比增长率 | 小数 `0.23` = 23% |
| `gross_margin` | 毛利率 | 小数 |
| `net_profit` | 净利润 | 整数，单位需与 `methodology` 一致 |
| `debt_ratio` | 资产负债率 | 小数 |

### 设计意图

- 给 `key_findings` 和生成智能体提供 **可引用的硬数字**
- 给 `charts` 提供 Y 轴数据（没有合适 table 时）
- 键名建议用英文 `snake_case`；展示名可在 findings 的 `title` 里写中文

> **注意**：`metrics` 是扁平 dict，不嵌套复杂结构；更细的明细放 `tables`。

---

## 2. `tables` — 结构化汇总表

### 是什么

适合放进报告或转成图表的 **二维表**，作为 Markdown / Word 表格的数据源。

### 谁产生

成员 1 的 `data_engine`（pandas 聚合后输出）。

### 示例

```json
[
  {
    "title": "分季度营收（万元）",
    "columns": ["季度", "营收", "同比"],
    "rows": [
      ["2024Q1", 12000, "18%"],
      ["2024Q2", 13500, "23%"],
      ["2024Q3", 14200, "25%"],
      ["2024Q4", 15800, "28%"]
    ]
  }
]
```

### 子字段

| 子字段 | 含义 |
|--------|------|
| `title` | 表标题（报告里显示） |
| `columns` | 列名，与 `rows` 每行元素一一对应 |
| `rows` | 行数据；单元格可以是数字、字符串（如 `"18%"`） |

### 与 `metrics` 的区别

| | `metrics` | `tables` |
|--|-----------|----------|
| 结构 | 单个 KPI | 多行明细 |
| 典型用途 | 「整体同比 23%」 | 「各季度分别是多少」 |
| 示例 | `{"revenue_yoy": 0.23}` | 四季营收逐行列表 |

### 下游用法

生成智能体可渲染为 Markdown 表格；`chart_builder` 会找标题含「分季度」的表生成柱状图。

---

## 3. `charts` — 可视化图表 spec

### 是什么

**不是图片文件**，而是 ECharts 的配置对象 + 元数据，供 HTML 报告渲染图表。

### 谁产生

成员 2 的 `chart_builder.build_charts()`，基于 `metrics` / `tables` 生成。

### 示例

```json
[
  {
    "type": "bar",
    "title": "分季度营收（万元）",
    "spec": {
      "title": { "text": "分季度营收（万元）", "left": "center" },
      "xAxis": { "type": "category", "data": ["2024Q1", "2024Q2", "2024Q3", "2024Q4"] },
      "yAxis": { "type": "value", "name": "营收（万元）" },
      "series": [{ "type": "bar", "data": [12000, 13500, 14200, 15800] }]
    }
  }
]
```

### 子字段

| 子字段 | 含义 |
|--------|------|
| `type` | 图表类型：`bar` / `line` / `pie` |
| `title` | 图表标题 |
| `spec` | 完整 ECharts `option` 对象（由 `EChartsGenerator` 生成） |

### 设计意图

- 数字来自 `tables` / `metrics`，与 `key_findings` 共用同一数据源，避免 LLM 瞎画
- 生成智能体在报告里嵌入图表并写图下说明，不必自己再算一遍

### 与 `DataVisualizer` 的区别

| | 本字段 `charts` | 项目内 `DataVisualizer` |
|--|----------------|------------------------|
| 数据来源 | 真实 Excel/DB 统计 | 已写好的报告文字 |
| 生成方向 | 数据 → 图 | 文字 → 反推图 |

---

## 4. `key_findings` — 业务解读结论

### 是什么

面向读者的 **自然语言结论**，每条对应一个可理解的发现。

### 谁产生

成员 2 的 LLM + RAG（`_interpret()`）；LLM 失败时用 `metrics` 生成占位条目。

### 示例

```json
[
  {
    "title": "营收同比增长",
    "value": "23%",
    "evidence": "基于 metrics.revenue_yoy=0.23，且高于行业平均..."
  },
  {
    "title": "gross_margin",
    "value": "0.41",
    "evidence": "来自数据引擎计算结果（骨架占位）"
  }
]
```

### 子字段

| 子字段 | 含义 | 约束 |
|--------|------|------|
| `title` | 结论主题 | 如「营收同比增长」「毛利率」 |
| `value` | 结论值（字符串） | 如 `"23%"`、`"41%"`；须能对应 `metrics` |
| `evidence` | 依据说明 | 引用 metrics、表格或 RAG 口径 |

### 与 `analysis_results.key_insights` 的区别

| | `data_analysis_results.key_findings` | `analysis_results.key_insights` |
|--|--------------------------------------|--------------------------------|
| 来源 | Excel/DB 真实计算 | 网页文章摘要 |
| 结构 | `{title, value, evidence}` | 通常是字符串列表 |
| 数字要求 | **必须**有 metrics 支撑 | 无硬性数值约束 |

### 设计意图

生成智能体写「数据分析章节」时，以 `key_findings` 为段落骨架，扩写为连贯文字，**但不改写 `value` 里的数字**。

---

## 5. `rag_refs` — RAG 检索引用

### 是什么

分析时从 **金融知识库** 检索到的片段，用于指标口径、术语解释、行业基准。

### 谁产生

RAG 组的 `retrieve(query)`，经 `rag_client` 调用；骨架阶段读 `fixtures/mock_rag.json`。

### 示例

```json
[
  {
    "content": "毛利率 = (营业收入 - 营业成本) / 营业收入，反映核心盈利能力。",
    "source": "金融指标口径.md",
    "score": 0.95
  },
  {
    "content": "同比（YoY）= (本期值 - 去年同期值) / 去年同期值。",
    "source": "术语词典.md",
    "score": 0.88
  }
]
```

### 子字段

| 子字段 | 含义 |
|--------|------|
| `content` | 检索到的知识片段正文 |
| `source` | 出处（文件名、文档 ID 等） |
| `score` | 相似度 / 相关性分数，0~1 |

### 用途

1. **分析阶段**：注入 LLM prompt，帮助正确解读 `metrics`
2. **报告阶段**（待实现）：生成智能体可在脚注 / 附录引用 `source`
3. **审计 / 答辩**：说明结论有口径依据，不是凭空生成

> **注意**：`rag_refs` 是引用记录，不是分析结论本身；结论在 `key_findings`。

---

## 6. 其他顶层字段

| 字段 | 含义 | 示例 |
|------|------|------|
| `status` | 本次分析是否成功 | `"success"` / `"error"` / `"skipped"` |
| `source_type` | 数据来源类型 | `"mock"`、`"excel"`、`"csv"`、`"database"` |
| `methodology` | 分析口径、样本说明 | `"共 4 个季度，按季度聚合，剔除空值"` |
| `message` | 错误信息 | 仅 `status=error` 时有值 |

---

## 7. 内部组装流程

```
Excel / CSV / DB
    ↓  data_engine（成员 1）
metrics + tables
    ↓  rag_client.retrieve（RAG 组）
rag_refs
    ↓  chart_builder（成员 2）
charts
    ↓  LLM _interpret（成员 2，结合 metrics + rag_refs）
key_findings
    ↓  组装 DataAnalysisResult
data_analysis_results
    →  state
    →  03_data_analysis.json
    →  synthesizer / report（待消费）
```

---

## 8. 完整 Mock 示例

```json
{
  "status": "success",
  "source_type": "mock",
  "metrics": {
    "revenue_yoy": 0.23,
    "gross_margin": 0.41,
    "net_profit": 8500,
    "debt_ratio": 0.38
  },
  "tables": [
    {
      "title": "分季度营收（万元）",
      "columns": ["季度", "营收", "同比"],
      "rows": [
        ["2024Q1", 12000, "18%"],
        ["2024Q2", 13500, "23%"],
        ["2024Q3", 14200, "25%"],
        ["2024Q4", 15800, "28%"]
      ]
    }
  ],
  "charts": [
    {
      "type": "bar",
      "title": "分季度营收（万元）",
      "spec": { "...": "ECharts option" }
    }
  ],
  "key_findings": [
    {
      "title": "revenue_yoy",
      "value": "0.23",
      "evidence": "来自数据引擎计算结果（骨架占位）"
    }
  ],
  "methodology": "共 4 个季度，2024 年营收逐季增长，mock 样例数据",
  "rag_refs": [
    {
      "content": "毛利率 = (营业收入 - 营业成本) / 营业收入...",
      "source": "金融指标口径.md",
      "score": 0.95
    }
  ],
  "message": null
}
```

---

## 相关文档

- [`docs/FINANCIAL_DATA_ANALYSIS.md`](docs/FINANCIAL_DATA_ANALYSIS.md) — 完整设计与接口说明
- [`src/agents/data_analysis/schemas.py`](src/agents/data_analysis/schemas.py) — Pydantic 模型定义
- [`fixtures/mock_stats.json`](fixtures/mock_stats.json) / [`fixtures/mock_rag.json`](fixtures/mock_rag.json) — Mock 样例
