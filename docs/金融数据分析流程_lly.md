# 金融数据分析智能体 — 设计、分工与代码改动汇总

> 本文档汇总数据分析智能体从方案讨论到骨架落地的全部内容，供团队分工、联调与答辩参考。  
> 架构图见 [`项目UML图.md`](../add_AnalysisAgent.md)。

---

## 1. 背景与目标

在 XunLong 多智能体系统中，新增 **金融垂直领域的数据分析智能体**，与现有搜索、生成、审核、迭代智能体协作。

### 1.1 核心分工原则

| 智能体 | 职责 |
|--------|------|
| **搜索智能体** | 金融资讯/政策/行情网页搜索，输出 `search_results` |
| **RAG 知识库（独立小组）** | 研报/指标口径/术语/监管规则向量检索，输出 `rag_refs` |
| **数据分析智能体** | **综合分析网页搜索输出 + RAG 输出**，抽取指标、生成结构化结论与图表 spec |
| **生成智能体** | 基于 `data_analysis_results` 撰写金融数据报告，统一文风与结构 |
| **审核智能体** | 指标口径、数据与图表一致性、搜索与 RAG 依据交叉验证 |

**关键决策**：

- 数据分析智能体 **不负责写完整报告**；结构化分析交给数据分析智能体，文字撰写交给生成智能体。
- 数据分析智能体的 **输入是 `search_results` + RAG 检索结果**，不是用户上传的 CSV/Excel（CSV 可作为后续扩展，非主路径）。
- **数字与结论须能追溯到搜索来源或 RAG 口径**，LLM 不得凭空编造。

### 1.2 模式特征（最终方案）

- 用户选择 **金融数据分析模式**（`financial_analysis`）
- 工作流顺序：**先网页搜索 → 再 RAG 检索 → 再数据分析**（数据分析依赖搜索产出）
- 生成智能体主要接收：
  - `data_analysis_results` → 数据分析章节（已融合搜索内容与 RAG 口径）
  - `search_results` → 可选，用于引用来源链接 / 附录

### 1.3 与现有模块的区别

| 现有模块 | 实际职责 | 与数据分析智能体的关系 |
|---------|---------|----------------------|
| `search_analyzer` + `analysis_results` | 对网页结果做 **轻量** 洞察/主题归纳 | 可保留；**深度金融分析**由 `data_analyzer` 完成 |
| `DataVisualizer`（在 `ReportCoordinator` 内） | 从报告 **文字** 反推图表 | 有 `data_analysis_results.charts` 时跳过 |
| **新增** `DataAnalysisAgent` + `data_analysis_results` | 综合 **search_results + RAG** 做结构化金融分析 | 本次核心新增能力 |

---

## 2. 架构图（摘要）

完整 Mermaid 图见 [`add_AnalysisAgent.md`](../add_AnalysisAgent.md)（**需按本章新方案更新时序：搜索 → RAG → 分析**）。

### 2.1 数据流（文字版）

```
用户 query
        ↓
协调器识别 financial_analysis
        ↓
搜索智能体 → search_results（网页正文/摘要）
        ↓
RAG 知识库 → rag_refs（指标口径/术语/规则）
        ↓
金融数据分析智能体（输入 = search_results + rag_refs）
        → 抽取 metrics / tables
        → 生成 charts / key_findings
        → data_analysis_results
        ↓
生成智能体（ReportCoordinator）
        ↓
审核 → HTML → 存储
```

---

## 3. 输出契约（schemas）

### 3.1 什么是「统一结构」

智能体之间传递的数据必须有 **固定字段、固定含义**，相当于 API 响应格式。  
用 `schemas.py` 中的 Pydantic 模型写进代码，便于生产、消费与校验。

### 3.2 字段命名约定

- **`analysis_results`**：保留给 `search_analyzer`（网页搜索轻量分析）
- **`data_analysis_results`**：新增，专用于金融数据分析智能体输出（**基于 search_results + RAG**）
- **`search_results`**：搜索智能体产出，作为数据分析智能体的 **主要输入**

### 3.3 数据结构

**成员 1 产出（`ExtractedStats` / 原 `ProcessedStats`）— 从搜索内容中抽取：**

```json
{
  "metrics": {"revenue_yoy": 0.23, "gross_margin": 0.41},
  "tables": [{"title": "分季度营收", "columns": [...], "rows": [...]}],
  "data_summary": "基于 5 条搜索结果与 RAG 口径归纳",
  "source_urls": ["https://...", "https://..."]
}
```

