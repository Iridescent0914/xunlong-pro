# XunLong 前端设计文档

> 本文档说明前端项目的结构、技术栈与启动方法。

---

## 一、项目结构

项目包含两套前端实现，共存于同一仓库：

```
xunlong-pro-main/
├── frontend/              # React + Vite 现代 SPA 项目（备用）
│   ├── index.html         # 入口 HTML
│   ├── package.json       # 依赖配置
│   ├── vite.config.js     # Vite 构建配置（含 API 代理）
│   ├── tailwind.config.js  # Tailwind CSS 配置
│   ├── postcss.config.js   # PostCSS 配置
│   ├── public/            # 静态公共资源
│   └── src/
│       ├── main.jsx       # React 根组件挂载
│       ├── App.jsx        # 根组件（路由入口）
│       ├── api/
│       │   └── client.js  # API 客户端封装
│       ├── components/
│       │   ├── Sidebar.jsx       # 侧边导航栏
│       │   └── TaskMonitor.jsx   # 任务状态监控组件
│       ├── pages/
│       │   ├── ReportPage.jsx     # 研究报告表单页
│       │   ├── FictionPage.jsx    # 小说创作表单页
│       │   ├── PptPage.jsx       # 演示文稿表单页
│       │   ├── TaskHistory.jsx    # 任务历史记录页
│       │   ├── AnalysisPlaceholder.jsx   # 数据分析占位页
│       │   └── RagPlaceholder.jsx        # RAG 检索占位页
│       └── styles/
│           └── global.css   # 全局样式
│
└── frontend-static/      # 纯 HTML + CSS 单文件（当前主推）
    ├── index.html         # 完整 SPA，所有交互逻辑内联（~2000 行）
    └── screenshot_report_form.png
```

**说明**：`frontend-static/index.html` 是当前使用的单文件版本，无需任何构建，可直接在浏览器打开或部署到任意静态服务器。

---

## 二、技术栈

| 层次 | 技术选型 | 说明 |
|------|---------|------|
| 框架 | 原生 HTML + CSS + JavaScript | 零依赖，单文件约 2000 行 |
| HTTP | Fetch API | 原生 AJAX 调用后端 |
| 样式 | CSS 变量 + 毛玻璃面板 | Morandi 水蓝水灰浅色主题 |
| 图标 | Emoji | 无额外图标依赖 |
| 图表 | ECharts 5.4.3 | CDN 引入，用于弹窗图表展示 |
| Markdown | 原生渲染 | `parseMarkdown()` 实现基础 Markdown 解析 |

---

## 三、页面模块说明

| 模块 | 路由 | 功能 | 状态 |
|------|------|------|------|
| 研究报告 | `/report` | 表单创建报告任务 + 实时监控 | ✅ 已完成 |
| 演示文稿 | `/ppt` | 表单创建 PPT 任务 + 实时监控 | ✅ 已完成 |
| 文件数据分析 | `/analysis` | 上传文件 + LLM 分析 + 指标卡片 + 图表弹窗 | ✅ 已完成 |
| 任务历史 | `/history` | 历史任务列表 | ✅ 已完成 |

---

## 四、API 接口对接

前端通过 `/api/v1` 前缀调用后端 API：

```
GET  /api/v1/tasks              → 任务列表
POST /api/v1/tasks/report       → 创建报告任务
POST /api/v1/tasks/fiction      → 创建小说任务
POST /api/v1/tasks/ppt          → 创建 PPT 任务
POST /api/v1/tasks/file_analysis → 创建文件分析任务
GET  /api/v1/tasks/{task_id}   → 查询任务状态
GET  /api/v1/tasks/{task_id}/result  → 获取任务结果（含分析数据）
GET  /api/v1/tasks/{task_id}/download?file_type=html  → 下载 HTML
GET  /api/v1/tasks/{task_id}/download?file_type=md  → 下载 Markdown
DELETE /api/v1/tasks/{task_id}  → 取消任务
```

---

## 五、启动方法

> **总原则**：始终先启动后端，再启动前端。两个终端同时运行。

