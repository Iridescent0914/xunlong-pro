# API 使用指南

SmartFin 前前只保留一个 API 入口：

```bash
python run_api.py
```

FastAPI 应用定义在 `src/api.py`。启动 `run_api.py` 后，后端会同时托管 `frontend-static/index.html` 这个可视化前端。

## 访问地址

- 可视化界面：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

不需要单独启动前端开发服务器，也不需要单独启动 worker。任务执行器已经在 `src/api.py` 启动事件中自动运行。

## 主要接口

```text
POST   /api/v1/tasks/report
POST   /api/v1/tasks/fiction
POST   /api/v1/tasks/ppt
POST   /api/v1/tasks/file_analysis
GET    /api/v1/tasks/{task_id}
GET    /api/v1/tasks/{task_id}/result
GET    /api/v1/tasks/{task_id}/download?file_type=html
GET    /api/v1/tasks/{task_id}/download?file_type=md
DELETE /api/v1/tasks/{task_id}
POST   /api/v1/data_analysis/file
POST   /api/v1/data_analysis/charts
GET    /api/v1/config/rag
PUT    /api/v1/config/rag
```

## 示例

```python
import requests

resp = requests.post(
    "http://localhost:8000/api/v1/tasks/report",
    json={
        "query": "人工智能行业趋势",
        "report_type": "comprehensive",
        "search_depth": "deep",
        "max_results": 10,
        "output_format": "html",
    },
)
resp.raise_for_status()
print(resp.json()["task_id"])
```

## 排查

如果任务长时间停留在 pending，重启 `python run_api.py` 并查看后端日志。当前项目不再需要单独的 worker 命令。

如果前端页面打不开，确认 `frontend-static/index.html` 存在，并访问 `http://localhost:8000`。