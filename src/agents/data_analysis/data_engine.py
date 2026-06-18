"""成员 1：输入数据 + 处理（确定性计算，不含 LLM）。"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from .schemas import DataTable, ProcessedStats

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = PROJECT_ROOT / "fixtures"
MOCK_STATS_PATH = FIXTURES_DIR / "mock_stats.json"


def _load_mock_stats() -> ProcessedStats:
    if not MOCK_STATS_PATH.exists():
        logger.warning(f"Mock stats not found: {MOCK_STATS_PATH}")
        return ProcessedStats(
            metrics={"revenue_yoy": 0.23, "gross_margin": 0.41},
            tables=[],
            data_summary="mock fallback",
        )
    raw = json.loads(MOCK_STATS_PATH.read_text(encoding="utf-8"))
    tables = [DataTable(**t) if isinstance(t, dict) else t for t in raw.get("tables", [])]
    return ProcessedStats(
        metrics=raw.get("metrics", {}),
        tables=tables,
        data_summary=raw.get("data_summary", ""),
    )


async def analyze(data_sources: Optional[Dict[str, Any]] = None) -> ProcessedStats:
    """
    读取 Excel/CSV/DB 并计算金融指标。

    骨架阶段：use_mock=True（默认）时返回 fixtures/mock_stats.json。
    成员 1 实现真实逻辑后，将 use_mock 设为 False 或移除 mock 分支。
    """
    data_sources = data_sources or {}
    use_mock = data_sources.get("use_mock", True)

    if use_mock:
        logger.info("[DataEngine] 使用 mock_stats.json（骨架模式）")
        return _load_mock_stats()

    excel_path = data_sources.get("excel_path") or data_sources.get("csv_path")
    if excel_path:
        return await _analyze_from_file(excel_path)

    logger.warning("[DataEngine] 未提供数据源，回退 mock")
    return _load_mock_stats()


async def _analyze_from_file(path: str) -> ProcessedStats:
    """成员 1 TODO: 实现真实文件分析。"""
    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = PROJECT_ROOT / path

    logger.info(f"[DataEngine] TODO: 分析文件 {file_path}")
    # 成员 1 在此接入 pandas + excel_reader
    return _load_mock_stats()
