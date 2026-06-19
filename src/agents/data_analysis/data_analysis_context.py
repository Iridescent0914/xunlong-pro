"""将 data_analysis_results 格式化为报告写作上下文，并生成与正文的逻辑关联说明。"""

import json
from typing import Any, Dict, List, Optional


DA_MODULE_TITLE = "金融数据分析"
DA_MODULE_ANCHOR = "金融数据分析"

_INTEGRATION_KEYWORDS = ("现状", "分析", "数据", "财务", "指标", "趋势", "业绩", "经营")


def has_usable_analysis(data: Optional[Dict[str, Any]]) -> bool:
    if not data or data.get("status") != "success":
        return False
    return bool(
        data.get("key_findings")
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


def build_main_body_relation(
    main_sections: List[Dict[str, Any]],
    data: Dict[str, Any],
) -> str:
    """独立分析模块开头的「与正文逻辑关系」段落。"""
    if not main_sections:
        return ""

    integrated = [
        s for s in main_sections if s.get("integrate_data_analysis")
    ]
    section_list = "、".join(
        f"第{s.get('id', s.get('section_id', '?'))}节「{s.get('title', '')}」"
        for s in main_sections
    )
    integrate_desc = ""
    if integrated:
        names = "、".join(f"「{s.get('title', '')}」" for s in integrated)
        integrate_desc = (
            f"正文 {names} 中的财务与经营论述，"
            f"以下指标与结论提供量化依据；"
        )
    else:
        integrate_desc = "正文各章节的量化论述，以下指标与结论提供依据；"

    findings = data.get("key_findings", [])
    finding_hint = ""
    if findings:
        titles = []
        for f in findings[:3]:
            if isinstance(f, dict):
                titles.append(f.get("title", ""))
            else:
                titles.append(str(f))
        finding_hint = f"核心结论包括：{'；'.join(t for t in titles if t)}。"

    lines = [
        "### 与正文的逻辑关系\n",
        f"- **正文结构**：本报告正文包含 {len(main_sections)} 节：{section_list}。",
        f"- **模块定位**：{integrate_desc}"
        f"正文侧重叙述与判断，本模块侧重**可溯源的结构化数据、表格与图表**。",
        f"- **阅读路径**：建议先阅读正文中与财务、经营相关的章节，"
        f"再在本模块查阅分来源指标与依据。{finding_hint}",
        f"- **交叉引用**：正文引用本模块时请使用链接 "
        f"[{DA_MODULE_TITLE}](#{DA_MODULE_ANCHOR})。\n",
    ]
    return "\n".join(lines)


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