### 5.1 启动后端（第一步，必须先跑）

```bash
# 1. 进入项目根目录
cd xunlong-pro-main

# 2. 确保 .env 文件存在（从 .env.example 复制并填入密钥）
copy .env.example .env   # Windows
# 或 cp .env.example .env  (Linux/macOS)

# 3. 编辑 .env，填入至少一个 LLM API Key，例如：
#    DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
#    （通义千问 / OpenAI / DeepSeek 等至少配置一个）

# 4. 启动后端（监听 0.0.0.0:8000）
python run_api.py
```

> 后端启动后会输出：`INFO: Uvicorn running on http://0.0.0.0:8000`

### 5.2 访问前端

> **重要**：后端 `run_api.py` 已经内置了前端静态文件路由，直接访问 `http://localhost:8000` 即可看到前端页面。

```
浏览器访问 http://localhost:8000
```

---

## 六、核心功能实现

### 1. 任务轮询机制

任务提交后，前端每 1.5 秒轮询一次任务状态：

```javascript
state.monitorTimer = setInterval(pollMonitor, 1500);
pollMonitor();
```

状态变为 `completed` / `failed` / `cancelled` 时自动停止轮询。file_analysis 任务完成后会调用 `/tasks/{task_id}/result` 获取分析结果并渲染。

### 2. 文件上传处理

支持 `.txt`、`.pdf`、`.docx` 三种格式。PDF 以 Base64 编码传输：

```javascript
async function readFileContent(fileInput) {
  if (file.name.endsWith('.pdf')) {
    const buf = await file.arrayBuffer();
    content = '[PDF_BASE64]' + arrayBufferToBase64(buf);
  } else {
    content = await file.text();
  }
}
```

### 3. 文件分析结果渲染

任务完成后调用 `renderFileAnalysisResult()` 展示分析结果，包含：

- **指标卡片**：`renderMetrics()` 渲染关键数值指标
- **关键发现**：`renderKeyFindings()` 渲染 LLM 分析和统计发现
- **图表弹窗**：`renderCharts()` + `openChartModal()` 提供 ECharts 弹窗查看

```javascript
function renderFileAnalysisResult(result) {
  const data = result.result || result;
  // 渲染指标卡片
  renderMetrics(data.metrics);
  // 渲染关键发现（含 LLM 分析）
  renderKeyFindings(data.key_findings);
  // 渲染图表列表
  renderCharts(data.charts || []);
}
```

### 4. 主题色切换

每个模块有独立的强调色（`modules` 对象中定义）：

```javascript
report:       { color: '#2563eb', accent: '#eff6ff' }  // 蓝色
ppt:          { color: '#059669', accent: '#ecfdf5' }  // 绿色
file_analysis: { color: '#7a9ec0', accent: '#eef2f6' } // 莫兰迪蓝
```

### 5. 图表弹窗实现

- `openChartModal()` 使用 ECharts CDN 渲染图表
- 支持 `chart.spec` 或 `chart.option` 格式
- 自动 JSON 解析字符串格式的 option
- ESC 键关闭弹窗

### 6. Markdown 解析

`parseMarkdown()` 实现基础 Markdown 渲染：
- 标题（`#` ~ `######`）
- 加粗（`**text**`）
- 斜体（`*text*`）
- 行内代码（`` `code` ``）
- 代码块（` ```code``` `）
- 链接（`[text](url)`）

---

## 七、后续开发注意事项

1. **RAG 检索模块**：当前为占位状态，需要后端实现对应 agent 并在 `coordinator.py` 中注册节点。

2. **环境变量**：前端 API 地址通过 `API_BASE` 常量配置（当前硬编码为 `http://localhost:8000`）。

3. **CORS 跨域**：后端 FastAPI 已配置 CORS 中间件（`src/api.py`），使用后端内置前端时（同端口 8000），无跨域问题。

4. **图表数据格式**：后端返回的 chart 对象需包含 `title`、`spec` 或 `option` 字段，前端弹窗使用 ECharts 渲染。
