### 架构组件图

```mermaid
graph TB
    subgraph "用户接口层"
        CLI[CLI命令行工具]
    end

    subgraph "智能体编排层"
        Coordinator[🎯 协调器 Coordinator<br/>任务分解与流程编排]
    end

    subgraph "知识增强层"
        RAG[📚 金融 RAG 知识库<br/>年报向量库 · RAGClient · evidence_adapter]
    end

    subgraph "核心智能体层"
        direction LR
        SearchAgent[🔍 搜索智能体<br/>网络搜索 & 内容提取]
        AnalysisAgent[📊 金融数据分析智能体<br/>RAG+网页 · LLM分析 · 图表]
        ReportAgent[📄 报告生成器<br/>Business / Academic / Technical]
        PPTAgent[📊 PPT 生成器<br/>Business / Creative / Minimal]
    end

    subgraph "支持服务层"
        HTMLConverter[📄 HTML 转换器<br/>Markdown → HTML]
        ExportManager[📁 导出管理器<br/>PDF / DOCX / PPTX]
        StorageManager[💾 存储管理器<br/>项目文件管理]
    end

    subgraph "LLM 服务层"
        LLMManager[🤖 LLM 管理器<br/>OpenAI / Anthropic / DeepSeek / Qwen]
        Observability[📈 可观测性<br/>LangFuse 监控]
    end

    CLI --> Coordinator
    Coordinator --> SearchAgent
    Coordinator --> AnalysisAgent
    Coordinator --> ReportAgent
    Coordinator --> PPTAgent

    ReportAgent --> HTMLConverter
    PPTAgent --> HTMLConverter
    HTMLConverter --> ExportManager
    ExportManager --> StorageManager

    Coordinator -.-> RAG

    SearchAgent -.调用.-> LLMManager
    AnalysisAgent -.调用.-> LLMManager
    ReportAgent -.调用.-> LLMManager
    PPTAgent -.调用.-> LLMManager
    LLMManager -.监控.-> Observability

    style Coordinator fill:#ff6b6b,stroke:#c92a2a,color:#fff
    style LLMManager fill:#4c6ef5,stroke:#364fc7,color:#fff
    style Observability fill:#ae3ec9,stroke:#862e9c,color:#fff
```


### 核心智能体（金融数据分析模式）

> **模式说明**：用户通过 `xunlong analyze` 进入金融数据分析模式。协调器**先完成网页搜索**，再调用金融数据分析智能体；智能体内部检索 **RAG 年报证据**，与 `search_results` 一并交给 **LLM 抽取数值表**，生成结构化 `data_analysis_results`，最后按 `--deliverable` 产出报告 / PPT / 仅分析 JSON。

