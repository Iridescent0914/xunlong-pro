数据分析模块变更说明

概述
-	目的：让 `data_analysis` 智能体兼容外部 RAG evidence-pack（即项目中的 `fixtures/mock_rag.json` 风格），并提供一个轻量后端接口以返回 ECharts 配置（便于前端和报告嵌入）。
-	范围：仅限数据分析输入/输出适配、图表生成逻辑与后端 API；不包含 RAG 数据源实现。

主要改动文件
-	`src/agents/data_analysis/schemas.py`
    - 新增并补全 Pydantic 模型：`EvidenceItem`, `RAGSummary`, `RAGEvidencePack`, `WebSearchEvidencePack`, `UnifiedEvidence`, `AnalysisInput`。
    - 目的：统一 search_results 与 RAG evidence pack 的内部表示，供模块间互操作。

-	`src/agents/data_analysis/evidence_adapter.py`
    - 增加 `parse_rag_evidence_pack` 的输入校验（`validate_rag_pack`），将 RAG evidence pack 解析为内部 `EvidenceItem` 列表。
    - 提供 `rag_pack_to_refs` 把 evidence pack 转为下游兼容的 `RAGReference` 列表。

-	`src/agents/data_analysis/rag_client.py`
    - 修复 Mock loader：当 fixtures 中的 `mock_rag.json` 为 evidence-pack（dict）时，使用 `evidence_adapter.parse_rag_evidence_pack` 解析；如果为 list，则按元素解析为 `RAGReference`。
    - 目的：避免在读取 mock_rag 时把字符串错误地传入 Pydantic 导致 500 错误。

-	`src/agents/data_analysis/data_analysis_agent.py`
    - 支持 `input_data` 中直接传入 `rag_pack`（优先使用），并用 `evidence_adapter` 解析为 `RAGReference` 列表；否则回退到 `RAGClient.retrieve()`。
    - 目的：允许上游直接传入 RAG evidence-pack JSON，便于集成测试或管线中其他组件。

-	`src/agents/data_analysis/chart_builder.py`
    - 增强图表生成策略：支持平滑折线（area），环比柱状，双轴（dual-axis），以及简单的堆叠柱状（stacked）场景。
    - 输出保持为 ECharts-compatible 的 option（封装在 `EChartsGenerator` 返回结构中）。

-	`src/api.py`
    - 新增轻量 POST 接口：`/api/v1/data_analysis/charts`。
    - 功能：接收 `query`（必需），可选 `search_results`、`rag_pack`、`use_mock`，返回结构化的分析结果与 `charts`（ECharts 配置）。
    - 备注：该接口设计为前端或报告生成时可直接调用的轻量入口。

新增文件（示例/辅助）
-	`frontend-static/data_analysis_demo.html`（前端示例页面 — 我已加入仓库作为参考，但你要求不要把 demo 整合到 README 中，这里仅记录文件存在）
-	`scripts/demo_data_analysis_run.py`（离线演示脚本 — 已加入仓库，用于快速离线验证）

设计要点与兼容性
-	RAG 输入形状：兼容两类常见输入形式：
    1) evidence-pack（对象，包含 `evidence` 数组、`rag_summary` 等），参考 `docs/rag输出格式.md` 或 `fixtures/mock_rag.json`。
    2) 简单的参考片段数组（list of dict），每项可映射为内部 `RAGReference`。
-	数据流：上游 → (`rag_pack` 或 search_results) → `evidence_adapter` → `FinancialAnalyzer` → `chart_builder` → `EChartsGenerator` → 前端/报告。
-	向后兼容：如果没有提供 `rag_pack`，模块会回退到 `RAGClient`（可为 mock 或真实 API）检索；如果没有搜索结果，会使用 `fixtures/mock_search.json`（联调用）。

如何验证（简要）
- 说明性（不包含 demo 运行步骤）：
  - 确认 `fixtures/mock_rag.json` 存在且符合 evidence-pack 结构（`source`,`query`,`evidence` 数组, `rag_summary`）。
  - 启动后端服务（`run_api.py`），访问新增接口 `/api/v1/data_analysis/charts` 可获得 JSON 响应，返回中包含 `result`（结构化分析结果）与 `charts`（ECharts 配置）。

错误修复记录
- 修复了 `RAGClient._load_mock()` 在遇到 evidence-pack（dict）时的解析错误（原实现把 dict 内部字符串作为参数解包到 Pydantic，导致: "argument after ** must be a mapping, not str"）。现在会正确识别并调用 `parse_rag_evidence_pack`。

接入建议（给开发者）
- 若你负责的上游预处理会改变输入形状，请确保输出至少包含上面提到的 `evidence` 数组或可映射为 `RAGReference` 的结构；否则可把预处理输出在管线中先转换为项目当前的 `EvidenceItem` / `RAGReference` 形状。
- 把 `data_analysis` 的输出（返回的 `result`）直接作为 `ReportCoordinator.generate_report(..., data_analysis_results=result)` 的 `data_analysis_results` 参数，就能在最终报告中插入“金融数据分析”章节（`report_section.build_data_analysis_section` 已支持渲染 charts）。

后续工作（可选）
- 把 `/api/v1/tasks/report` 的异步任务流中自动触发数据分析，并将结果注入报告生成管线（可自动化展示）。
- 增加单元测试覆盖 `evidence_adapter.parse_rag_evidence_pack`、`rag_pack_to_refs` 与 `RAGClient._load_mock` 的不同输入形态。

文件位置（便于快速查阅）
- `src/agents/data_analysis/`（核心实现）
- `src/api.py`（新增 HTTP 接口）
- `fixtures/mock_rag.json`（示例 RAG pack）

当前文件仅包含改动说明与集成要点