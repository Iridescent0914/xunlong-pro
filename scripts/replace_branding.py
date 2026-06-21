#!/usr/bin/env python3
"""
批量替换仓库中的品牌词：
 - SmartFin -> SmartFin
 - SmartFin -> SmartFin
 - SmartFin.py -> SmartFin.py
会对文本文件创建 .bak 备份（原始内容）。
"""
import sys
from pathlib import Path
import fnmatch

ROOT = Path('.').resolve()
EXCLUDE_DIRS = {'.git', 'venv', 'env', '__pycache__', 'node_modules', 'dist', '.venv'}
TEXT_EXTENSIONS = ('*.py', '*.md', '*.rst', '*.txt', '*.html', '*.htm', '*.js', '*.json', '*.yml', '*.yaml', '*.css', '*.ts', '*.jsx', '*.tsx', '*.cfg', '*.ini')

replacements = [
    ('SmartFin', 'SmartFin'),
    ('SmartFin.py', 'SmartFin.py'),
    ('SmartFin', 'SmartFin'),
]

changed_files = []

for p in ROOT.rglob('*'):
    if any(part in EXCLUDE_DIRS for part in p.parts):
        continue
    if p.is_file():
        matched = False
        for pat in TEXT_EXTENSIONS:
            if fnmatch.fnmatch(p.name, pat):
                matched = True
                break
        # Also check certain files without extension (like README) or files in docs/
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
        for old, new in replacements:
            if old in new_text:
                new_text = new_text.replace(old, new)
        if new_text != text:
            bak = p.with_suffix(p.suffix + '.bak') if p.suffix else Path(str(p) + '.bak')
            p.write_text(new_text, encoding='utf-8')
            bak.write_text(text, encoding='utf-8')
            changed_files.append(str(p))

print('Replacements complete. Files changed: {}'.format(len(changed_files)))
for f in changed_files:
    print(f)

# Exit with code 0
sys.exit(0)
