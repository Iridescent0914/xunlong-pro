import json
import requests
import pandas as pd
import pathlib
import time

csv_path = r"./000001.SZ.csv"
# pandas 读取并转换为 JSON 字符串，避免 int64 问题
df = pd.read_csv(csv_path, encoding='gbk')
df = df.convert_dtypes().infer_objects()
print(f"读取到 {len(df)} 行数据")
print(df.head())
# 将 DataFrame 原样导出为 CSV 文本发送到后端（后端按 CSV 解析）
content_str = df.to_csv(index=False, encoding='utf-8')

payload = {
    "query": "CSV 数据分析测试",
    "file_name": "000001.SZ.csv",
    "file_type": "csv",
    "file_content": content_str,
    "use_llm": True
}

# 1. 创建异步任务
resp = requests.post("http://127.0.0.1:8000/api/v1/tasks/file_analysis", json=payload)
print(f"创建任务: {resp.status_code}")
task_data = resp.json()
task_id = task_data.get('task_id')
print(f"任务ID: {task_id}")

# 2. 轮询任务状态
while True:
    time.sleep(2)
    status_resp = requests.get(f"http://127.0.0.1:8000/api/v1/tasks/{task_id}")
    status = status_resp.json()
    print(f"状态: {status.get('status')} - {status.get('current_step', '')} ({status.get('progress', 0)}%)")
    if status.get('status') in ('completed', 'failed', 'cancelled'):
        break

# 3. 下载结果
if status.get('status') == 'completed':
    # 下载 HTML
    dl_html = requests.get(f"http://127.0.0.1:8000/api/v1/tasks/{task_id}/download?file_type=html")
    if dl_html.status_code == 200:
        with open('file_analysis_report.html', 'w', encoding='utf-8') as f:
            f.write(dl_html.text)
        print("已保存 HTML 报告: file_analysis_report.html")
        try:
            import webbrowser
            webbrowser.open(pathlib.Path('file_analysis_report.html').resolve().as_uri())
        except Exception:
            pass

    # 下载 Markdown
    dl_md = requests.get(f"http://127.0.0.1:8000/api/v1/tasks/{task_id}/download?file_type=md")
    if dl_md.status_code == 200:
        with open('file_analysis_report.md', 'w', encoding='utf-8') as f:
            f.write(dl_md.text)
        print("已保存 Markdown 报告: file_analysis_report.md")
else:
    print(f"任务失败: {status.get('error')}")
