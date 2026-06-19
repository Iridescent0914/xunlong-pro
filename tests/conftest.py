"""单元测试公共 fixture：避免拉取完整 coordinator 依赖链。"""

import sys
from unittest.mock import MagicMock

# 数据分析单测不需要网页抽取栈，提前 stub 避免 import coordinator
for _mod in ("trafilatura", "langgraph"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
