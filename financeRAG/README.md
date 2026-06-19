# FinanceRAG 数据处理模块

## 📁 目录结构

```
financeRAG/
├── data/                          # 原始数据 (parquet 文件)
│   ├── stock_news.parquet
│   ├── stock_earning_call_transcripts.parquet
│   └── ...
├── processor/                     # 核心处理模块
│   ├── __init__.py
│   ├── models.py                  # 数据模型
│   ├── reader.py                  # 数据读取器
│   ├── cleaner.py                 # 文本清洗
│   ├── chunker.py                 # 文本切块
│   └── pipeline.py                # 处理流程
├── scripts/                       # 可执行脚本
│   ├── process_finance_data.py    # 完整处理脚本
│   └── quick_start.py             # 快速测试脚本
├── tests/                         # 测试模块
│   └── test_processor.py          # 单元测试
└── processed_data/                # 输出结果（自动生成）
    └── combined_documents.jsonl   # 最终输出文件
```

## 🚀 快速开始

### 1. 快速测试 (推荐)
仅处理前 1000 条新闻记录，用于验证环境：

```bash
cd financeRAG
python scripts/quick_start.py
```

### 2. 完整处理
处理所有数据集。需要耐心等待（取决于系统性能）：

```bash
cd financeRAG
python scripts/process_finance_data.py
```

### 3. 单元测试
测试各个模块功能：

```bash
cd financeRAG
python tests/test_processor.py
```

## 📊 处理流程

```
parquet 文件
    ↓
[1] ParquetReader: 流式读取 - 支持大文件, 显示进度条
    ↓
[2] TextCleaner.is_valid_text(): 筛选有效数据
    ↓
[3] TextCleaner.clean(): 清洗文本 - 去除HTML、URL、特殊字符
    ↓
[4] Document: 生成标准格式 - 包含元数据
    ↓
[5] TextChunker.chunk_text(): 切块 - 滑动窗口分割
    ↓
JSONL 文件 (每行一个 JSON 对象)
```

## 🔧 核心模块说明

### 1. **models.py** - 数据模型
- `DocumentMetadata`: 文档元数据
  - source: 数据来源 (stock_news 或 stock_earning_call)
  - symbol: 股票代码
  - title, publisher, report_date: 文档信息
  - original_index: 原始数据索引

- `Document`: 标准文档格式
  - doc_id: 唯一ID (MD5哈希)
  - content: 文本内容
  - metadata: 元数据
  - chunk_index: 切块索引
  - chunk_size, chunk_overlap: 切块配置

### 2. **reader.py** - 数据读取
- `StockNewsReader`: 处理股票新闻
  - 自动解析嵌套的 news JSON 字段
  - 组合标题和段落内容
  - 流式处理（内存使用恒定）

- `StockEarningCallReader`: 处理财报电话会议
  - 解析 transcripts 结构化字段
  - 组织发言人和内容
  - 添加财年/季度/日期头部

### 3. **cleaner.py** - 文本清洗
- 移除 HTML 标签: `<tag>` → ``
- 移除 HTML 实体: `&nbsp;` → ` `
- 移除 URL 和邮箱
- 清理多余空格/换行/制表符
- 移除零宽字符

使用示例：
```python
cleaner = TextCleaner()
cleaned = cleaner.clean(raw_text)  # 清洗文本
is_valid = TextCleaner.is_valid_text(text)  # 验证有效性
stats = TextCleaner.get_text_stats(text)  # 获取统计
```

### 4. **chunker.py** - 文本切块
两种切块方式：

**方式 1: 滑动窗口（推荐）**
```python
chunker = TextChunker(chunk_size=512, overlap=100)
chunks = chunker.chunk_text(long_text)
# 输出: [{'content': str, 'chunk_index': int, 'start_char': int, 'end_char': int}, ...]
```

**方式 2: 按句子**
```python
chunks = chunker.chunk_by_sentences(text, max_chars=1000)
# 尊重句子边界，块大小可变
```

### 5. **pipeline.py** - 主流程
`FinanceDataPipeline` 类：

```python
pipeline = FinanceDataPipeline(
    chunk_size=512,           # 块大小
    chunk_overlap=100,        # 块重叠
    output_dir="processed_data",  # 输出目录
    batch_size=100,           # 批处理大小
)

# 处理数据
documents = pipeline.process_stock_news(
    parquet_path="data/stock_news.parquet",
    max_records=None  # None = 全部
)

# 保存结果
save_stats = pipeline.save_documents_batch(
    documents=documents,
    output_file="output.jsonl"
)

# 获取统计
stats = pipeline.get_statistics()
```

