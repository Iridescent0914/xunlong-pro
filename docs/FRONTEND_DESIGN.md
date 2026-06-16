# XunLong 前端设计文档

> 本文档说明前端项目的结构、技术栈与启动方法。

---

## 一、项目结构

项目包含两套前端实现，共存于同一仓库：

```
xunlong-pro-main/
├── frontend/              # React + Vite 现代 SPA 项目（主推）
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
└── frontend-static/      # 纯 HTML + CSS 单文件（零依赖备用）
    ├── index.html         # 完整 SPA，所有交互逻辑内联
    └── screenshot_report_form.png
```

**说明**：`frontend/` 是 React 版本，功能完整；`frontend-static/index.html` 是单文件版本，无需任何构建，可直接在浏览器打开或部署到任意静态服务器。（目前我使用的是这个静态版，react版我还没调）

---

## 二、技术栈

| 层次 | 技术选型 | 说明 |
|------|---------|------|
| 框架 | React 18 + Vite 6 | 现代 SPA，支持热更新 |
| 路由 | React Router v7 | 页面导航 |
| HTTP | Axios + Fetch | 统一封装，Fetch 用于文件上传 |
| 样式 | Tailwind CSS 3 + 自定义 CSS | 原子化 CSS + 毛玻璃面板设计 |
| 图标 | Emoji | 无额外图标依赖，纯 Emoji 渲染 |
| UI | 纯 CSS | 无 Ant Design / Material UI 等重型库 |

---

## 三、页面模块说明

| 模块 | 路由 | 功能 | 状态 |
|------|------|------|------|
| 研究报告 | `/report` | 表单创建报告任务 + 实时监控 | ✅ 已完成 |
| 小说创作 | `/fiction` | 表单创建小说任务 + 实时监控 | ✅ 已完成 |
| 演示文稿 | `/ppt` | 表单创建 PPT 任务 + 实时监控 | ✅ 已完成 |
| 数据分析 | `/analysis` | 占位界面（占位） | 🔲 待接入 agent |
| RAG 检索 | `/rag` | 占位界面（占位） | 🔲 待接入 agent |
| 任务历史 | `/history` | 历史任务列表 | ✅ 已完成 |

---

## 四、API 接口对接

前端通过 `/api/v1` 前缀调用后端 API：

```
GET  /api/v1/tasks              → 任务列表
POST /api/v1/tasks/report       → 创建报告任务
POST /api/v1/tasks/fiction      → 创建小说任务
POST /api/v1/tasks/ppt          → 创建 PPT 任务
GET  /api/v1/tasks/{task_id}   → 查询任务状态
GET  /api/v1/tasks/{task_id}/result  → 获取任务结果
GET  /api/v1/tasks/{task_id}/download?file_type=html  → 下载 HTML
DELETE /api/v1/tasks/{task_id}  → 取消任务
```

Vite 开发服务器已将 `/api` 代理到 `http://localhost:8000`（`frontend/vite.config.js` 第 9 行）。生产环境（直接用后端内置前端时）前端页面和 API 都在同一端口（8000），无跨域问题。

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

# 4. 启动后端（监听 0.0.0.0:8000，reload=True 开启热重载）
python run_api.py
```

> 后端启动后会输出：`INFO: Uvicorn running on http://0.0.0.0:8000`

### 5.2 启动前端（第二步）

> **重要**：后端 `run_api.py` 已经内置了前端静态文件路由，直接访问 `http://localhost:8000` 即可看到前端页面，**无需单独启动 http.server**。
> 如果选择"方式 B/C"单独启动前端服务器，通常用于调试前端样式/脚本的场景。

#### 方式 A：后端内置（最简，无需额外命令）

```bash
# 只启动后端（已内置前端）
python run_api.py
# 浏览器访问 http://localhost:8000
```

#### 方式 B：独立前端服务器（可选，用于前端开发调试）

```bash
# 新开一个终端，进入前端静态目录
cd frontend-static

# 启动 Python 内置静态服务器（端口自定义，这里用 3000）
python -m http.server 3000

# 浏览器访问 http://localhost:3000
```

#### 方式 C：React SPA（需要 npm，偶还没 debug）

```bash
# 新开一个终端
cd frontend
npm install          # 首次安装依赖
npm run dev          # 启动 Vite dev server（自动打开 http://localhost:5173）
```

> 前提：后端 `python run_api.py` 必须先跑起来。Vite 会把 `/api` 请求代理到 `http://localhost:8000`。

### 5.3 完整启动流程（最终状态）

默认方式（后端内置前端），只需一个终端：

```
┌─────────────────────────────────────────────────────┐
│  终端 1 — 后端 API（含前端服务）                      │
│  ==================================================  │
│  $ python run_api.py                                 │
│  INFO: Uvicorn running on http://0.0.0.0:8000     │
│  Frontend static files mounted at /static           │
│                                                      │
│  职责：处理所有 /api/v1/* 请求 + 提供前端页面        │
└─────────────────────────────────────────────────────┘

用户浏览器：
  http://localhost:8000  ← 前端页面（表单、监控）
         │ AJAX
         ▼
  http://localhost:8000/api/v1  ← 后端 API
```

**关闭顺序**：直接 Ctrl+C 关闭后端即可。

---

## 六、关键实现细节

### 1. 任务轮询机制

任务提交后，前端每 1.5 秒轮询一次任务状态（`frontend-static/index.html` 第 978 行）：

```javascript
state.monitorTimer = setInterval(pollMonitor, 1500);
pollMonitor();
```

状态变为 `completed` / `failed` / `cancelled` 时自动停止轮询。

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

### 3. 主题色切换

每个模块有独立的强调色（`modules` 对象中定义）：

```javascript
report:  { color: '#2563eb', accent: '#eff6ff' }  // 蓝色
fiction: { color: '#db2777', accent: '#fdf2f8' }  // 桃红色
ppt:     { color: '#059669', accent: '#ecfdf5' }  // 绿色
```

### 4. API 客户端封装（React 版本）

`frontend/src/api/client.js` 导出统一的 API 方法：

```javascript
export const api = {
  createReport: payload => request('/tasks/report', { method: 'POST', body: JSON.stringify(payload) }),
  createFiction: payload => request('/tasks/fiction', { method: 'POST', body: JSON.stringify(payload) }),
  createPPT: payload => request('/tasks/ppt', { method: 'POST', body: JSON.stringify(payload) }),
  getTaskStatus: taskId => request(`/tasks/${encodeURIComponent(taskId)}`),
  getTaskResult: taskId => request(`/tasks/${encodeURIComponent(taskId)}/result`),
  cancelTask: taskId => request(`/tasks/${encodeURIComponent(taskId)}`, { method: 'DELETE' }),
  getTaskList: (limit = 20) => request(`/tasks?limit=${limit}`),
};
```

---

## 七、后续开发注意事项

1. **数据分析 / RAG 模块**：当前为占位状态，需要后端实现对应 agent 并在 `coordinator.py` 中注册节点，前端已预留好 API 对接入口（`/tasks/analysis`、`/tasks/rag`）。

2. **环境变量**：React 版本可通过 `.env` 文件配置 API 地址：
   ```
   VITE_API_BASE_URL=http://localhost:8000/api/v1
   ```

3. **CORS 跨域**：后端 FastAPI 已配置 CORS 中间件（`src/api.py`），允许前端 dev server 的跨域请求。使用后端内置前端时（同端口 8000），无跨域问题。

4. **任务结果查看**：目前点击"查看详情"直接渲染 JSON，可后续接入 Markdown 渲染器（如 `react-markdown`）美化输出。
