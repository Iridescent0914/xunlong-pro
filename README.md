# SmartFin

SmartFin 是一个面向金融分析、研究报告、演示文稿和数据洞察的多智能体内容生成系统。项目基于 XunLong 的多智能体框架演进而来，保留通用内容生成能力，并强化了金融数据分析、RAG 证据增强、可视化报告和 Web/API 工作流。

> 基于 XunLong 项目改造，当前项目定位为 SmartFin 智能金融分析与内容生成平台。

## 核心能力

- 智能金融分析：结合网页搜索、RAG 证据包和结构化分析，生成关键指标、关键发现、图表与分析报告。
- 文件数据分析：通过 Web/API 上传 CSV 或文本内容，生成统计指标、数据洞察、可视化图表和 HTML/Markdown 报告。
- RAG 证据增强：内置年报 RAG 和 Yahoo Finance RAG 配置入口，可在前端动态切换知识来源。
- 研究报告生成：支持综合、日报、分析、研究等报告类型，可输出 HTML 或 Markdown。
- PPT 生成：根据主题自动生成演示结构、页面内容、主题风格和演讲备注，并可导出为 PPTX。
- 多智能体协作：基于 LangGraph 编排任务分解、网页搜索、内容综合、质量评估、报告/PPT/小说生成等流程。
- 文档上下文：CLI 和 API 可接收 `.txt`、`.pdf`、`.docx` 作为补充材料。
- 多格式导出：支持 Markdown、HTML、PDF、DOCX、PPTX 等常用交付格式。
- 任务化 Web API：长任务采用任务队列模型，前端可轮询进度、查看详情并下载结果。
- 通用内容创作：保留小说创作等 XunLong 原有能力，适合演示多智能体扩展场景。

## 项目结构

```text
SmartFin/
├── xunlong.py                  # CLI 入口
├── run_api.py                  # Web/API 开发启动入口
├── requirements.txt            # Python 依赖
├── src/
│   ├── api.py                  # FastAPI 主应用
│   ├── deep_search_agent.py    # 统一智能体入口
│   ├── agents/                 # 报告、PPT、小说、数据分析等智能体
│   ├── llm/                    # LLM 配置、客户端、Prompt 管理
│   ├── tools/                  # 搜索、图片、文档、Excel 等工具
│   ├── export/                 # PDF/DOCX/PPTX/Markdown 导出
│   ├── mcp/                    # MCP 搜索集成
│   ├── search/                 # 搜索管理
│   └── task_manager.py         # Web 任务管理
├── frontend-static/
│   └── index.html              # 单文件前端界面
├── RAG/                        # 年报 RAG 子系统
├── financeRAG/                 # 金融数据 RAG 子系统
├── prompts/                    # 智能体和任务提示词
├── templates/                  # HTML 输出模板
├── docs/                       # 文档站和项目说明
├── tests/                      # 单元测试与集成测试
├── storage/                    # 生成项目与输出文件
└── tasks/                      # Web/API 任务记录
```

## 环境准备

推荐使用 Python 3.10+。如果使用 Conda：

```powershell
conda create -n xunlong python=3.11
conda activate xunlong
pip install -r requirements.txt
```

网页搜索依赖 Playwright 浏览器：

```powershell
playwright install chromium
```

PDF 导出依赖 WeasyPrint。Windows 通常随 Python 包安装即可；macOS/Linux 如需 PDF 导出，可根据 WeasyPrint 官方说明安装系统库。

## 配置环境变量

复制环境变量模板：

```powershell
copy .env.example .env
```

至少配置一个可用的大模型服务。当前代码优先支持 OpenAI 兼容接口，并内置 Qwen、OpenAI、Anthropic、Zhipu、DeepSeek、Azure OpenAI、Ollama 等 provider 识别。

常用配置示例：

```env
DEFAULT_LLM_PROVIDER=qwen
DEFAULT_LLM_MODEL=qwen-max
DASHSCOPE_API_KEY=your_dashscope_api_key

LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com

ZHIPU_MCP_API_KEY=your_zhipu_mcp_api_key
UNSPLASH_ACCESS_KEY=your_unsplash_access_key
PEXELS_API_KEY=your_pexels_api_key

ANNUAL_REPORT_RAG_ENABLED=true
YAHOO_FINANCE_RAG_ENABLED=false
```

## 运行方式

### 1. CLI

```powershell
conda activate xunlong
python xunlong.py --help
python xunlong.py status
```

当前 CLI 文件仍为 `xunlong.py`，支持以下子命令：

```text
report    生成研究报告
analyze   金融数据分析，可选生成报告或 PPT
fiction   小说创作
ppt       演示文稿生成
export    导出项目
iterate   迭代修改已有项目
ask       快速问答入口
status    查看运行配置状态
```

### 2. Web/API

```powershell
conda activate xunlong
python run_api.py
```

服务默认运行在：

```text
http://127.0.0.1:8000/
```

访问根路径会打开内置前端界面，API 文档可通过 FastAPI 自动文档查看：

```text
http://127.0.0.1:8000/docs
```

### 3. 后端主应用

FastAPI 主应用位于 `src/api.py`，可按模块方式直接启动：

```powershell
conda activate xunlong
python -m src.api
```

也可以使用 Uvicorn：

```powershell
uvicorn src.api:app --host 127.0.0.1 --port 8000
```

### 4. 前端界面

前端是 `frontend-static/index.html` 单文件应用。最方便的方式是启动后端后访问：

```text
http://127.0.0.1:8000/
```

也可以单独启动静态服务器：

```powershell
cd frontend-static
python -m http.server 8080
```

然后访问：

```text
http://127.0.0.1:8080/index.html
```

