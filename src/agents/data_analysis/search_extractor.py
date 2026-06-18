"""从网页搜索结果中抽取结构化金融数据（成员 1）。"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .schemas import DataTable, ProcessedStats, SearchReference

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MOCK_SEARCH_PATH = PROJECT_ROOT / "fixtures" / "mock_search.json"
MOCK_STATS_PATH = PROJECT_ROOT / "fixtures" / "mock_stats.json"


def _load_mock_search() -> List[Dict[str, Any]]:
    if not MOCK_SEARCH_PATH.exists():
        return []
    return json.loads(MOCK_SEARCH_PATH.read_text(encoding="utf-8"))


def _load_mock_stats_raw() -> Dict[str, Any]:
    if not MOCK_STATS_PATH.exists():
        return {
            "metrics": {"revenue_yoy": 0.23, "gross_margin": 0.41},
            "tables": [],
            "data_summary": "mock fallback",
        }
    return json.loads(MOCK_STATS_PATH.read_text(encoding="utf-8"))


def _build_search_refs(search_results: List[Dict[str, Any]]) -> List[SearchReference]:
    refs = []
    for item in search_results[:5]:
        snippet = item.get("snippet") or item.get("content") or ""
        refs.append(
            SearchReference(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=snippet[:300] if snippet else "",
            )
        )
    return refs


def _extract_metrics_from_text(text: str) -> Dict[str, Any]:
    """从搜索正文尝试抽取简单指标（骨架：正则匹配百分比）。"""
    metrics: Dict[str, Any] = {}
    yoy_match = re.search(r"同比增长\s*(\d+(?:\.\d+)?)\s*%", text)
    if yoy_match:
        metrics["revenue_yoy"] = float(yoy_match.group(1)) / 100

    margin_match = re.search(r"毛利率\s*(\d+(?:\.\d+)?)\s*%", text)
    if margin_match:
        metrics["gross_margin"] = float(margin_match.group(1)) / 100

    debt_match = re.search(r"资产负债率\s*(\d+(?:\.\d+)?)\s*%", text)
    if debt_match:
        metrics["debt_ratio"] = float(debt_match.group(1)) / 100

    return metrics


async def extract_from_search(
    search_results: Optional[List[Dict[str, Any]]] = None,
    use_mock: bool = False,
) -> ProcessedStats:
    """
    从 search_results 抽取 metrics、tables、search_refs。

    骨架阶段：
    - 无搜索结果或 use_mock=True 时使用 fixtures/mock_search.json
    - 指标优先从正文正则抽取，不足时回退 mock_stats.json
    """
    results = search_results or []
    if use_mock or not results:
        logger.info("[SearchExtractor] 使用 mock_search.json（骨架模式）")
        results = _load_mock_search()

    search_refs = _build_search_refs(results)

    combined_text = "\n".join(
        (r.get("content") or r.get("snippet") or "") for r in results
    )
    metrics = _extract_metrics_from_text(combined_text)

    mock_raw = _load_mock_stats_raw()
    tables = [DataTable(**t) for t in mock_raw.get("tables", [])]

    if not metrics:
        metrics = mock_raw.get("metrics", {})
        logger.info("[SearchExtractor] 正文未抽到指标，回退 mock_stats")

    summary = (
        f"基于 {len(results)} 条搜索结果抽取；"
        f"{'含正则指标' if _extract_metrics_from_text(combined_text) else '指标来自 mock_stats 回退'}"
    )

    return ProcessedStats(
        metrics=metrics,
        tables=tables,
        data_summary=summary,
        search_refs=search_refs,
    )