## 📈 配置参数

### 块大小选择

| 场景 | chunk_size | overlap | 适用 |
|------|-----------|---------|------|
| 快速 | 256 | 50 | 测试、预处理 |
| 推荐 | 512 | 100 | 默认配置 |
| 质量优先 | 1024 | 200 | 长文档、精准搜索 |
| 中文优化 | 600 | 120 | 中文文本 |

### 批处理大小
- `batch_size=50`: 内存受限时使用
- `batch_size=100`: 平衡（推荐）
- `batch_size=500`: 处理速度优先

## 📝 输出文件格式

**文件**: `combined_documents.jsonl`

每行一个 JSON 对象（JSONL 格式）：

```json
{
  "doc_id": "a1b2c3d4e5f6g7h8",
  "content": "实际的文本内容...",
  "metadata": {
    "source": "stock_news",
    "symbol": "AAPL",
    "title": "Apple Earnings Report",
    "publisher": "Yahoo Finance",
    "report_date": "2024-01-15",
    "source_type": "STORY",
    "link": "https://...",
    "original_index": 42,
    "processed_at": "2024-01-20T10:30:00"
  },
  "chunk_index": 0,
  "chunk_size": 512,
  "chunk_overlap": 100
}
```

## 💡 使用示例

### 示例 1: 只处理新闻
```python
from financeRAG.processor.pipeline import FinanceDataPipeline

pipeline = FinanceDataPipeline()
documents = pipeline.process_stock_news("financeRAG/data/stock_news.parquet")
pipeline.save_documents_batch(documents, "output.jsonl")
```

### 示例 2: 自定义清洗规则
```python
from financeRAG.processor.cleaner import TextCleaner

cleaner = TextCleaner()
# 添加自定义规则
cleaner.rules.append((r'特定模式', '替换内容'))
cleaned = cleaner.clean(raw_text)
```

### 示例 3: 按句子切块
```python
from financeRAG.processor.chunker import TextChunker

chunker = TextChunker()
chunks = chunker.chunk_by_sentences(
    long_text,
    max_chars=800,
    sentence_endings='。！？.\\n'
)
```

### 示例 4: 只处理特定股票
```python
pipeline = FinanceDataPipeline()

for doc in pipeline.process_stock_news("stock_news.parquet"):
    if doc.metadata.symbol == "AAPL":
        print(f"处理 Apple 新闻: {doc.metadata.title}")
```

## ⚙️ 依赖库

- `pandas`: 数据处理
- `pydantic`: 数据验证模型
- `tqdm`: 进度条
- `loguru`: 彩色日志

安装：
```bash
pip install pandas pydantic tqdm loguru
```

## 🐛 常见问题

### Q: 内存不足？
**A:** 减小参数：
```python
pipeline = FinanceDataPipeline(
    chunk_size=256,      # 减小
    batch_size=50,       # 减小
    output_dir="output"
)
```

### Q: 处理速度慢？
**A:** 增大参数：
```python
pipeline = FinanceDataPipeline(
    chunk_size=1024,     # 增大
    batch_size=500,      # 增大
    output_dir="output"
)
```

### Q: 只处理部分数据？
**A:** 使用 `max_records` 参数：
```python
documents = pipeline.process_stock_news(
    parquet_path="stock_news.parquet",
    max_records=10000  # 只处理前 10000 条
)
```

### Q: 如何并行处理？
**A:** 当前不支持多进程（内存限制），但您可以：
1. 分别处理不同数据源
2. 分块处理数据 (设定 max_records)
3. 考虑使用 Spark/Dask 进行分布式处理

## 📊 性能参考

基于测试数据（stock_news.parquet, 101 万条, 0.8 GB）：

| 指标 | 值 |
|-----|-----|
| 处理速度 | ~10,000 条/分钟 |
| 内存使用 | ~300-500 MB |
| 平均有效率 | 95%+ |
| 平均切块数 | 2-3 个/记录 |
| 总处理时间 | ~100-150 分钟（全部数据） |

## 🎯 后续步骤

- [ ] 导入向量数据库 (Milvus/Weaviate)
- [ ] 建立搜索索引
- [ ] 进行 RAG 查询测试
- [ ] 集成 LLM 问答系统
- [ ] 建立监控和日志系统

## 📚 文档

完整详细文档请查看: [FINANCE_DATA_PROCESSOR_GUIDE.md](../docs/FINANCE_DATA_PROCESSOR_GUIDE.md)

---

**版本**: 1.0  
**最后更新**: 2024-01-20  
**维护**: FinanceRAG Team
