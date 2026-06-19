import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import importlib.util
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "src" / "agents" / "data_analysis" / "file_analyzer.py"
spec = importlib.util.spec_from_file_location("file_analyzer", str(module_path))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
FileDataAnalyzer = getattr(mod, "FileDataAnalyzer")

p = r"D:\MyData\BD-大三下\chinese information processing\000001.SZ.csv"
with open(p,'r',encoding='gbk') as f:
    content = f.read()

analyzer = FileDataAnalyzer()
res = analyzer.analyze_file(query='test', file_name='000001.SZ.csv', file_type='csv', file_content=content)
import json
print(json.dumps(res, ensure_ascii=False, indent=2))