**最终输出（`DataAnalysisResult`）— 写入 state：**

```json
{
  "status": "success",
  "source_type": "web_rag",
  "metrics": {},
  "tables": [],
  "charts": [{"type": "bar", "title": "...", "spec": {}}],
  "key_findings": [{"title": "...", "value": "...", "evidence": "..."}],
  "methodology": "分析所依据的搜索来源与 RAG 口径说明",
  "rag_refs": [{"content": "...", "source": "...", "score": 0.95}],
  "search_refs": [{"title": "...", "url": "...", "snippet": "..."}]
}
```

定义文件：`src/agents/data_analysis/schemas.py`（**待增 `search_refs` 字段**）

---

## 4. 接口说明

本节描述 **金融数据分析模式** 下，智能体之间经协调器 `DeepSearchState` 传递的数据形状。  
智能体不直接互调，而是：**读 state 某些字段 → 返回 envelope → 协调器写回 state**。

### 4.1 统一外壳（Agent 返回值）

几乎所有智能体 `process()` 返回同一层包装：

```python
{
    "status": "success",      # 或 "error" / "warning"
    "agent": "智能体名称",
    "result": { ... },        # 各智能体自己的 payload
    "error": "..."            # 仅失败时
}
```

协调器写入 state 时，**通常只存内层 `result`**：

```python
state["task_analysis"] = result.get("result", {})
state["analysis_results"] = result.get("result", {})
state["data_analysis_results"] = result.get("result", {})
state["synthesis_results"] = result.get("result", {})
```

### 4.2 总线：`DeepSearchState` 关键字段

金融模式下，state 中主要字段形状如下：

```python
{
    "query": "分析2024年某行业营收趋势",
    "context": {
        "output_type": "financial_analysis",
        ...
    },

    # 任务分解
    "task_analysis": { ... },

    # 搜索链（数据分析的上游输入）
    "search_results": [ ... ],          # 见 §4.5 → 传入数据分析智能体
    "analysis_results": { ... },        # 见 §4.6（轻量搜索分析，可选）

    # 数据分析链（新增）
    "data_analysis_results": { ... },   # 见 §4.4
    "data_analysis_status": "success",

    # 综合与报告
    "synthesis_results": { ... },
    "final_report": { "result": {...}, "status": "success" },
}
```

> **变更说明**：不再以 `data_sources`（CSV/Excel）作为主输入；数据分析智能体消费 `search_results`。

### 4.3 协调器 → 任务分解智能体

**传入：**

```python
{
    "query": "...",
    "context": { "output_type": "financial_analysis", ... }
}
```

**写入 `state["task_analysis"]`：**

```python
{
    "subtasks": [
        {
            "id": "s1",
            "type": "search",
            "title": "搜索行业营收与政策动态",
            "search_queries": ["..."],
            "depth_level": "deep",
            "time_context": { ... }
        }
    ],
    "strategy": "...",
    "report_type": "comprehensive"
}
```

### 4.4 协调器 → 金融数据分析智能体

**触发时机**：在 `search_results` 就绪 **之后**（不再与搜索并行）。

**传入：**

```python
{
    "query": "...",
    "search_results": [ {...}, {...} ],   # §4.5，主要分析对象
    "task_analysis": { ... },
    # RAG 在 Agent 内部通过 rag_client.retrieve(query) 获取
}
```

**写入 `state["data_analysis_results"]`（即 `DataAnalysisResult`）：**

```python
{
    "status": "success",
    "source_type": "web_rag",
    "metrics": {
        "revenue_yoy": 0.23,
        "gross_margin": 0.41
    },
    "tables": [
        {
            "title": "分季度营收（万元）",
            "columns": ["季度", "营收", "同比"],
            "rows": [["2024Q1", 12000, "18%"], ...]
        }
    ],
    "charts": [
        {
            "type": "bar",
            "title": "分季度营收（万元）",
            "spec": { /* ECharts option */ }
        }
    ],
    "key_findings": [
        {
            "title": "营收同比增长",
            "value": "23%",
            "evidence": "据搜索结果 [1] 与 RAG 毛利率口径综合判断"
        }
    ],
    "methodology": "综合 Top-5 搜索结果与金融 RAG 指标口径",
    "rag_refs": [
        {
            "content": "毛利率 = (营业收入 - 营业成本) / 营业收入...",
            "source": "金融指标口径.md",
            "score": 0.95
        }
    ],
    "search_refs": [
        {
            "title": "2024年银行业财报解读",
            "url": "https://...",
            "snippet": "..."
        }
    ],
    "message": null
}
```

