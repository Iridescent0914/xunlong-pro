# `analyze` 命令用法说明

> 金融数据分析模式的 CLI 入口。执行 **网页搜索 → 结构化金融分析**，并可选择生成 **综合分析报告**、**演示 PPT** 或 **仅输出分析结果**。

---

## 1. 基本用法

```bash
python xunlong.py analyze "你的分析主题"
```

等价于：

```bash
python xunlong.py analyze "你的分析主题" --deliverable report
```

**示例：**

```bash
python xunlong.py analyze "分析2024至2026年华为公司营收趋势"
python xunlong.py analyze "分析2024年银行业营收趋势" --depth deep -v
python xunlong.py analyze "测试分析" --mock-search -v
```

---

## 2. 产出物：`--deliverable` / `-D`

| 取值 | 说明 |
|------|------|
| `report`（**默认**） | 执行金融分析 + 生成综合分析报告（HTML 或 Markdown） |
| `ppt` | 执行金融分析 + 生成多页 HTML 演示文稿 |
| `none` | **仅**执行金融分析，不生成报告或 PPT |

```bash
# 默认：分析报告
python xunlong.py analyze "分析华为营收"

# 生成 PPT
python xunlong.py analyze "分析华为营收" --deliverable ppt

# 只要分析 JSON，不要报告/PPT
python xunlong.py analyze "分析华为营收" --deliverable none
```

**工作流说明：**

- 三种模式下都会跑 **搜索** 和 **金融数据分析**。
- `report`：分析完成后继续生成正文报告，并在报告中插入独立章节「金融数据分析」。
- `ppt`：分析完成后生成 PPT；若分析成功，会在 **结论页之前** 自动插入 2–3 页分析幻灯片（分析结果 / 图表 / 分析来源）。
- `none`：分析完成后结束，适合只要结构化数据、自行对接下游的场景。

---

## 3. 全部参数

### 3.1 通用参数

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | — | （必填） | 分析主题，如「分析2024年华为公司营收趋势」 |
| `--deliverable` | `-D` | `report` | 产出物：`report` / `ppt` / `none` |
| `--depth` | `-d` | `deep` | 搜索深度：`surface` / `medium` / `deep` |
| `--max-results` | `-m` | `20` | 最大网页搜索结果条数 |
| `--input-file` | — | — | 补充参考文档（`.txt` / `.pdf` / `.docx`） |
| `--mock-search` | — | 关闭 | 使用 `fixtures/mock_search.json` 代替真实搜索（离线联调） |
| `--verbose` | `-v` | 关闭 | 打印详细日志与配置 |

### 3.2 仅 `--deliverable report` 时有效

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--output-format` | `-o` | `html` | 报告格式：`html` / `md` |
| `--html-template` | — | `enhanced_professional` | HTML 模板名称 |
| `--html-theme` | — | `light` | HTML 主题：`light` / `dark` |

### 3.3 仅 `--deliverable ppt` 时有效

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--ppt-style` | `-s` | `business` | PPT 风格：`ted` / `business` / `academic` / `creative` / `simple` |
| `--slides` | `-n` | `10` | 目标幻灯片页数（不含后续插入的分析页） |
| `--ppt-theme` | — | `default` | PPT 配色主题 |

---

## 4. 常用命令示例

### 4.1 生成 HTML 分析报告（默认）

```bash
python xunlong.py analyze "分析2024年银行业营收趋势" -v
python xunlong.py analyze "分析华为营收" --deliverable report -o html
python xunlong.py analyze "分析华为营收" -o md
```

### 4.2 生成 PPT

```bash
python xunlong.py analyze "分析华为营收" --deliverable ppt
python xunlong.py analyze "分析华为营收" -D ppt -s business -n 12 -v
python xunlong.py analyze "分析华为营收" -D ppt --ppt-theme blue
```

### 4.3 仅金融分析

```bash
python xunlong.py analyze "分析华为营收" --deliverable none -v
```

### 4.4 离线测试（Mock 搜索）

```bash
python xunlong.py analyze "分析2024年银行业营收趋势" --mock-search -v
python xunlong.py analyze "测试" --mock-search --deliverable none
```

---

## 5. 输出文件位置

运行成功后，结果保存在 `storage/{时间戳}_{查询摘要}/` 目录下。

| 路径 | 说明 | 何时生成 |
|------|------|----------|
| `intermediate/02_search_results.json` | 网页搜索结果 | 始终 |
| `intermediate/03_data_analysis.json` | 金融数据分析结构化结果 | 分析未跳过时 |
| `reports/FINAL_REPORT.html` | HTML 综合分析报告 | `--deliverable report` 且 `-o html` |
| `reports/FINAL_REPORT.md` | Markdown 报告 | `--deliverable report` 且 `-o md` |
| `ppt/index.html` | PPT 导航页 | `--deliverable ppt` |
| `ppt/presenter.html` | PPT 演示模式 | `--deliverable ppt` |
| `ppt/slides/slide_XX_*.html` | 各页幻灯片 | `--deliverable ppt` |

终端结束时会打印 **项目目录**、**报告/PPT 路径** 以及 **分析状态**（`success` / `skipped` / `failed`）。

---

## 6. 金融分析模块内容

无论产出物是 report 还是 ppt，分析模块均包含以下结构（与 LLM 正文分离，数值由分析智能体确定性生成）：

| 模块 | 内容 |
|------|------|
| **分析结果** | 结构化数据表 + 结论 |
| **分析图表** | 由表格自动生成的 ECharts 图表 |
| **分析来源** | 仅列出表格「来源」列中出现的 `[N]` 引用，**不含摘要** |

- **报告模式**：以上内容写入 `FINAL_REPORT` 的独立章节「金融数据分析」。
- **PPT 模式**：在结论页前插入对应幻灯片（分析结果页、图表页、分析来源页）。

若搜索无结果或分析被跳过（`status: skipped`），则不会插入分析章节/幻灯片。

---

## 7. 与 `search` 命令的区别

| | `analyze` | `search` |
|--|-----------|----------|
| 核心能力 | 金融结构化分析 + 可选报告/PPT | 通用深度搜索 + 报告 |
| 分析模块 | 必有（成功时） | 无独立金融分析章节 |
| 典型场景 | 营收趋势、财务指标、行业数据 | 综合调研、行业综述 |

---

## 8. 常见问题

**Q：分析状态为 `skipped`？**  
通常因网页搜索返回 0 条结果（网络/代理问题）或结果与查询不相关。可先用 `--mock-search -v` 验证流程，或检查搜索配置。

**Q：报告/PPT 有了，但没有分析章节？**  
查看 `intermediate/03_data_analysis.json` 中 `status` 是否为 `success`；只有成功时才会插入分析模块。

**Q：只想快速看分析 JSON？**  
使用 `--deliverable none -v`，完成后打开 `intermediate/03_data_analysis.json`。

**Q：PPT 页数比 `--slides` 多？**  
分析成功时会额外插入 2–3 页「金融数据分析」幻灯片，总页数 = 原大纲页数 + 分析页。

---

## 9. 相关文档

- 架构与数据流：[`金融数据分析流程_lly.md`](./金融数据分析流程_lly.md)
- 项目 README：[`README_CN.md`](../README_CN.md)

---

*文档版本：v1 — 含 `--deliverable report/ppt/none` 与 PPT 分析模块插入说明。*
