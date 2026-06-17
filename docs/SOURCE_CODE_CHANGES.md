# 源代码修改记录

> 本文档记录本次对 XunLong 源码的主要修改，分为**原有功能修复**和 **Prompt 完善**两大部分。

---

## 一、原有功能修复

### 1.1 网络搜索：Playwright 替换为 httpx

#### 问题背景

在 Windows 上通过 `uvicorn` 运行 `run_api.py` 时，搜索功能报错 `NotImplementedError: Protocol not supported: select`，原因是：

- **根本原因**：uvicorn（FastAPI）使用 Windows 上的 `SelectorEventLoop`，而 Playwright 底层需要 `asyncio.create_subprocess_exec` 启动浏览器进程——Windows 的 `SelectorEventLoop` 不支持这个操作
- **表现**：搜索返回 0 条结果，系统退化为纯 LLM 补全，报告缺乏真实数据支撑

#### 搜索方案演进

```
第一阶段：Playwright 浏览器自动化
  ❌ Windows uvicorn 环境下无法启动浏览器进程
  ❌ SelectorEventLoop 不支持 subprocess

第二阶段：httpx + BeautifulSoup 直接请求 DuckDuckGo
  ✅ 无需浏览器，完全 HTTP 请求
  ❌ DuckDuckGo 检测 User-Agent，返回 Cloudflare 挑战页

第三阶段：httpx + html.duckduckgo.com 端点
  ✅ 专用 HTML 端点，返回真实搜索结果
  ✅ 全平台兼容，无需 Playwright
```

#### 修改文件

**`src/searcher/duckduckgo.py`**

新增 `search_with_httpx()` 方法，使用 `html.duckduckgo.com` 端点：

```python
async def search_with_httpx(
    self, query: str, max_results: int = 10
) -> List[SearchLink]:
    """
    使用 httpx 请求 DuckDuckGo HTML 端点（无需浏览器）。
    Uses html.duckduckgo.com which returns a simple, scrape-friendly HTML page.
    Falls back to main duckduckgo.com if lite endpoint fails.
    """
    # 优先尝试 html.duckduckgo.com/lite（简洁 HTML，无需 JS）
    r = await client.get("https://html.duckduckgo.com/html/", params=[("q", query)])
    # 降级：如果 lite 端点无结果，尝试主站
    if not results:
        r = await client.get("https://duckduckgo.com/html/", params=[...])
    soup = BeautifulSoup(html, "lxml")
    for result_div in soup.select(".result"):
        # 解析标题、URL、摘要
```

**`src/tools/web_searcher.py`**

- 移除 `from playwright.async_api import async_playwright`（不再在 import 区引用）
- 新增 `import httpx` + `from bs4 import BeautifulSoup`
- 新增 `_fetch_full_content_with_httpx()` 方法，使用 httpx + BeautifulSoup 抓取网页正文
- 修改 `_search_duckduckgo()`，路由到 httpx 方法（不再调用 Playwright）

**注意**：`src/searcher/base.py` 中的抽象基类 `BaseSearcher` 和 `src/tools/web_searcher.py` 中仍保留了旧的 `_fetch_full_content_with_browser()` 方法，作为向后兼容保留，不影响当前搜索流程。

#### 修改效果

| 对比项 | 修复前 | 修复后 |
|--------|--------|--------|
| 浏览器依赖 | 需要 Playwright + Chromium | 无需浏览器 |
| Windows uvicorn 兼容性 | ❌ NotImplementedError | ✅ 正常 |
| 实现方式 | subprocess + 浏览器 | 纯 HTTP 请求 |
| 依赖重量 | playwright（~200MB） | httpx（轻量） |

---

### 1.2 下载接口修复 + PPT ZIP 打包

#### 问题背景

报告生成完成后，点击"下载"按钮返回 404，原因是 `DeepSearchCoordinator.process_query()` 只返回了 `project_dir`，没有返回 `output_dir`，导致 `task_info.output_dir` 为 `None`。

此外，PPT 任务有多个 slide 文件（HTML），需要一个打包机制。

#### 修改文件

**`src/agents/coordinator.py`**

修复 `_coordinator_node` 的返回值，补上 `output_dir`：

```python
# 之前只有
return {"project_dir": project_dir}

# 修复后
return {
    "project_dir": str(self.storage.get_project_dir()),
    "output_dir": str(self.storage.get_project_dir())  # 新增，供下载接口使用
}
```

**`src/api.py`**

