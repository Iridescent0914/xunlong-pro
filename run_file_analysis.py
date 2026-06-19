import json
import requests
import pandas as pd
import pathlib
import asyncio

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
    "output_formats": ["json", "html", "md"],
    "use_llm": True
}

resp = requests.post("http://127.0.0.1:8000/api/v1/data_analysis/file", json=payload)
print(resp.status_code)
data = resp.json()
# print a short summary to terminal
print(json.dumps(data.get('result', {}), ensure_ascii=False)[:2000])

# save outputs locally for easy viewing
report = data.get('report', {}) or {}
if report.get('html'):
    out_html = 'file_analysis_report.html'
    with open(out_html, 'w', encoding='utf-8') as f:
        f.write(report['html'])
    print(f"Saved HTML report to {out_html}")
    try:
        import webbrowser, pathlib
        webbrowser.open(str(pathlib.Path(out_html).resolve()))
    except Exception:
        pass

if report.get('markdown'):
    out_md = 'file_analysis_report.md'
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write(report['markdown'])
    print(f"Saved Markdown report to {out_md}")

charts = data.get('charts')
if charts:
    out_charts = 'file_analysis_charts.json'
    with open(out_charts, 'w', encoding='utf-8') as f:
        json.dump(charts, f, ensure_ascii=False, indent=2)
    print(f"Saved charts to {out_charts}")

# If backend provides a full HTML page under top-level 'html', save it too
if data.get('html'):
    out_html2 = 'file_analysis_full.html'
    with open(out_html2, 'w', encoding='utf-8') as f:
        f.write(data['html'])
    print(f"Saved full HTML to {out_html2}")

# PPT 导出已移除：不再在客户端自动生成 PPTX
