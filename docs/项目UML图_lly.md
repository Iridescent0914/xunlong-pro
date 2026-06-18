### 核心智能体（金融数据分析模式）

> **模式说明**：用户选择「金融数据分析模式」时，网页搜索与数据分析并行执行；数据分析智能体结合 RAG 金融知识库完成指标计算与解读，生成智能体综合 **分析结果 + 搜索资料** 撰写报告。

```mermaid
graph TD
    subgraph "协调层"
        Coordinator["🎯 协调器 Coordinator<br/>━━━━━━━━━━━<br/>• 识别金融数据分析模式<br/>• 任务分解与流程编排<br/>• 并行调度搜索与分析"]
    end

    subgraph "知识增强层"
        RAG["📚 金融 RAG 知识库<br/>━━━━━━━━━━━<br/>• 研报 / 指标口径 / 术语<br/>• 监管规则与行业基准<br/>• 向量检索与上下文注入"]
    end

    subgraph "执行层"
        SearchAgent["🔍 搜索智能体<br/>━━━━━━━━━━━<br/>• 金融资讯与政策搜索<br/>• 市场动态内容提取<br/>• 外部信息整合"]

        AnalysisAgent["📊 金融数据分析智能体<br/>━━━━━━━━━━━<br/>• Excel / 财报数据清洗<br/>• 金融数据库查询与统计<br/>• RAG 增强解读<br/>• 输出结构化结论与图表 spec"]

        GenerationAgent["📝 生成智能体<br/>━━━━━━━━━━━<br/>• 撰写金融数据报告<br/>• 融合分析结论与搜索资料<br/>• 结构组织与风格控制"]

        ReviewAgent["✅ 审核智能体<br/>━━━━━━━━━━━<br/>• 指标口径一致性<br/>• 数据与图表校验<br/>• 内外部信息交叉验证"]

        IterationAgent["🔄 迭代智能体<br/>━━━━━━━━━━━<br/>• 需求分析<br/>• 局部修改<br/>• 版本管理"]
    end

    Coordinator --> SearchAgent
    Coordinator --> AnalysisAgent
    Coordinator --> GenerationAgent
    Coordinator --> ReviewAgent
    Coordinator --> IterationAgent

    RAG -.检索增强.-> AnalysisAgent

    SearchAgent -.提供外部资料.-> GenerationAgent
    SearchAgent -.补充市场背景.-> AnalysisAgent

    AnalysisAgent -.分析结论与图表.-> GenerationAgent

    GenerationAgent -.提交审核.-> ReviewAgent
    ReviewAgent -.反馈修改.-> GenerationAgent

    style Coordinator fill:#ff6b6b,stroke:#c92a2a,color:#fff
    style RAG fill:#228be6,stroke:#1864ab,color:#fff
    style SearchAgent fill:#4c6ef5,stroke:#364fc7,color:#fff
    style AnalysisAgent fill:#12b886,stroke:#099268,color:#fff
    style GenerationAgent fill:#51cf66,stroke:#2b8a3e,color:#fff
    style ReviewAgent fill:#ffd43b,stroke:#f59f00,color:#333
    style IterationAgent fill:#ae3ec9,stroke:#862e9c,color:#fff
```

### 金融数据分析内容生成流程

> 网页搜索与数据分析 **并行执行**；生成智能体同时接收 `data_analysis_results` 与 `search_results`，分别用于数据章节与背景/市场解读章节。