1. **`GET /api/v1/tasks/{task_id}/result`**：在 `COMPLETED` 状态时返回 `output_dir` 字段：

```python
if task_info.status == TaskStatus.COMPLETED:
    response.update({
        "result": task_info.result,
        "project_id": task_info.project_id,
        "output_dir": task_info.output_dir  # 新增
    })
```

2. **`GET /api/v1/tasks/{task_id}/download`**：重写整个接口，添加 PPT ZIP 打包逻辑：

```python
@app.get("/api/v1/tasks/{task_id}/download")
async def download_task_file(task_id: str, file_type: str = Query("html", ...)):
    output_dir = Path(task_info.output_dir)

    if file_type == "html":
        # PPT 任务 → 打包成 zip（含所有 slide 文件）
        if task_info.task_type == TaskType.PPT:
            import zipfile, time
            zip_name = f"ppt_{int(time.time())}.zip"
            zip_path = output_dir / zip_name
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in (output_dir / "ppt").rglob("*"):
                    if file_path.is_file():
                        zf.write(file_path, file_path.relative_to(output_dir / "ppt"))
            return FileResponse(path=zip_path, filename="ppt.zip",
                               headers={"Content-Disposition": "attachment; filename*=UTF-8''ppt.zip"})
        else:
            file_path = output_dir / "reports" / "FINAL_REPORT.html"

    elif file_type == "md":
        file_path = output_dir / "reports" / "FINAL_REPORT.md"
```

3. **响应头修复**：确保 `Content-Disposition` 为 `attachment`（触发下载而非预览）

---

### 1.3 前端静态文件服务集成

#### 问题背景

前端单文件（`frontend-static/index.html`）需要独立启动一个 `http.server`，增加了部署复杂度。

#### 修改文件

**`src/api.py`**

将前端静态文件挂载到 FastAPI 路由，前端和 API 共用一个 8000 端口：

```python
# 静态资源挂载到 /static/（css/js/图片等）
frontend_static = pathlib.Path("frontend-static")
if frontend_static.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_static)), name="frontend-static")

# 根路径 / 直接返回 index.html
@app.get("/")
async def root():
    index_path = frontend_static / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"name": "XunLong API", ...}
```

修改后：**只需启动 `python run_api.py`**，访问 `http://localhost:8000` 即可看到前端页面。

#### 前端下载按钮动态文案

**`frontend-static/index.html`**：新增 PPT 任务下载按钮的动态文案逻辑：

```javascript
// 之前：所有任务都显示"下载 HTML"
<a class="ghost-btn" href="...download?file_type=html">下载 HTML</a>

// 修复后：PPT 任务显示"下载 PPT"，其他任务显示"下载 HTML"
<a class="ghost-btn" href="...download?file_type=html">
  ${info.task_type === 'ppt' ? '下载 PPT' : '下载 HTML'}
</a>
// Markdown 下载按钮：仅非 PPT 任务显示
${info.task_type !== 'ppt' ? '...' : ''}
```

---

### 1.4 后台任务调度：TaskWorker

#### 问题背景

后端启动后，API 正常响应，但后台的任务队列轮询没有启动，已提交的任务永远不会开始执行。

#### 修改文件

**`src/api.py`**

注册 `TaskWorker` 到 FastAPI startup 事件：

```python
from .task_worker import TaskWorker

task_worker = TaskWorker(task_manager=task_manager)

@app.on_event("startup")
async def startup_background_worker():
    import asyncio
    asyncio.create_task(task_worker.run_forever(interval=3))
```

`TaskWorker` 每 3 秒轮询一次任务队列，触发等待中的任务开始执行。

---

### 1.5 PPT 多页并发生成稳定性修复

#### 问题背景

PPT 生成流程（`generate_ppt_v3`）一次性并发 15 个 LLM 请求，导致阿里云 DashScope API 触发 429 限流，部分页面生成失败。同时存在以下稳定性问题：

- `response` 为 `None`（请求超时）时，后续代码调用 `.get()` 触发 `'NoneType' object has no attribute 'get'` 错误
- 429 错误被 client 层吞掉，上层重试逻辑从未触发
- 日志中 DEBUG 级别信息大量刷屏，掩盖关键错误

#### 修改文件

**`src/llm/client.py`**

修改 `_openai_chat_completion` 和 `chat_completion` 两个方法：