```mermaid
graph TD
    subgraph "协调层"
        Coordinator["🎯 协调器 Coordinator<br/>━━━━━━━━━━━<br/>• 识别分析模式<br/>• 任务分解与流程编排<br/>• 搜索 → 分析 → 报告/PPT"]
    end

    subgraph "知识增强层"
        RAG["📚 金融 RAG 知识库<br/>━━━━━━━━━━━<br/>• 年报向量库 <br/>• 指标口径与原文片段"]
    end

    subgraph "执行层"
        SearchAgent["🔍 搜索智能体<br/>━━━━━━━━━━━<br/>• 金融资讯与政策搜索<br/>• 正文提取与质量评估<br/>• 输出 search_results"]

        AnalysisAgent["📊 金融数据分析智能体<br/>DataAnalysisAgent<br/>━━━━━━━━━━━<br/>• RAG + 网页证据 → 抽表<br/>• chart_builder 生成图表<br/>• 输出 data_analysis_results"]

        GenerationAgent["📝 生成智能体<br/>ReportCoordinator / PPTCoordinator<br/>━━━━━━━━━━━<br/>• 正文章节 LLM 撰写<br/>• 插入分析模块<br/>• 多页 HTML PPT 或 FINAL_REPORT"]

        ReviewAgent["✅ 审核智能体<br/>━━━━━━━━━━━<br/>• 质量检查<br/>• 内容优化<br/>• 一致性验证"]
    end

    Coordinator --> SearchAgent
    SearchAgent --> AnalysisAgent
    Coordinator --> AnalysisAgent
    Coordinator --> GenerationAgent
    Coordinator --> ReviewAgent

    RAG -.retrieve_pack.-> AnalysisAgent
    SearchAgent -.search_results.-> AnalysisAgent

    AnalysisAgent -.data_analysis_results.-> GenerationAgent
    SearchAgent -.search_results.-> GenerationAgent

    GenerationAgent -.提交审核.-> ReviewAgent
    ReviewAgent -.反馈修改.-> GenerationAgent

    style Coordinator fill:#ff6b6b,stroke:#c92a2a,color:#fff
    style RAG fill:#228be6,stroke:#1864ab,color:#fff
    style SearchAgent fill:#4c6ef5,stroke:#364fc7,color:#fff
    style AnalysisAgent fill:#12b886,stroke:#099268,color:#fff
    style GenerationAgent fill:#51cf66,stroke:#2b8a3e,color:#fff
    style ReviewAgent fill:#ffd43b,stroke:#f59f00,color:#333
```

### 多智能体协作流程

采用基于LangGraph的状态机工作流：

```mermaid
graph LR
    A[👤 用户输入] --> B[🔍 需求分析]
    B --> C[📋 任务分解]
    C --> D[🌐 并行搜索]
    D --> E[📦 内容整合]
    E --> F[✨ 智能生成]
    F --> G[✅ 质量审核]
    G --> H[🔄 格式转换]
    H --> I[📤 导出输出]

    style A fill:#e3f2fd,stroke:#1976d2
    style B fill:#f3e5f5,stroke:#7b1fa2
    style C fill:#f3e5f5,stroke:#7b1fa2
    style D fill:#fff3e0,stroke:#f57c00
    style E fill:#fff3e0,stroke:#f57c00
    style F fill:#e8f5e9,stroke:#388e3c
    style G fill:#e8f5e9,stroke:#388e3c
    style H fill:#fce4ec,stroke:#c2185b
    style I fill:#fce4ec,stroke:#c2185b
```

---

### `data_analysis/` 模块内部结构

> 目录路径：`src/agents/data_analysis/`（共 13 个文件）

```mermaid
graph TB
    subgraph "入口与编排"
        DAA["data_analysis_agent.py<br/>DataAnalysisAgent.process()"]
    end

    subgraph "证据获取"
        RC["rag_client.py<br/>RAGClient"]
        EA["evidence_adapter.py<br/>parse_rag_evidence_pack / rag_pack_to_refs"]
        SR["search_relevance.py<br/>（工具模块，按 query 筛搜索）"]
    end

    subgraph "LLM 分析"
        LSA["llm_search_analyzer.py<br/>extract_table_from_search()"]
    end

    subgraph "可视化"
        CB["chart_builder.py<br/>build_chart_for_table()"]
    end

    subgraph "契约与上下文"
        SCH["schemas.py<br/>DataAnalysisResult 等"]
        DAC["data_analysis_context.py<br/>has_usable_analysis / format_*"]
    end

    subgraph "下游渲染"
        RS["report_section.py<br/>build_data_analysis_section()"]
        PS["ppt_section.py<br/>build_data_analysis_slides()"]
    end

    subgraph "文件上传路径（API 独立）"
        FA["file_analyzer.py<br/>FileDataAnalyzer"]
        FR["file_report.py<br/>build_file_analysis_html/md"]
    end

    DAA --> RC
    RC --> EA
    DAA --> LSA
    EA -.RAG evidence.-> LSA
    LSA --> CB
    DAA --> SCH
    SCH --> RS
    SCH --> PS
    DAC -.写作上下文.-> RS
    FA --> FR
    FA --> CB

    style DAA fill:#12b886,stroke:#099268,color:#fff
    style LSA fill:#4dabf7,stroke:#1971c2,color:#fff
    style RS fill:#51cf66,stroke:#2b8a3e,color:#fff
    style PS fill:#20c997,stroke:#0ca678,color:#fff
```