**Agent 内部链路（不写入 state）：**

```
search_results ──┐
                 ├──→ extract_from_search()（成员 1）→ metrics, tables
rag_refs ────────┘
                 ↓
         build_charts()（成员 2）→ charts[]
                 ↓
         LLM _interpret()（成员 2，结合 metrics + rag_refs + search_refs）
                 ↓
         DataAnalysisResult
```

### 4.5 协调器 → 搜索智能体 → `search_results`

**每条 `search_results[i]` 大致为：**

```python
{
    "url": "https://...",
    "title": "文章标题",
    "snippet": "摘要...",
    "content": "正文...",
    "content_length": 5000,
    "search_query": "原始查询",
    "subtask_id": "s1",
    "source": "web",
    "rank": 1,
    "has_full_content": true
}
```

> 此列表是数据分析智能体的 **核心输入**，智能体从中抽取数字、事实与表格。

### 4.6 协调器 → 搜索分析智能体 → `analysis_results`（可选轻量层）

> 轻量归纳，**不是** `data_analysis_results` 的替代品。

**写入 `state["analysis_results"]`：**

```python
{
    "analysis_summary": "对搜索内容的总体评价...",
    "key_insights": ["洞察1", "洞察2"],
    "content_themes": ["主题A", "主题B"],
    "recommendations": ["建议1"]
}
```

数据分析智能体 **可不依赖** 此字段，直接读原始 `search_results`。

### 4.7 协调器 → 内容综合智能体

**传入：**

```python
{
    "query": "...",
    "search_results": [ {...}, {...} ],
    "analysis_results": { ... },
    "data_analysis_results": { ... },   # 已含搜索+RAG 综合分析结果
}
```

**写入 `state["synthesis_results"]`：**

```python
{
    "executive_summary": "执行摘要...",
    "main_findings": ["发现1", "发现2"],
    "report_content": "## 执行摘要\n...\n## 数据分析\n...",
    "sources": ["url1", "url2"],
    "analysis_quality": "good"
}
```

> ⚠️ **现状**：`data_analysis_results` 已传入，但 `content_synthesizer` **尚未读取该字段**。

### 4.8 协调器 → 报告协调器（生成智能体）

**传入：**

```python
generate_report(
    query="...",
    search_results=[ ... ],              # 可选：引用来源
    synthesis_results={ ... },
    data_analysis_results={ ... },       # 主输入：数据分析章节
)
```

### 4.9 全流程传递关系

```mermaid
flowchart TB
    Q["用户 query"]
    Search["🔍 搜索智能体"]
    SR["search_results[]"]
    RAG["📚 RAG retrieve(query)"]
    RAGR["rag_refs[]"]
    DA["📊 数据分析智能体"]
    DAR["data_analysis_results"]
    Gen["📝 生成智能体"]
    FR["final_report"]

    Q --> Search
    Search --> SR
    Q --> RAG
    RAG --> RAGR
    SR --> DA
    RAGR --> DA
    DA --> DAR
    DAR --> Gen
    SR -.可选引用.-> Gen
    Gen --> FR
```

### 4.10 两套「分析」字段对照（勿混淆）

| state 字段 | 来源智能体 | 分析对象 | 形状关键词 |
|-----------|-----------|---------|-----------|
| `analysis_results` | `search_analyzer` | 网页文章（轻量） | `analysis_summary`, `key_insights`, `content_themes` |
| `data_analysis_results` | `data_analyzer` | **search_results + RAG** | `metrics`, `tables`, `charts`, `key_findings`, `rag_refs`, `search_refs` |

### 4.11 接口来源说明

| 类型 | 说明 |
|------|------|
| 协调器调用方式 | 沿用原项目 `process_query` + state 总线 |
| `data_analysis_results` 及 schemas | **本次新建**的自定义契约 |
| `search_results` | 原项目已有；现同时作为 **数据分析智能体输入** |
| 下游消费缺口 | `data_analysis_results` 已进 state 并持久化，synthesizer / report **尚未真正消费** |

---

## 5. 团队分工

### 5.1 三组并行

