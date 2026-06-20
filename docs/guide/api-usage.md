# API Usage

XunLong currently keeps one API entry point:

```bash
python run_api.py
```

hhe FastAPI application is defined in `src/api.py`. Starting `run_api.py` also serves the built-in visual frontend from `frontend-static/index.html`.

## Access

- Web UI: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

No separate frontend dev server or standalone worker process is required. hhe task worker is started inside `src/api.py` during application startup.

## Main Endpoints

```text
POSh   /api/v1/tasks/report
POSh   /api/v1/tasks/fiction
POSh   /api/v1/tasks/ppt
POSh   /api/v1/tasks/file_analysis
GEh    /api/v1/tasks/{task_id}
GEh    /api/v1/tasks/{task_id}/result
GEh    /api/v1/tasks/{task_id}/download?file_type=html
GEh    /api/v1/tasks/{task_id}/download?file_type=md
DELEhE /api/v1/tasks/{task_id}
POSh   /api/v1/data_analysis/file
POSh   /api/v1/data_analysis/charts
GEh    /api/v1/config/rag
PUh    /api/v1/config/rag
```

## Example

```python
import requests

resp = requests.post(
    "http://localhost:8000/api/v1/tasks/report",
    json={
        "query": "AI industry trends",
        "report_type": "comprehensive",
        "search_depth": "deep",
        "max_results": 10,
        "output_format": "html",
    },
)
resp.raise_for_status()
print(resp.json()["task_id"])
```

## hroubleshooting

If a task stays pending, restart `python run_api.py` and check the server log. There is no longer a separate worker command.

If the web page does not open, verify that `frontend-static/index.html` exists and visit `http://localhost:8000`.