| 文件 | 作用 |
|------|------|
| `data_analysis_agent.py` | 智能体入口：RAG 检索 → LLM 抽表 → 图表 → 组装 `DataAnalysisResult` |
| `llm_search_analyzer.py` | 将网页 + RAG 证据交 LLM，抽取数值表、结论、methodology |
| `rag_client.py` | RAG 检索客户端（Chroma 年报库 / mock / 远程 API） |
| `evidence_adapter.py` | 统一解析 search / RAG evidence pack，转换为引用结构 |
| `search_relevance.py` | 按 query 筛选相关搜索结果（独立工具，可选） |
| `chart_builder.py` | 由数据表生成 ECharts spec |
| `schemas.py` | Pydantic 数据契约（`DataAnalysisResult` 等） |
| `data_analysis_context.py` | 报告写作上下文、章节整合标记 |
| `report_section.py` | 渲染 FINAL_REPORT 独立章节「金融数据分析」 |
| `ppt_section.py` | 渲染 PPT 分析幻灯片（结论页前插入） |
| `file_analyzer.py` | 用户上传 CSV/文本的独立分析路径 |
| `file_report.py` | 文件分析结果的 HTML/Markdown 渲染 |
| `__init__.py` | 模块对外导出 |

---

### 金融数据分析内容生成流程

> **顺序执行**：先搜索 → 再分析（含 RAG）；分析模块与正文分离渲染。`--deliverable` 控制最终产出物。

```mermaid
sequenceDiagram
    autonumber
    participant User as 👤 用户
    participant CLI as 💻 CLI (analyze)
    participant Coord as 🎯 协调器
    participant Search as 🔍 搜索智能体
    participant DAA as 📊 DataAnalysisAgent
    participant RAG as 📚 RAGClient
    participant LLM as 🤖 llm_search_analyzer
    participant Chart as 📈 chart_builder
    participant Gen as 📝 ReportCoordinator
    participant RS as 📋 report_section
    participant PPT as 📽️ PPTCoordinator
    participant PS as 🖼️ ppt_section
    participant HTML as 📄 document_html_agent
    participant Storage as 💾 存储

    User->>CLI: xunlong analyze "query" [--deliverable report|ppt|none]
    CLI->>Coord: context.output_type = financial_analysis

    Coord->>Coord: 任务分解 task_decomposer
    Coord->>Search: deep_searcher 执行搜索
    activate Search
    Search-->>Coord: search_results[]
    deactivate Search

    Coord->>DAA: _data_analyzer_node
    activate DAA

    DAA->>RAG: retrieve_pack(query)
    activate RAG
    RAG-->>DAA: RAGEvidencePack
    deactivate RAG

    DAA->>LLM: extract_table_from_search(query, search_results, rag_evidence)
    activate LLM
    LLM->>LLM: LLM 抽取数值表 + 结论
    LLM-->>DAA: LLMSearchAnalysis
    deactivate LLM

    DAA->>Chart: build_chart_for_table(table)
    Chart-->>DAA: charts[]

    DAA->>DAA: 数值归一化 / 组装 DataAnalysisResult
    DAA-->>Coord: data_analysis_results
    deactivate DAA

    alt deliverable = report（默认）
        Coord->>Gen: content_synthesizer → report_generator
        activate Gen
        Gen->>Gen: LLM 撰写正文各章节
        Gen->>RS: build_data_analysis_section(data_analysis_results)
        RS-->>Gen: 分析结果 / 图表 / 分析来源
        Gen->>HTML: FINAL_REPORT.html + ECharts
        HTML-->>Coord: HTML 报告
        deactivate Gen
    else deliverable = ppt
        Coord->>PPT: ppt_generator
        activate PPT
        PPT->>PPT: PageAgent 生成大纲与页面
        PPT->>PS: build_data_analysis_slides(data_analysis_results)
        PS-->>PPT: 分析结果 / 图表 / 来源页
        PPT-->>Coord: ppt/index.html + slides/
        deactivate PPT
    else deliverable = none
        Note over Coord: 仅保留 data_analysis_results
    end

    Coord->>Storage: 03_data_analysis.json<br/>reports/ 或 ppt/
    Storage-->>User: 项目目录与产物路径
```

