# HTML转换系统快速开始

## 🚀 5分钟快速上手

### 安装依赖

```bash
pip install markdown
# 或者重新安装所有依赖
pip install -r requirements.txt
```

### 基础用法

#### 1. 文档转换（报告、论文）

```python
from src.agents.html import DocumentHTMLAgent

agent = DocumentHTMLAgent()
html = agent.convert_to_html(
    content="""
# 研究报告

## 摘要
这是研究摘要...

## 1. 引言
这是引言部分...
""",
    metadata={'title': '研究报告', 'author': '张三'},
    template='academic',  # 学术风格
    theme='light',
    output_path='output/report.html'
)
```

#### 2. 小说转换

```python
from src.agents.html import FictionHTMLAgent

agent = FictionHTMLAgent()
html = agent.convert_to_html(
    content="""
# 推理小说

## 第一章 开始
故事从这里开始...

## 第二章 转折
意外发生了...
""",
    metadata={'title': '推理小说', 'author': '李四'},
    template='novel',  # 小说模板
    theme='sepia',     # 复古主题，适合阅读
    output_path='output/novel.html'
)
```

#### 3. PPT转换

```python
from src.agents.html import PPTHTMLAgent

agent = PPTHTMLAgent(framework='reveal')  # 使用Reveal.js
html = agent.convert_to_html(
    content="""
# AI的未来

---

## 什么是AI？

人工智能的定义...

---

## 应用领域

- 医疗
- 金融
- 教育
""",
    metadata={'title': 'AI的未来', 'author': '王五'},
    template='default',
    theme='sky',  # Reveal.js主题
    output_path='output/presentation.html'
)
```

## 📚 运行示例

### 完整示例

```bash
python xunlong.py --help
```

这将生成3个示例文件：
- `output/document_example.html` - 文档示例
- `output/fiction_example.html` - 小说示例
- `output/ppt_example.html` - PPT示例

### 测试

```bash
python tests/test_html_conversion.py
```

## 🎨 模板和主题

### 查看可用模板

```python
from src.agents.html import get_template_registry

registry = get_template_registry()

# 文档模板
print(registry.list_templates('document'))
# 输出: [academic, technical, ...]

# 小说模板
print(registry.list_templates('fiction'))
# 输出: [novel, ebook, ...]

# PPT模板
print(registry.list_templates('ppt'))
# 输出: [default, business, ...]
```

### 可用主题

#### 文档/小说主题
- `light` - 浅色（白天阅读）
- `dark` - 深色（夜间阅读）
- `sepia` - 复古（长时间阅读）

#### PPT主题（Reveal.js）
- `white`, `black` - 简洁黑白
- `league`, `sky`, `beige` - 彩色主题
- `night`, `serif`, `simple` - 专业主题
- `blood`, `moon`, `solarized` - 特色主题

## 💡 常见场景

### 场景1：将XunLong生成的报告转为HTML

```python
from src.deep_search_agent import DeepSearchAgent
from src.agents.html import DocumentHTMLAgent

# 1. 生成报告
search_agent = DeepSearchAgent()
result = await search_agent.search("AI在医疗领域的应用")

# 2. 读取报告
report_path = result['project_dir'] / 'reports' / 'FINAL_REPORT.md'
report_content = report_path.read_text()

# 3. 转换为HTML
html_agent = DocumentHTMLAgent()
html = html_agent.convert_to_html(
    content=report_content,
    template='academic',
    output_path=result['project_dir'] / 'reports' / 'FINAL_REPORT.html'
)
```

### 场景2：将AI生成的小说转为HTML

```python
from src.agents.fiction.fiction_outline_generator import FictionOutlineGenerator
from src.agents.html import FictionHTMLAgent

# 1. 生成小说
# ... 小说生成代码 ...

# 2. 转换为HTML
html_agent = FictionHTMLAgent()
html = html_agent.convert_to_html(
    content=novel_content,
    metadata={
        'title': '密室谜案',
        'author': 'AI作家',
        'genre': '推理小说'
    },
    template='novel',
    theme='sepia',
    output_path='output/mystery_novel.html'
)
```

### 场景3：创建演示文稿

```python
from src.agents.html import PPTHTMLAgent

agent = PPTHTMLAgent(framework='reveal')

# 内容使用 --- 分隔幻灯片
content = """
# 市场分析报告

---

## 市场现状

- 市场规模：XXX亿
- 增长率：XX%
- 主要玩家：A, B, C

---

## 趋势预测

![趋势图](trend.png)

---

## 结论

总结要点...
"""

html = agent.convert_to_html(
    content=content,
    template='business',
    theme='white',
    output_path='output/market_analysis.html'
)
```

## 🔧 集成到CLI

可以在 `xunlong.py` 中添加HTML转换命令：

```python
@app.command()
def to_html(
    input_file: str,
    output_file: str = "output.html",
    type: str = "document",  # document, fiction, ppt
    template: str = None,
    theme: str = None
):
    """将Markdown文件转换为HTML"""
    from src.agents.html import DocumentHTMLAgent, FictionHTMLAgent, PPTHTMLAgent

    # 读取输入文件
    content = Path(input_file).read_text()

    # 选择Agent
    if type == "document":
        agent = DocumentHTMLAgent()
    elif type == "fiction":
        agent = FictionHTMLAgent()
    elif type == "ppt":
        agent = PPTHTMLAgent()

    # 转换
    html = agent.convert_to_html(
        content=content,
        template=template,
        theme=theme,
        output_path=output_file
    )

    print(f"✅ 已转换为HTML: {output_file}")
```

使用：

```bash
python xunlong.py to-html report.md --output report.html --type document --template academic
```

## 📖 更多资源

- [完整使用指南](HTML_CONVERSION_GUIDE.md)
- [实现文档](HTML_CONVERSION_IMPLEMENTATION.md)
- 当前精简版已移除 `examples/` 示例目录；请使用 `python xunlong.py ...` 或 `python run_api.py`。

## 🐛 故障排除

### 问题1: ModuleNotFoundError

```bash
# 确保在项目根目录运行
cd /path/to/XunLong
python xunlong.py --help
```

### 问题2: markdown库未安装

```bash
pip install markdown
```

### 问题3: 模板未找到

```python
# 检查模板目录
ls templates/html/document/
ls templates/html/fiction/
ls templates/html/ppt/
```

### 问题4: 中文乱码

确保：
1. 输入文件使用UTF-8编码
2. 在浏览器中查看（自动处理编码）

---

**享受HTML转换功能！** 🎉