前端默认调用 `http://localhost:8000/api/v1`，因此提交任务、查看进度和下载结果时需要同时运行后端服务。

## CLI 使用示例

### 生成研究报告

```powershell
python xunlong.py report "2026年人工智能行业趋势分析"
python xunlong.py report "新能源汽车产业链研究" --type research --depth deep --max-results 30 -o html -v
python xunlong.py report "企业数字化转型方案" --input-file .\docs\brief.docx
```

常用参数：

| 参数 | 说明 |
| --- | --- |
| `--type` / `-t` | `comprehensive`、`daily`、`analysis`、`research` |
| `--depth` / `-d` | `surface`、`medium`、`deep` |
| `--max-results` / `-m` | 最大搜索结果数 |
| `--output-format` / `-o` | `html`、`md`、`markdown` |
| `--html-template` | HTML 模板，如 `enhanced_professional` |
| `--html-theme` | HTML 主题，如 `light`、`dark` |
| `--input-file` | 补充 `.txt`、`.pdf`、`.docx` 文档 |

### 金融数据分析

```powershell
python xunlong.py analyze "分析2024年银行业营收趋势"
python xunlong.py analyze "分析华为营收表现" --deliverable report -o html
python xunlong.py analyze "分析新能源行业财务表现" --deliverable ppt -s business -n 12
python xunlong.py analyze "仅输出结构化金融分析" --deliverable none
```

常用参数：

| 参数 | 说明 |
| --- | --- |
| `--deliverable` / `-D` | `report`、`ppt`、`none` |
| `--depth` / `-d` | 搜索深度 |
| `--max-results` / `-m` | 最大搜索结果数 |
| `--ppt-style` / `-s` | PPT 风格 |
| `--slides` / `-n` | PPT 页数 |
| `--mock-search` | 使用本地 mock 搜索数据进行联调 |
| `--input-file` | 补充参考文档 |

### 生成 PPT

```powershell
python xunlong.py ppt "2026年产品发布会"
python xunlong.py ppt "公司年度经营复盘" --style business --slides 15 --theme blue
python xunlong.py ppt "AI 在教育行业的应用" --speech-notes "面向高校教师的分享"
```

### 创作小说

```powershell
python xunlong.py fiction "暴风雪山庄中的密室推理" --genre mystery --length short
python xunlong.py fiction "星际移民时代的家族史诗" --genre scifi --length medium --viewpoint third
python xunlong.py fiction "江湖门派纷争" --genre wuxia -c "群像叙事" -c "保留开放式结尾"
```

### 迭代与导出

生成任务完成后，终端会显示项目 ID 和项目目录。项目文件通常保存在 `storage/` 下。

```powershell
python xunlong.py iterate <project_id> "补充第三章的数据案例，并让结论更聚焦"

python xunlong.py export <project_id> --type pdf
python xunlong.py export <project_id> --type docx
python xunlong.py export <project_id> --type pptx
python xunlong.py export <project_id> --type md -o output.md
```

## Web/API 使用示例

API 基础地址：

```text
http://127.0.0.1:8000/api/v1
```

健康检查：

```http
GET /health
```

创建报告任务：

```http
POST /api/v1/tasks/report
Content-Type: application/json

{
  "query": "人工智能在金融风控中的应用",
  "report_type": "research",
  "search_depth": "deep",
  "max_results": 20,
  "output_format": "html",
  "html_template": "enhanced_professional",
  "html_theme": "light"
}
```

创建 PPT 任务：

```http
POST /api/v1/tasks/ppt
Content-Type: application/json

{
  "query": "新能源行业投资分析",
  "slides": 12,
  "style": "business",
  "theme": "default",
  "depth": "medium",
  "speech_notes": "用于课堂展示"
}
```

创建文件数据分析任务：

```http
POST /api/v1/tasks/file_analysis
Content-Type: application/json

{
  "query": "分析销售数据",
  "file_name": "sales.csv",
  "file_type": "csv",
  "file_content": "date,region,sales\n2026-01,East,1200",
  "use_llm": false
}
```

查询任务：

```http
GET /api/v1/tasks/{task_id}
GET /api/v1/tasks/{task_id}/result
GET /api/v1/tasks/{task_id}/download?file_type=html
GET /api/v1/tasks?limit=20
```

RAG 配置：

```http
GET /api/v1/config/rag
PUT /api/v1/config/rag
GET /api/v1/config/rag/initial
```

## 产物目录

每次生成会创建独立项目目录，保存元数据、中间过程和最终结果：

```text
storage/<project_id>/
├── metadata.json
├── intermediate/
│   ├── 01_task_decomposition.json
│   ├── 02_search_results.json
│   └── 03_data_analysis.json
├── reports/
│   ├── FINAL_REPORT.md
│   └── FINAL_REPORT.html
├── ppt/
│   └── ...
├── versions/
│   └── ...
└── exports/
    ├── report.pdf
    ├── report.docx
    └── presentation.pptx
```

## 技术栈

- Python 3.10+
- FastAPI / Uvicorn
- LangGraph / LangChain
- OpenAI-compatible LLM Client
- Playwright / aiohttp / trafilatura
- Pandas / OpenPyXL
- ChromaDB
- Jinja2 / Markdown / Markdown2
- WeasyPrint / python-docx / python-pptx
- Langfuse
- ECharts

## 测试与验证

```powershell
conda activate xunlong
python -m compileall src
python -m unittest
```

也可以按模块运行已有测试文件：

```powershell
python tests\test_html_conversion.py
python tests\test_echarts_template_script.py
```

## 许可证

本项目采用 [MIT License](./LICENSE)。



