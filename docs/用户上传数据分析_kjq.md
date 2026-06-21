# 报告与前端展示更新说明（自动生成报告）

此文档说明在 `run_file_analysis.py` 客户端与报告渲染模块中，近期完成的前端/样式与可视化相关改进、使用方式与后续说明。

## 变更概览
- 移除客户端 PPT 导出逻辑（不再自动生成 PPT）。对应文件：[run_file_analysis.py](run_file_analysis.py)
- 大幅改进 HTML 报告样式与交互（美化头部、卡片、表格与图表容器），并增加表格列控制与悬浮提示。代码在：[src/agents/data_analysis/file_report.py](src/agents/data_analysis/file_report.py)
- 修复 ECharts 在报告中不渲染的问题：确保每个图表占位有固定高度、唯一 id，并在 JS 中初始化和处理窗口 resize。图表使用 ECharts CDN（在线加载）。

## 关键文件
- [run_file_analysis.py](run_file_analysis.py): 客户端示例脚本，发送 CSV 到本地 API 并保存返回的 HTML/MD/Charts。
- [src/agents/data_analysis/file_report.py](src/agents/data_analysis/file_report.py): 报告 HTML 生成函数，包含样式与嵌入的 JS（图表初始化、表格列控件等）。

## 用户可见效果
- 报告头部采用渐变色卡片，突出标题与摘要。
- 表格采用卡片样式、自动列宽策略、超过长度的单元格会显示 `title` 提示（鼠标悬浮可看完整值）。
- 每个表格上方有“列显示”按钮，可以勾选/隐藏列（实现折叠列的交互）。
- 图表容器有固定高度（默认 360px），并且在窗口尺寸变化时会自动 resize，提升跨设备兼容性。

## 如何使用（快速运行）
1. 启动本地 API（确保服务端运行）

```bash
# 示例 —— 启动 FastAPI（按你项目实际命令）
uvicorn src.api:app --reload
```

2. 运行客户端脚本（会把 CSV POST 到本地并保存 HTML/MD）

```bash
python run_file_analysis.py
```

3. 打开生成的 HTML
- 默认生成文件：`file_analysis_report.html` 与 `file_analysis_report.md`，直接在浏览器打开 `file_analysis_report.html` 即可查看样式与交互。

## 依赖与注意事项
- 前端图表依赖 ECharts CDN（已嵌入在 HTML）：无需额外本地安装。
- 若你需要 PPT 导出功能：之前有 `src/export/pptx_exporter.py`，但客户端已移除自动调用。若要使用 PPT 导出，请安装 `python-pptx` 并调用导出器脚本：

```bash
pip install python-pptx
# 然后按需调用 src.export.pptx_exporter.PPTXExporter
```

## 可继续的改进项（建议优先级）
1. 将表格中的数值列自动识别为可折叠（默认折叠大数值列）并提供“恢复默认视图”按钮。  
2. 将交互式图表渲染为 PNG 并嵌入到静态报告或 PPT 中（便于离线分享）。  
3. 增加深色主题与打印友好样式（@media print）。

---