| 小组 | 人数 | 职责 |
|------|------|------|
| **RAG 组** | 2 人 | 金融知识库、向量检索、`retrieve(query) -> List[RAGChunk]` API |
| **数据分析组** | 2 人 | 见下表 |
| **（其余）** | — | 协调器调度顺序、生成智能体消费、CLI 等 |

### 5.2 数据分析组两人分工（推荐）

| | 成员 1：搜索内容抽取 | 成员 2：综合分析 + 输出 |
|--|---------------------|------------------------|
| **负责** | 从 `search_results` 抽取 metrics、tables、来源引用 | RAG 对接、LLM 综合解读、图表 spec、Agent 主流程 |
| **主要文件** | `search_extractor.py`（新建，替代原 `data_engine` 主职责） | `data_analysis_agent.py`、`rag_client.py`、`chart_builder.py` |
| **输入** | `search_results[]` | `search_results` + `rag_refs` + 成员 1 抽取结果 |
| **不做** | LLM 长文撰写、RAG 建库 | 网页爬虫（搜索智能体做） |
| **Day 1 交付** | script：`mock_search.json` → metrics JSON | script：mock → 完整 `data_analysis_results.json` |

**共建**：`schemas.py` + `fixtures/mock_search.json` + `fixtures/mock_rag.json`

### 5.3 RAG 的作用（在本方案中）

| 模块 | 作用 |
|------|------|
| `search_results` | 提供 **事实与数字**（行情、财报报道、政策原文） |
| `rag_refs` | 提供 **口径与定义**（指标怎么算、什么叫合理区间） |
| 数据分析智能体 | 把两者 **综合** 成结构化 `data_analysis_results` |

RAG **不替代搜索**，也不单独完成分析；必须与搜索输出一起进入数据分析智能体。

### 5.4 2 天并行策略：Mock 先行

| Mock 文件 | 模拟内容 | 谁先用 |
|-----------|---------|--------|
| `fixtures/mock_search.json` | 模拟 `search_results` | 成员 1、成员 2 |
| `fixtures/mock_rag.json` | RAG 组检索返回 | 成员 2 |

Day 2：Mock 替换为真实搜索产出 + 真实 RAG API。

---

## 6. 代码改动清单

### 6.1 目标文件结构（按新方案）

```
src/agents/data_analysis/
├── __init__.py
├── schemas.py              # 输出契约；待增 search_refs
├── search_extractor.py     # 成员 1：从 search_results 抽取结构化数据
├── rag_client.py           # RAG 客户端
├── chart_builder.py        # 成员 2：ECharts spec
└── data_analysis_agent.py  # 主智能体：输入 search_results + RAG

fixtures/
├── mock_search.json        # 模拟 search_results（新）
├── mock_rag.json           # RAG 返回样例
└── mock_stats.json         # 过渡期可保留，后续废弃

prompts/agents/data_analyzer/system.yaml
```

### 6.2 需调整的代码（相对当前骨架）

| 文件 | 调整方向 |
|------|----------|
| `coordinator.py` | 数据分析节点改到 **搜索完成之后**；向 `data_analyzer` 传入 `search_results` |
| `data_analysis_agent.py` | `process()` 增加 `search_results` 参数；主路径不再依赖 `data_sources` |
| `data_engine.py` | 重构为 `search_extractor.py`，或改为包装搜索抽取逻辑 |
| `schemas.py` | `source_type` 增加 `web_rag`；增加 `search_refs` 字段 |
| `report_coordinator.py` | 消费 `data_analysis_results` 写数据分析章节（待实现） |

### 6.3 尚未改动（待办）

| 项 | 说明 |
|----|------|
| 协调器触发顺序 | 当前骨架在搜索 **前** 调分析，需改为搜索 **后** |
| `data_analysis_agent` 输入 | 当前传 `data_sources`，需改为传 `search_results` |
| `xunlong.py` CLI | 尚无 `analyze` 子命令 |
| `content_synthesizer` | 已传 `data_analysis_results`，未消费 |
| CSV/Excel 路径 | 降为 P2 可选扩展，非主方案 |

---

## 7. 协调器接入细节

### 7.1 如何启用金融数据分析模式

```python
await coordinator.process_query(
    query="分析2024年银行业营收趋势",
    context={
        "output_type": "financial_analysis",
        "search_depth": "deep",
        "max_results": 20,
        "output_format": "html",
    },
)
```

> 不再需要 `data_sources`；搜索产出自动成为分析输入。

### 7.2 推荐触发顺序（新方案）