```mermaid
sequenceDiagram
    autonumber
    participant User as 👤 用户
    participant CLI as 💻 CLI
    participant Coord as 🎯 协调器
    participant Search as 🔍 搜索智能体
    participant RAG as 📚 金融 RAG
    participant Analysis as 📊 金融数据分析智能体
    participant Gen as 📝 生成智能体
    participant Review as ✅ 审核智能体
    participant HTML as 📄 HTML转换器
    participant Export as 📁 导出管理器
    participant Storage as 💾 存储管理器

    User->>CLI: 选择金融数据分析模式 + 输入分析需求
    Note over User,CLI: 可选：上传 Excel/CSV<br/>或指定金融数据库连接
    CLI->>Coord: 启动金融数据分析工作流

    Coord->>Coord: 识别模式 = 金融数据分析
    Note over Coord: 拆解子任务<br/>并行调度搜索与分析

    par 并行采集与分析
        Coord->>Search: 执行金融资讯搜索
        activate Search
        Search->>Search: 网络搜索（政策 / 行情 / 行业动态）
        Search->>Search: 内容提取与质量评估
        Search-->>Coord: 返回 search_results
        deactivate Search
    and
        Coord->>Analysis: 执行金融数据分析
        activate Analysis
        Analysis->>Analysis: 读取 Excel / 财报 / 数据库
        Analysis->>Analysis: 数据清洗与金融指标计算

        Analysis->>RAG: 检索相关知识片段
        activate RAG
        Note over RAG: 指标口径、行业基准<br/>术语定义、监管规则
        RAG-->>Analysis: 返回 Top-K 上下文
        deactivate RAG

        Analysis->>Analysis: RAG 增强解读与归因
        Analysis->>Analysis: 输出结构化结论与图表 spec
        Analysis-->>Coord: 返回 data_analysis_results
        deactivate Analysis
    end

    Coord->>Gen: 生成金融数据报告（分析结果 + 搜索资料）
    activate Gen

    Gen->>Gen: 生成报告大纲
    Gen->>Gen: 撰写数据分析章节（基于 data_analysis_results）
    Gen->>Gen: 撰写背景与市场解读（基于 search_results）
    Gen->>Gen: 嵌入图表与表格说明
    Gen->>Gen: 统一金融报告风格

    Gen->>Review: 提交审核
    activate Review
    Review->>Review: 校验指标口径与数据一致性
    Review->>Review: 检查图表与文字是否匹配
    Review->>Review: 交叉验证分析结论与搜索资料

    alt 审核通过
        Review-->>Gen: 通过
        Gen-->>Coord: 返回 Markdown 内容
    else 审核未通过
        Review-->>Gen: 反馈修改意见
        Gen->>Gen: 修订报告内容
        Gen-->>Coord: 返回 Markdown 内容
    end
    deactivate Review
    deactivate Gen

    Coord->>HTML: 转换为 HTML
    HTML-->>Coord: 返回 HTML

    Coord->>Storage: 保存项目文件
    Storage-->>Storage: metadata.json<br/>search_results<br/>data_analysis_results<br/>RAG 引用片段<br/>最终金融数据报告

    opt 用户请求导出
        User->>CLI: export 命令
        CLI->>Export: 执行导出
        Export->>Export: 生成 PDF / DOCX
        Export->>Storage: 保存到 exports/
        Export-->>User: 导出完成
    end

    opt 用户请求迭代
        User->>CLI: iterate 命令
        CLI->>Coord: 启动迭代流程
        Coord->>Storage: 创建版本备份
        alt 需更新源数据或分析逻辑
            Coord->>Analysis: 重新执行分析（含 RAG）
            Analysis-->>Coord: 返回更新后的 data_analysis_results
            Coord->>Gen: 同步更新数据报告章节
        else 需更新外部资讯
            Coord->>Search: 重新执行搜索
            Search-->>Coord: 返回更新后的 search_results
            Coord->>Gen: 同步更新背景与市场章节
        else 仅修改报告表述
            Coord->>Gen: 根据需求修订文案
        end
        Gen->>Review: 再次审核
        Review-->>Gen: 审核结果
        Gen-->>Storage: 保存新版本
        Storage-->>User: 迭代完成
    end
```

### 模式对比（路由说明）

```mermaid
flowchart LR
    User([👤 用户选择模式])

    User --> Mode{模式判断}

    Mode -->|综合报告 / PPT / 小说| NormalFlow["🔍 搜索智能体<br/>→ 生成智能体"]
    Mode -->|金融数据分析| DataFlow["🔍 搜索 ∥ 📊 分析 + RAG<br/>→ 生成智能体"]

    style DataFlow fill:#d3f9d8,stroke:#099268
    style NormalFlow fill:#dbe4ff,stroke:#364fc7
```
