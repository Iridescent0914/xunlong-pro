## 完整数据处理工作流程指南

### 工作流程概览

完整的处理流程包含以下 6 个步骤：

```
1. 读取 parquet
   ↓
2. 筛选文本字段 (过滤无效记录)
   ↓
3. 清洗文本 (去除特殊字符、多余空格等)
   ↓
4. 生成标准 Document (统一格式的 Document 对象)
   ↓
5. 切块 (超长文本进行滑动窗口分割)
   ↓
6. 保存 processed documents (JSON/Pickle/CSV 多种格式)
```

### 文件结构

```
financeRAG/
├── data_loader.py          # 读取和筛选数据（步骤 1-2）
├── cleaner.py              # 清洗文本（步骤 3）
├── document_schema.py      # Document 数据结构（步骤 4）
├── chunker.py              # 文本切块（步骤 5）
├── process_pipeline.py     # 完整处理管道（所有步骤 + 保存）
├── workflow_test.py        # 工作流程测试脚本
└── data/
    ├── stock_earning_call_transcripts.parquet
    └── stock_news.parquet
```

### 问题解决：pyarrow 导入错误

**问题原因**: 使用不同 Python 解释器导致包安装位置不一致

**解决方案**:

#### 方案 1: 使用系统 Python 环境
```bash
# 安装依赖到系统环境
pip install pyarrow pandas

# 运行脚本
python financeRAG/workflow_test.py
```

#### 方案 2: 使用指定 Python 解释器
```bash
# 使用 Python 3.12 来安装依赖
D:/py3.12/python.exe -m pip install --user pyarrow pandas

# 运行脚本
D:/py3.12/python.exe financeRAG/workflow_test.py
```

#### 方案 3: 创建虚拟环境（推荐）
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境（Windows）
venv\Scripts\activate

# 安装依赖
pip install pyarrow pandas

# 运行脚本
python financeRAG/workflow_test.py
```

### 快速开始

1. **安装依赖**
   ```bash
   pip install pyarrow pandas
   ```

2. **运行工作流程**
   ```bash
   python financeRAG/workflow_test.py
   ```

3. **查看处理结果**
   ```bash
   processed_data/
   ├── processed_documents.json          # 所有文档的 JSON 格式
   ├── processed_documents.pkl           # Python pickle 格式（推荐用于后续处理）
   ├── processed_documents_summary.csv   # 文档摘要 CSV 格式
   └── statistics.json                   # 处理统计信息
   ```

### 使用处理后的数据

#### 加载处理后的文档
```python
from financeRAG.process_pipeline import load_documents_pickle, load_documents_json

# 方式 1: 加载 Pickle（推荐，保留完整 Document 对象）
docs = load_documents_pickle('processed_data/processed_documents.pkl')

# 方式 2: 加载 JSON
docs = load_documents_json('processed_data/processed_documents.json')

# 使用文档
for doc in docs:
    print(f"文档 ID: {doc.chunk_id}")
    print(f"来源: {doc.source_type}")
    print(f"干净文本: {doc.clean_text[:100]}...")
    print(f"元数据: {doc.metadata}")
```

### 配置参数

#### 在 `process_pipeline.py` 中调整

```python
# 调整切块大小和重叠
chunked_docs = chunk_documents(
    doc_list,
    chunk_size=500,  # 块大小（字符数）
    overlap=80       # 相邻块的重叠（字符数）
)
```

### 输出统计信息示例

`statistics.json` 包含以下信息：
```json
{
  "total_documents": 15234,
  "original_documents": 10567,
  "chunked_documents": 15234,
  "by_source": {
    "earning_call": 8900,
    "stock_news": 6334
  },
  "text_stats": {
    "avg_raw_text_len": 450.5,
    "avg_clean_text_len": 380.2,
    "min_clean_text_len": 20,
    "max_clean_text_len": 5000
  }
}
```

### 调试提示

1. **查看详细日志**：在 `workflow_test.py` 中运行时，会打印每一步的详细信息

2. **检查特定文档**：
   ```python
   import json
   with open('processed_data/processed_documents.json') as f:
       docs = json.load(f)
   print(f"总文档数: {len(docs)}")
   print(f"第一个文档: {docs[0]}")
   ```

3. **验证文本清洗质量**：
   ```bash
   # 查看 CSV 摘要
   cat processed_data/processed_documents_summary.csv | head -20
   ```

### 常见问题

**Q: 为什么有些文档被过滤了？**  
A: 以下文档会被过滤：
- 原始文本为空或 None
- 清洗后文本长度 < 20 字符（见 `cleaner.py`）
- 元数据缺失

**Q: 如何处理超大型 parquet 文件？**  
A: `data_loader.py` 已经使用了分批读取（按 row groups）来处理大文件

**Q: 切块大小应该设置多少？**  
A: 推荐值根据应用场景：
- 向量数据库检索：500-1000 字符
- 摘要生成：200-400 字符
- 完整上下文理解：1000-2000 字符

---

**下一步**: 按照"快速开始"步骤运行工作流程！