```
output_type_detector
    → task_decomposer
    → deep_searcher          # 产出 search_results
    → data_analyzer          # 输入 search_results + RAG
    → search_analyzer        # 可选，轻量分析
    → content_synthesizer
    → report_generator
```

### 7.3 State 关键字段

```python
search_results: List[Dict]             # 数据分析智能体输入（主）
data_analysis_results: Dict[str, Any]  # 数据分析智能体输出
data_analysis_status: str
# data_sources 降为可选扩展，非主路径
```

### 7.4 存储

```
storage/{project_id}/intermediate/
├── 02_search_results.json       # 搜索产出（分析输入）
├── 03_data_analysis.json        # 综合分析结果
└── 04_search_analysis.json      # 轻量 search_analyzer 产出
```

---

## 8. 各模块职责（目标方案）

### 8.1 `search_extractor.py`（成员 1）

- 输入：`search_results[]`
- 输出：`metrics`、`tables`、`search_refs`（来源 URL/标题）
- 手段：规则 + LLM 辅助抽取（数字必须标注来源片段）

### 8.2 `rag_client.py`（RAG 组 / 成员 2）

- 输入：`query`
- 输出：`rag_refs[]`
- 为数据分析提供指标口径与术语上下文

### 8.3 `data_analysis_agent.py`（成员 2）

目标流程：

```
search_results
    → search_extractor()     # 成员 1
rag_client.retrieve(query)   # RAG 组
    → build_charts()
    → LLM _interpret(search + rag)
    → DataAnalysisResult
```

### 8.4 `chart_builder.py`

- 基于抽取出的 `metrics` / `tables` 生成 ECharts spec
- 图表数据须能对应 `search_refs` 中的来源

---

## 9. 命令行与 README 现状

### 9.1 当前能否用 CLI 启动？

**不能。** 需通过 `context["output_type"] = "financial_analysis"` 编程调用。

### 9.2 计划中的 CLI 形态

```bash
python xunlong.py analyze "分析2024年银行业营收趋势" --depth deep -v
```

不再需要 `--data-file`；数据来自搜索与 RAG。

---

## 10. 方案演进记录

| 阶段 | 结论 |
|------|------|
| 初版 | 新增数据分析智能体；分析 + 图表 |
| 分工讨论 | 分析为主、生成交给生成智能体 |
| 垂直领域 | 金融场景 + RAG 知识增强 |
| 数据源 v1 | Excel/CSV + RAG（成员 1 读文件） |
| **数据源 v2（当前）** | **数据分析智能体分析 `search_results` + RAG 输出** |
| 搜索 | 先搜索，再分析（分析依赖搜索产出） |
| 落地 | 骨架已建，需按 v2 调整 coordinator 与 Agent 输入 |

---

## 11. 后续待办（按优先级）

### P0 — 能 demo

- [ ] 协调器：数据分析节点移到搜索 **之后**，传入 `search_results`
- [ ] 成员 1：实现 `search_extractor.py` + `fixtures/mock_search.json`
- [ ] RAG 组：`retrieve()` API 与 `mock_rag.json` 同结构
- [ ] 成员 2：`data_analysis_agent` 改为消费 search + RAG
- [ ] `ReportCoordinator` 消费 `data_analysis_results` 写章节

### P1 — 体验完善

- [ ] `schemas.py` 增加 `search_refs`、`source_type: web_rag`
- [ ] `xunlong.py` 新增 `analyze` 命令
- [ ] `README_CN.md` 使用指南补充
- [ ] 审核：结论 ↔ 搜索来源 ↔ RAG 口径 一致性校验

### P2 — 扩展

- [ ] 用户上传 CSV/Excel 作为 **补充数据源**（与搜索并存）
- [ ] 有结构化 charts 时跳过 `DataVisualizer`

---

## 12. 快速验证（目标调用方式）

```python
import asyncio
from src.agents.data_analysis import DataAnalysisAgent
from src.llm.manager import LLMManager

MOCK_SEARCH = [...]  # fixtures/mock_search.json

async def main():
    agent = DataAnalysisAgent(LLMManager())
    out = await agent.process({
        "query": "分析2024年银行业营收趋势",
        "search_results": MOCK_SEARCH,
    })
    print(out["status"])
    print(out["result"]["key_findings"])
    print(len(out["result"]["rag_refs"]), "rag refs")

asyncio.run(main())
```

---

*文档版本：v2 — 数据分析智能体输入改为网页搜索输出 + RAG 输出。*