```python
# 1. response 可能为 None（超时），补充判空并抛出可重试异常
response = await self._client.chat.completions.create(**params)

if response is None:
    raise TimeoutError("API response is None (timeout)")

# 2. 429 和超时归类为可重试错误，不在此打印 ERROR
error_str = str(e)
is_retriable = (
    "429" in error_str
    or "limit_requests" in error_str
    or "timeout" in error_str.lower()
    or "TimedOut" in type(e).__name__
)
if is_retriable:
    raise  # 让上层重试逻辑处理，不要吞掉
```

**`src/agents/ppt/page_agent.py`**

为 `PageAgent` 添加并发控制 + 完善重试逻辑：

```python
def __init__(self, llm_client, css_guide: str):
    self._semaphore = asyncio.Semaphore(4)  # 最多 4 个并发，防止 DashScope 限流

async def _chat_with_retry(self, messages, ..., max_retries=3, initial_delay=3.0):
    for attempt in range(max_retries):
        async with self._semaphore:
            try:
                return await self.llm_client.chat_completion(...)
            except Exception as e:
                # 429 / rate limit / timeout → 指数退避重试
                if is_retriable and attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)  # 3s → 6s → 12s
                    await asyncio.sleep(delay)
                else:
                    raise
```

**`run_api.py`**

屏蔽 DEBUG 日志，减少刷屏：

```python
logger.remove()
logger.add(sys.stderr, level="INFO")  # 只输出 INFO 及以上
```

#### 修改效果

| 问题 | 修复前 | 修复后 |
|------|--------|--------|
| 并发量 | 15 页同时请求 | Semaphore(4) 控制，最多 4 页并发 |
| 429 限流 | 直接失败 | 指数退避重试 3 次（3s→6s→12s） |
| 超时 response=None | `'NoneType' object has no attribute 'get'` | 抛出 `TimeoutError`，进入重试 |
| DEBUG 日志刷屏 | 大量刷屏 | level=INFO，仅显示关键进度 |

---

### 1.6 图片下载器跳过无效 URL

#### 问题背景

图片下载器对没有 `http://` / `https://` 前缀的 URL 直接发送请求，触发 `httpx` 报错并打 ERROR 日志。

#### 修改文件

**`src/tools/image_downloader.py`**

在 `download_image` 方法开头添加 URL 有效性检查：

```python
# URL 有效性检查，无效 URL 不报错直接跳过
if not url or not (url.startswith("http://") or url.startswith("https://")):
    return None
```

---

### 1.7 PPT 接口字段缺失修复

#### 问题背景

前端 `frontend-static/index.html` 的 PPT 表单中包含"深度"（depth）和"演说稿说明"（speech_notes）两个字段，但提交时没有传递给后端，导致后端无法获取这些参数。

#### 修改文件

**`frontend-static/index.html`** — PPT 模块的 `submit()` 方法

- `body()` 改为 `async body()`，支持文件上传（与其他模块保持一致）
- 补充 `depth` 和 `speech_notes` 两个字段
- 删除不存在的 `output_format`、`html_template`、`html_theme` 字段

```javascript
submit() {
  return {
    path: '/tasks/ppt',
    async body() {
      const fileData = await readFileContent($('field-file'));
      return {
        query: ($('field-query').value || '').trim(),
        slides: Number($('field-slides').value),
        style: $('field-style').value,
        theme: $('field-theme').value,
        depth: $('field-depth').value,          // 新增
        speech_notes: ($('field-speech_notes').value || '').trim(),  // 新增
        ...(fileData ? { user_document: fileData } : {})
      };
    }
  };
}
```

**`src/api.py`** — `PPTRequest` 模型

新增两个字段：

```python
class PPTRequest(BaseModel):
    query: str = Field(..., description="PPT")
    slides: int = Field(15, description="")
    style: str = Field("business", description=": business/creative/minimal/educational")
    theme: str = Field("corporate-blue", description="")
    depth: str = Field("medium", description=": surface/medium/deep")           # 新增
    speech_notes: Optional[str] = Field("", description="演说稿说明")           # 新增
    user_document: Optional[Dict[str, Any]] = Field(None, description="...")
```

**`src/api.py`** — `create_ppt_task` 接口

`context.ppt_config` 中新增 `depth` 和 `speech_notes`：

```python
context = {
    'output_type': 'ppt',
    'ppt_config': {
        'slides': request.slides,
        'style': request.style,
        'theme': request.theme,
        'depth': request.depth,             # 新增
        'speech_notes': request.speech_notes,  # 新增
    },
    'user_document': request.user_document
}
```

#### 修改效果

