# 📸 图片功能使用指南

XunLong 现已支持在生成的文档中自动插入高质量配图，让你的报告更加生动专业！

## ✨ 功能特性

### 双重图片来源

1. **网页爬取图片** - 从搜索结果页面自动提取相关图片
2. **专业图片API** - 使用 Unsplash/Pexels 获取高质量配图

### 智能图片处理

- ✅ 自动下载并保存到本地
- ✅ 图片优化（压缩、尺寸调整）
- ✅ 智能插入（基于内容相关性）
- ✅ 支持多种插入模式
- ✅ 自动添加图片元数据（摄影师、来源等）

## 🚀 快速开始

### 1. 配置 API 密钥

#### 方式一：使用 Unsplash（推荐）

**免费额度**: 5000次/小时

**获取步骤**:
1. 访问 [Unsplash Developers](https://unsplash.com/developers)
2. 注册并登录
3. 点击 "New Application"
4. 填写应用信息并同意条款
5. 获取 **Access Key**

**配置到 `.env`**:
```bash
UNSPLASH_ACCESS_KEY=your_access_key_here
```

#### 方式二：使用 Pexels

**免费额度**: 无限制

**获取步骤**:
1. 访问 [Pexels API](https://www.pexels.com/api/)
2. 注册并登录
3. 生成 API Key

**配置到 `.env`**:
```bash
PEXELS_API_KEY=your_api_key_here
```

### 2. 启用图片功能

在 `.env` 文件中配置:

```bash
# 启用文档配图
ENABLE_DOCUMENT_IMAGES=true

# 每个章节的配图数量
IMAGES_PER_SECTION=2

# 图片插入模式: smart, top, bottom, distribute, none
IMAGE_INSERT_MODE=smart
```

### 3. 运行测试

```bash
# 测试图片功能
# examples/ 已移除；请通过 python run_api.py 启动后使用前端或 API 验证图片功能
```

测试将验证:
- ✅ 图片搜索
- ✅ 图片下载
- ✅ 图片插入
- ✅ 批量处理

### 4. 生成带配图的报告

```bash
# 生成报告（自动包含配图）
python xunlong.py report "人工智能技术发展趋势" --verbose
```

## 📖 图片插入模式

### `smart` - 智能插入（推荐）

基于内容相关性自动判断插入位置：
- 分析图片 `alt` 文本与段落内容的相关性
- 在相关段落后插入对应图片
- 剩余图片放在文末附录

**适用场景**: 大部分情况

**示例效果**:
```markdown
## 机器学习基础

机器学习是人工智能的核心技术...

![机器学习算法](images/ml_algorithm.jpg)
*尺寸: 1200x800 | 摄影师: John Doe | 来源: unsplash*

## 深度学习网络

深度学习使用多层神经网络...
```

### `top` - 开头插入

所有图片集中放在文档开头：

**适用场景**:
- 封面图展示
- 图片预览

### `bottom` - 末尾插入（附录模式）

所有图片作为附录放在文档末尾：

**适用场景**:
- 正式报告
- 学术论文

### `distribute` - 均匀分布

图片在段落间均匀分布：

**适用场景**:
- 图片较多
- 需要视觉平衡

### `none` - 不插入

仅下载但不插入到文档中：

**适用场景**:
- 仅需收集图片
- 手动调整位置

## 🛠️ 高级配置

### 自定义图片下载器

```python
from src.tools.image_downloader import ImageDownloader

downloader = ImageDownloader(
    storage_dir=Path("my_images"),
    max_image_size=2048,  # 最大尺寸（像素）
    quality=85,            # JPEG质量 (1-100)
    max_concurrent_downloads=10  # 并发下载数
)
```

### 自定义图片搜索

```python
from src.tools.image_searcher import ImageSearcher

searcher = ImageSearcher(
    prefer_source="unsplash",  # 或 "pexels"
)

# 搜索指定方向的图片
images = await searcher.search_images(
    query="technology",
    count=5,
    orientation="landscape"  # landscape, portrait, squarish
)
```

### 在代码中启用/禁用

```python
from src.agents.report import ReportCoordinator

coordinator = ReportCoordinator(
    llm_manager=llm_manager,
    prompt_manager=prompt_manager,
    enable_images=True  # 启用图片
)
```

## 📂 文件结构

生成的报告项目结构:

```
storage/
└── 20251007_123456_ProjectName/
    ├── metadata.json
    ├── reports/
    │   ├── FINAL_REPORT.md      # 包含图片的完整报告
    │   └── FINAL_REPORT.html
    └── images/                   # 下载的图片
        ├── abc123.jpg
        ├── def456.jpg
        └── ...
```

## 💡 最佳实践

### 1. API 密钥管理

- ⚠️ **不要**将 API 密钥提交到版本控制
- ✅ 使用 `.env` 文件存储密钥
- ✅ `.env.example` 作为模板

### 2. 图片版权

- Unsplash: 可免费商用，建议注明摄影师
- Pexels: 可免费商用，无需署名
- 网页爬取: 注意版权，仅供研究使用

### 3. 性能优化

- 合理设置 `IMAGES_PER_SECTION`（推荐 2-3张）
- 启用图片优化（自动压缩）
- 使用本地缓存避免重复下载

### 4. 降级策略

如果未配置图片 API：
1. 系统自动降级到网页爬取模式
2. 仍可从搜索结果页面提取图片
3. 部分功能受限但不影响核心流程

## 🔧 故障排查

### 问题1: 图片搜索失败

**症状**: 日志显示 "未配置任何图片API密钥"

**解决**:
```bash
# 检查 .env 文件
cat .env | grep UNSPLASH
cat .env | grep PEXELS

# 确保至少配置一个
```

### 问题2: 图片下载失败

**症状**: 图片 URL 无法访问

**解决**:
- 检查网络连接
- 确认防火墙设置
- 尝试使用代理

### 问题3: 图片未显示在报告中

**可能原因**:
1. `IMAGE_INSERT_MODE=none` - 改为其他模式
2. `ENABLE_DOCUMENT_IMAGES=false` - 改为 `true`
3. 图片搜索返回空结果 - 检查搜索关键词

### 问题4: 图片过大

**解决**:
```python
# 调整最大尺寸和质量
downloader = ImageDownloader(
    max_image_size=1024,  # 降低尺寸
    quality=70            # 降低质量
)
```

## 📊 API 用量监控

### Unsplash

- 免费额度: 5000次/小时
- 查看用量: [Dashboard](https://unsplash.com/oauth/applications)

### Pexels

- 无限免费
- 无需监控

## 🎯 示例代码

### 完整示例：生成带配图的报告

```python
import asyncio
from src.agents.report import ReportCoordinator
from src.llm import LLMManager, PromptManager

async def generate_report_with_images():
    # 初始化
    llm_manager = LLMManager()
    prompt_manager = PromptManager()

    # 创建协调器（启用图片）
    coordinator = ReportCoordinator(
        llm_manager=llm_manager,
        prompt_manager=prompt_manager,
        enable_images=True
    )

    # 生成报告
    result = await coordinator.generate_report(
        query="人工智能技术应用",
        search_results=[],  # 你的搜索结果
        report_type="comprehensive"
    )

    print(f"报告已生成: {result['report']['title']}")

asyncio.run(generate_report_with_images())
```

## 🚧 未来规划

- [ ] 支持更多图片源（Getty Images, Pixabay）
- [ ] AI 生成图片（DALL-E 3, Stable Diffusion）
- [ ] 图片智能裁剪和美化
- [ ] 图片去重和质量评分
- [ ] 自动生成图表和数据可视化

## 📞 获取帮助

遇到问题？

- 📖 查看 [完整文档](https://jaguarliuu.github.io/xunlong/)
- 🐛 提交 [Issue](https://github.com/jaguarliuu/xunlong/issues)
- 💬 加入社区讨论

---

**Happy Creating! 🎨**