---

### 分析模块在报告 / PPT 中的呈现

```mermaid
flowchart LR
    DAR["data_analysis_results"]

    DAR --> RS["report_section.py"]
    DAR --> PS["ppt_section.py"]

    RS --> R1["### 分析结果<br/>表格 + 结论"]
    RS --> R2["### 分析图表<br/>ECharts"]
    RS --> R3["### 分析来源<br/>仅表格引用的 W/R 来源"]

    PS --> P1["幻灯片：分析结果"]
    PS --> P2["幻灯片：图表"]
    PS --> P3["幻灯片：分析来源"]

    R1 & R2 & R3 --> FR["FINAL_REPORT.md/html"]
    P1 & P2 & P3 --> PPT["ppt/slides/*.html"]

    style DAR fill:#d3f9d8,stroke:#099268
    style FR fill:#dbe4ff,stroke:#364fc7
    style PPT fill:#c3fae8,stroke:#0ca678
```

---

### 模式对比（路由说明）

```mermaid
flowchart LR
    User([👤 用户])

    User --> Mode{命令 / 模式}

    Mode -->|search / report| NormalFlow["🔍 搜索<br/>→ 生成智能体<br/>（无独立分析模块）"]
    Mode -->|analyze| AnalyzeFlow["🔍 搜索<br/>→ 📊 DataAnalysisAgent<br/>（RAG + LLM 抽表）"]

    AnalyzeFlow --> Deliverable{--deliverable}

    Deliverable -->|report 默认| ReportOut["📝 综合报告<br/>+ 金融数据分析章节"]
    Deliverable -->|ppt| PPTOut["📽️ 多页 HTML PPT<br/>+ 分析幻灯片"]
    Deliverable -->|none| JSONOut["📄 仅 03_data_analysis.json"]

    style AnalyzeFlow fill:#d3f9d8,stroke:#099268
    style NormalFlow fill:#dbe4ff,stroke:#364fc7
    style ReportOut fill:#e7f5ff,stroke:#1971c2
    style PPTOut fill:#c3fae8,stroke:#0ca678
    style JSONOut fill:#fff3bf,stroke:#f59f00
```

---

### 数据流总览

```mermaid
flowchart TB
    Q["用户 query"]
    Search["🔍 deep_searcher"]
    SR["search_results[]"]
    DAA["📊 DataAnalysisAgent"]
    RAG["📚 RAGClient"]
    LSA["llm_search_analyzer"]
    CB["chart_builder"]
    DAR["data_analysis_results"]
    RC["ReportCoordinator"]
    RS["report_section"]
    PPT["PPTCoordinator + ppt_section"]
    FR["FINAL_REPORT"]
    Slides["ppt/slides"]

    Q --> Search --> SR --> DAA
    Q --> RAG --> DAA
    DAA --> LSA --> CB --> DAR
    DAR --> RS --> RC --> FR
    DAR --> PPT --> Slides
    SR --> RC
```

---

*文档版本：v2 — 对齐 LLM 抽表主路径；RAG 内嵌于 DataAnalysisAgent；支持 `--deliverable report/ppt/none`。*