| 字段 | 修复前 | 修复后 |
|------|--------|--------|
| depth（深度） | ❌ 未传递 | ✅ 正确传递 |
| speech_notes（演说稿说明） | ❌ 未传递 | ✅ 正确传递 |
| 文件上传（user_document） | ⚠️ 未处理 | ✅ 正确处理 |

---

## 二、Prompt 完善

### 2.0 Prompts 目录主要问题

#### 问题概述

经审查，`prompts/` 目录中的 YAML prompt 文件存在以下核心问题：

**1. Prompt 文件与实际代码严重脱节**

代码中大量 agent 根本没有使用 `prompts/` 目录下的 YAML 文件，而是在 Python 代码里写死了极简的 placeholder 提示词，导致 YAML 中编写的详细提示词从未被 LLM 看到。

| Agent | YAML 文件 | 实际使用 |
|-------|----------|---------|
| `query_optimizer.py` | ✅ 有 | ❌ 代码里只有 5 行 placeholder |
| `content_synthesizer.py` | ✅ 有 | ❌ 代码里只有 5 行 placeholder |
| `report_generator.py` | ✅ 有 | ⚠️ 部分使用，有 fallback |
| `content_evaluator.py` | ✅ 有 | ⚠️ 部分使用，有 fallback |
| `ppt/outline_generator.py` | ❌ 无 | ⚠️ 代码里硬编码了简化提示词 |

**2. 缺失的 Prompt 文件**

| 功能 | 状态 |
|------|------|
| 小说生成 (Fiction) | ❌ 完全缺失 |
| PPT 大纲生成 | ❌ 无对应 YAML |
| PPT 页面生成 | ❌ 完全缺失 |
| 报告章节写作 (SectionWriter) | ❌ 完全缺失（代码里写死） |
| 数据分析 Agent | ❌ 完全缺失 |

**3. YAML 文件质量问题**

- 模板变量（`{{ variable }}`）调用时未填充，导致渲染失败
- 各报告类型 YAML 结构高度重复，未抽象复用
- 输出格式定义不统一（有的要求 JSON，有的要求纯文本）
- Content Evaluator 的评分标准与代码实现不一致

**4. 改进方向**

- 优先级 1：修复 agent 代码，让其正确加载并使用 YAML prompt
- 优先级 2：补充缺失的 prompt 文件（小说、PPT、章节写作等）
- 优先级 3：统一所有 prompt 的结构格式和输出规范

---

### 2.1 Agent 代码修复：正确加载 YAML Prompt

#### 问题背景

原有的 agent 代码虽然调用了 `prompt_manager.get_prompt()`，但：
1. 没有传入 YAML 中的模板变量（如 `{{ user_query }}`），导致渲染可能不完整
2. user prompt 部分过于简陋，只有几行 placeholder，没有充分利用 YAML 中的详细指导
3. JSON 解析失败时的 fallback 处理不够健壮

#### 修改文件

**`src/agents/query_optimizer.py`**

- 重写 `process()` 方法的 user prompt，构建详细的查询优化指令
- 调用 `get_prompt()` 时传入 `optimization_task`、`user_query`、`query_context`、`search_engine` 等参数
- JSON 解析增加正则提取 fallback
- 补充默认值，确保错误时返回合理的 fallback 数据

**`src/agents/content_synthesizer.py`**

- 重写 `process()` 方法的 user prompt，构建详细的综合报告指令
- 调用 `get_prompt()` 时传入 `synthesis_task`、`target_audience`、`report_type` 等参数
- JSON 解析增加正则提取 fallback
- 修复 `synthesize_subtask()` 方法，同样加载 YAML prompt 并传入参数
- 修复硬编码的时间戳 `2025-09-25`，改为 `datetime.now().isoformat()`

**`src/agents/content_evaluator.py`**

- 重写 `_build_evaluation_prompt()` 方法，充分利用 YAML 中的评分标准说明
- 调用 `get_prompt()` 时传入参数，YAML 中无变量时使用合理的 default 值
- JSON 解析增加更健壮的 fallback 逻辑
- 修复 `_fallback_parse()` 中的评分计算（使用 `min()` 防止超限）
- 修复中文关键字判断，增强 fallback 识别能力

#### 核心改进

```python
# 之前：调用 get_prompt() 不传参数
system_prompt = self.get_prompt("agents/query_optimizer/system")

# 之后：传入 YAML 中定义的模板变量
system_prompt = self.get_prompt(
    "agents/query_optimizer/system",
    optimization_task=f"优化搜索查询: {query}",
    user_query=query,
    query_context=query_context,
    search_engine="duckduckgo"
)
```

