#!/usr/bin/env python3
import re
from pathlib import Path
p = Path('README.md')
text = p.read_text(encoding='utf-8', errors='ignore')
text_new = re.sub(r'xunlong\.py', 'SmartFin.py', text, flags=re.IGNORECASE)
text_new = re.sub(r'xunlong', 'SmartFin', text_new, flags=re.IGNORECASE)
if text_new != text:
    p.write_text(text_new, encoding='utf-8')
    print('README.md updated')
else:
    print('No change')
