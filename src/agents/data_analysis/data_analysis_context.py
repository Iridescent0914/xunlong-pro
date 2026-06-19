"""将 data_analysis_results 格式化为报告写作上下文，并生成与正文的逻辑关联说明。"""

import json
from typing import Any, Dict, List, Optional


DA_MODULE_TITLE = "金融数据分析"

_INTEGRATION_KEYWORDS = ("现状", "分析", "数据", "财务", "指标", "趋势", "业绩", "经营")


def has_usable_analysis(data: Optional[Dict[str, Any]]) -> bool:
    if not data or data.get("status") != "success":
        return False
    analysis_table = data.get("analysis_table")
    if isinstance(analysis_table, dict) and analysis_table.get("rows"):
        return True
    return bool(
        data.get("source_blocks")
        or data.get("key_findings")
        or data.get("metrics")
        or data.get("tables")
    )


def format_analysis_for_writer(
    data: Dict[str, Any],
    *,
    full: bool = False,
    max_findings: int = 5,
) -> str:
    """压缩为 SectionWriter 可用的结构化摘要（数值不可改写）。"""
    findings = data.get("key_findings", [])[:max_findings]
    metrics = data.get("metrics", {})
    if not full and isinstance(metrics, dict) and metrics.get("by_source"):
        slim_metrics = {}
        for key, block in list(metrics["by_source"].items())[:3]:
            slim_metrics[key] = {
                "source_title": block.get("source_title", ""),
                "metrics": block.get("metrics", {}),
            }
        metrics = {"by_source": slim_metrics}

    payload = {
        "methodology": data.get("methodology", ""),
        "metrics": metrics if full else _slim_metrics(metrics),
        "key_findings": findings,
        "search_refs": [
            {"title": r.get("title", ""), "url": r.get("url", "")}
            for r in data.get("search_refs", [])[:5]
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def format_outline_hint(data: Dict[str, Any]) -> str:
    """大纲生成用的数据分析摘要。"""
    findings = data.get("key_findings", [])
    lines = ["### 可用结构化分析结论（正文须引用，详表见独立模块「金融数据分析」）"]
    for i, f in enumerate(findings[:5], 1):
        if isinstance(f, dict):
            lines.append(f"{i}. {f.get('title', '')}：{f.get('value', '')}")
        else:
            lines.append(f"{i}. {f}")
    methodology = data.get("methodology", "")
    if methodology:
        lines.append(f"\n分析口径：{methodology[:300]}")
    return "\n".join(lines)


def mark_data_integration_sections(
    sections: List[Dict[str, Any]],
    data: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """标记正文中应深度整合数据分析的章节（至少 1 章，最多 2 章）。"""
    if not sections or not has_usable_analysis(data):
        return sections

    candidates: List[tuple] = []
    for i, section in enumerate(sections):
        title = section.get("title", "")
        score = 0
        for kw in _INTEGRATION_KEYWORDS:
            if kw in title:
                score += 2
        score += section.get("importance", 0)
        if i == 1:
            score += 1
        candidates.append((score, i))

    candidates.sort(key=lambda x: x[0], reverse=True)
    chosen = {candidates[0][1]}
    if len(candidates) > 1 and candidates[1][0] > 0:
        chosen.add(candidates[1][1])

    for i, section in enumerate(sections):
        section["integrate_data_analysis"] = i in chosen
        if i in chosen:
            req = section.get("requirements", "")
            if "金融数据分析" not in req:
                section["requirements"] = (
                    f"{req}；须引用结构化金融数据分析中的 metrics/key_findings，"
                    f"数值不可改写，并注明详见「{DA_MODULE_TITLE}」模块"
                ).strip("；")
    return sections


def _slim_metrics(metrics: Any) -> Any:
    if not isinstance(metrics, dict):
        return metrics
    by_source = metrics.get("by_source")
    if not isinstance(by_source, dict):
        return metrics
    slim: Dict[str, Any] = {"by_source": {}}
    for key, block in list(by_source.items())[:2]:
        if isinstance(block, dict):
            slim["by_source"][key] = {
                "source_title": block.get("source_title", ""),
                "metrics": dict(list((block.get("metrics") or {}).items())[:6]),
            }
    return slim