```python
# 之前：user prompt 只有几行 placeholder
user_prompt = f"""
: {query}

1.
2.
3.

JSON
"""

# 之后：构建详细的指令，充分利用 YAML 中的指导框架
user_prompt = f"""## 任务
请分析并优化以下搜索查询，生成高效的搜索策略。

## 原始查询
"{query}"

## 查询上下文
{query_context if query_context else "无特殊上下文"}

## 输出要求
请严格按照以下 JSON 格式输出...
```

#### 修改效果

| 问题 | 修复前 | 修复后 |
|------|--------|--------|
| YAML 模板变量 | ❌ 未传入，渲染不完整 | ✅ 传入所有变量 |
| User prompt 详细度 | ❌ 只有 5 行 placeholder | ✅ 包含完整的任务描述、评分标准、输出格式 |
| JSON 解析失败 | ❌ 可能返回不完整数据 | ✅ 正则提取 + 合理 fallback |
| 时间戳 | ❌ 硬编码 `2025-09-25` | ✅ `datetime.now().isoformat()` |
| 日志 | ❌ 中文乱码（TODO） | ✅ 完整中文描述 |

---

### 2.2 小说章节写作 Prompt（新增）

#### 问题背景

小说创作流程复用报告章节生成器（`SectionWriter`），LLM 收到的是报告类型的 prompt，导致：
- 章节内插入大量元数据（人物设定表、背景设定框）
- 人物设定、背景设定与正文混杂
- 第 1-2 章尤为严重

#### 解决方案

为小说创作流程新增专用的章节写作 prompt，与报告 prompt 完全隔离。

#### 修改文件

**`src/agents/coordinator.py`** — `_fiction_writer_node` 方法

向 `section_writer` 传递 fiction 专属参数：

```python
# 标记类型，使 section_writer 走 fiction prompt 路径
context["report_type"] = "fiction"
context["fiction_elements"] = fiction_elements
context["fiction_outline"] = fiction_outline

task = self.report_coordinator.section_writer.write_section(
    section=section_requirements,
    available_content=available_content,
    context=context  # 包含 fiction_elements 等信息
)
```

**`src/agents/report/section_writer.py`** — `_build_writing_prompt` 方法

在 `_build_writing_prompt` 入口增加 fiction 分支判断，并新增 `_build_fiction_writing_prompt` 方法：

```python
def _build_writing_prompt(self, section, relevant_content, context):
    report_type = context.get("report_type", "comprehensive") if context else "comprehensive"

    # fiction 走专用 prompt，与报告完全隔离
    if report_type == "fiction":
        return self._build_fiction_writing_prompt(section, context, relevant_content, word_count)

    # report 走原有 prompt（保持不变）
    ...

def _build_fiction_writing_prompt(self, section, context, relevant_content, word_count):
    """构建小说章节写作 prompt，与报告 prompt 完全隔离。"""
    # 从 context 中提取 fiction_elements（人物/时间/地点/情节/主题）
    fiction_elements = context.get("fiction_elements", {})
    characters = fiction_elements.get("characters", [])
    time_info = fiction_elements.get("time", {})
    place_info = fiction_elements.get("place", {})
    plot_info = fiction_elements.get("plot", {})
    theme_info = context.get("theme", {})

    prompt = f"""# 小说章节写作

## 本章信息
- 章节序号: {section_id}
- 章节标题: {title}
- 目标字数: 约 {word_count} 字（允许上下浮动20%）

## 故事设定（必须严格遵守）
### 时间背景
{time_info.get('period', '当代')} | {time_info.get('duration', '')}

### 主要场景
{place_info.get('main_location', '')}: {place_info.get('description', '')}

### 登场人物
{chr(10).join(character_profiles)}

### 核心主题
{theme_info.get('core_theme', '')}
情感基调: {theme_info.get('tone', '')}

### 情节走向
{plot_info.get('core_conflict', '')}
起点事件: {plot_info.get('inciting_incident', '')}
转折点: {', '.join(plot_info.get('turning_points', []))}
高潮: {plot_info.get('climax', '')}
结局: {plot_info.get('resolution', '')}

## 章节衔接
{"上一章: " + prev_title if prev_title else ""}
{"上一章梗概: " + prev_summary if prev_summary else ""}

## 写作指令
1. **纯小说文体**：直接开始叙事，不要插入任何元数据表格、人物设定框、背景说明等。
2. **禁止**：不要输出 Markdown 表格、`## 人物设定`、`## 背景设定`、`**角色**` 等非故事内容。
3. **字数**：确保本章内容达到约 {word_count} 字。
4. **衔接自然**：本章开头需与上一章末尾形成情绪或事件上的承接。
5. **仅输出正文**：只输出本章的故事情节，不要有任何前言、后记、总结。

