"""API"""

import sys
from loguru import logger

# 只输出 INFO 及以上，屏蔽 DEBUG
logger.remove()
logger.add(sys.stderr, level="INFO")

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.api:app",  # reload
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
