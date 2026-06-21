#!/usr/bin/env python3
"""
第二遍替换：
 - 使用大小写不敏感匹配替换全部 SmartFin/SmartFin -> SmartFin
 - 先替换 SmartFin.py -> SmartFin.py，再替换 SmartFin -> SmartFin
 - 跳过 .bak 文件
 - 扩展匹配到更多文本扩展名（包含 .mts）
"""
import sys
from pathlib import Path
import fnmatch
import re

ROOT = Path('.').resolve()
EXCLUDE_DIRS = {'.git', 'venv', 'env', '__pycache__', 'node_modules', 'dist', '.venv'}
TEXT_EXTENSIONS = ('*.py', '*.md', '*.rst', '*.txt', '*.html', '*.htm', '*.js', '*.json', '*.yml', '*.yaml', '*.css', '*.ts', '*.jsx', '*.tsx', '*.cfg', '*.ini', '*.mts', '*.toml')

patterns = [
    (re.compile(r'SmartFin\.py', re.IGNORECASE), 'SmartFin.py'),
    (re.compile(r'SmartFin', re.IGNORECASE), 'SmartFin'),
]

changed_files = []

for p in ROOT.rglob('*'):
    if any(part in EXCLUDE_DIRS for part in p.parts):
        continue
    if p.is_file():
        if p.name.endswith('.bak'):
            continue
        matched = False
        for pat in TEXT_EXTENSIONS:
            if fnmatch.fnmatch(p.name, pat):
                matched = True
                break
        if not matched and (p.suffix == '' and p.name.lower().startswith('readme')):
            matched = True
        if not matched:
            continue
        try:
            text = p.read_text(encoding='utf-8')
        except Exception:
            try:
                text = p.read_text(encoding='latin-1')
            except Exception:
                continue
        new_text = text
        for regex, repl in patterns:
            new_text = regex.sub(repl, new_text)
        if new_text != text:
            bak = p.with_suffix(p.suffix + '.bak') if p.suffix else Path(str(p) + '.bak')
            p.write_text(new_text, encoding='utf-8')
            bak.write_text(text, encoding='utf-8')
            changed_files.append(str(p))

print('Pass2 replacements complete. Files changed: {}'.format(len(changed_files)))
for f in changed_files:
    print(f)

sys.exit(0)