直接开始写：
"""
    return prompt
```

#### 设计原则

| 原则 | 说明 |
|------|------|
| **隔离报告指令** | 小说和报告用完全不同的 prompt，避免 LLM 混淆格式要求 |
| **提供完整世界观** | 传入 `fiction_elements`（人物/时间/地点/情节/主题），LLM 不需自行创作设定 |
| **强制叙事文体** | 明确禁止输出元数据表格、人物设定框、背景说明等非故事内容 |
| **衔接上下文** | 传入上一章标题和梗概，保证章节之间情节连贯 |
| **字数控制** | 要求约 `word_count` 字，允许 20% 浮动 |
| **禁止前言后记** | 只输出正文，禁止前言、后记、总结 |

---

## 三、修改文件清单

| 文件路径 | 修改类型 | 主要内容 |
|---------|---------|---------|
| `src/searcher/duckduckgo.py` | 修改 | 新增 `search_with_httpx()` 使用 DuckDuckGo HTML 端点 |
| `src/tools/web_searcher.py` | 修改 | 移除 Playwright 调用，新增 httpx 搜索和 `_fetch_full_content_with_httpx()` |
| `src/agents/coordinator.py` | 修改 | 返回值补上 `output_dir`；`_fiction_writer_node` 传递 `fiction_elements` 和 `report_type="fiction"` |
| `src/api.py` | 修改 | 根路由 `/` 返回 `index.html`；`/static/` 挂载静态文件；TaskWorker 注册到 startup 事件；下载接口重写（支持 PPT ZIP 打包）；result 接口返回 `output_dir` |
| `src/llm/client.py` | 修改 | response=None 判空、429/超时归类为可重试、不打印 ERROR |
| `src/agents/ppt/page_agent.py` | 修改 | Semaphore(4) 并发控制、指数退避重试（3s→6s→12s） |
| `src/tools/image_downloader.py` | 修改 | URL 无效性检查，跳过无效 URL |
| `src/api.py` | 修改 | 根路由 `/` 返回 `index.html`；`/static/` 挂载静态文件；TaskWorker 注册到 startup 事件；下载接口重写（支持 PPT ZIP 打包）；result 接口返回 `output_dir`；`PPTRequest` 新增 `depth`、`speech_notes` 字段 |
| `src/agents/query_optimizer.py` | 修改 | 重写 user prompt，正确传入 YAML 模板变量，增强 JSON 解析 |
| `src/agents/content_synthesizer.py` | 修改 | 重写 user prompt，正确传入 YAML 模板变量，修复 `synthesize_subtask()` |
| `src/agents/content_evaluator.py` | 修改 | 重写 `_build_evaluation_prompt()`，充分利用 YAML 评分标准 |
| `frontend-static/index.html` | 修改 | API_BASE 硬编码为 `http://localhost:8000`；下载按钮动态文案（PPT 任务显示"下载 PPT"）；PPT `submit()` 补充 `depth`/`speech_notes` 字段 |
| `frontend/src/components/Sidebar.jsx` | 修改 | activeClass 添加文字颜色（如 `text-blue-900`） |
| `run_api.py` | 修改 | `logger.remove()` + level=INFO，屏蔽 DEBUG 日志 |

---

## 四、验证方法

```bash
# 1. 启动后端（只需这一条命令，前端已集成到 API 中）
python run_api.py

# 2. 打开浏览器访问 http://localhost:8000
#    确认前端页面正常显示（无需单独启动 http.server）

# 3. 测试搜索功能
#    - 观察日志中搜索请求是否走 httpx（而非 Playwright）
#    - 确认返回了真实搜索结果（而非 0 条）

# 4. 测试 PPT 生成
#    - 429 限流时出现 "限流，Xs后重试" WARNING（而非 ERROR）
#    - 不再出现 "'NoneType' object has no attribute 'get'" 错误
#    - 下载按钮显示"下载 PPT"（而非"下载 HTML"）

# 5. 测试小说生成
#    - 每章正文干净，无 "## 人物设定"、"## 背景设定" 等元数据框
#    - 章节之间情节衔接自然

# 6. 测试下载
#    - 点击"下载 HTML"/"下载 Markdown"不再返回 404，正常触发浏览器下载
#    - PPT 任务下载得到的是 .zip 压缩包
```
