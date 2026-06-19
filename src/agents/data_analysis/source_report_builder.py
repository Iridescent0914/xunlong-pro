"""按来源构建「表格 + 图表 + 结论」分析块（LLM 与算法 metrics 整合）。"""

import json
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional

from loguru import logger

from .analysis_output import AnalysisOutput
from .chart_builder import build_chart_for_table
from .schemas import DataFinding, DataTable, SearchReference

LLMCallback = Callable[[str, str], Awaitable[str]]

_METRIC_LABELS = {
    "revenue_yoy": "营收同比增长",
    "net_profit_yoy": "净利润同比增长",
    "gross_margin": "毛利率",
    "debt_ratio": "资产负债率",
    "loan_growth": "贷款总额增幅",
    "asset_growth": "总资产增幅",
    "revenue_period_growth": "营收区间增幅",
    "avg_growth_rate": "平均增长率",
    "max_growth_rate": "最高增长率",
    "min_growth_rate": "最低增长率",
    "net_profit": "净利润",
    "total_assets": "总资产",
    "revenue": "营收",
}


async def build_source_blocks(
    query: str,
    analysis: AnalysisOutput,
    search_results: Optional[List[Dict[str, Any]]] = None,
    *,
    llm_callback: Optional[LLMCallback] = None,
) -> List[Dict[str, Any]]:
    """为每个搜索来源生成 table + chart + conclusion。"""
    grouped = _group_by_source(analysis)
    if not grouped:
        return []

    content_map = _source_content_map(search_results or [], analysis.search_refs)
    blocks: List[Dict[str, Any]] = []

    for src_idx in sorted(grouped.keys()):
        bundle = grouped[src_idx]
        ref = _pick_search_ref(analysis.search_refs, src_idx)
        title = bundle.get("source_title") or (ref.title if ref else f"来源{src_idx}")
        url = ref.url if ref else ""
        snippet = content_map.get(src_idx, ref.snippet if ref else "")

        algo_table = _pick_algorithm_table(bundle.get("tables", []))
        algo_metrics = bundle.get("metrics") or {}

        merged_table = await _merge_table_with_llm(
            query=query,
            source_index=src_idx,
            source_title=title,
            source_content=snippet,
            algorithm_metrics=algo_metrics,
            algorithm_table=algo_table,
            llm_callback=llm_callback,
        )
        if not merged_table:
            merged_table = _fallback_table(src_idx, title, algo_table, algo_metrics)

        chart = build_chart_for_table(
            merged_table,
            chart_id=f"chart_src_{src_idx}",
        )
        conclusion = await _generate_conclusion_with_llm(
            query=query,
            source_index=src_idx,
            source_title=title,
            table=merged_table,
            metrics=algo_metrics,
            llm_callback=llm_callback,
        )
        if not conclusion:
            conclusion = _fallback_conclusion(src_idx, bundle.get("findings", []))

        blocks.append(
            {
                "source_index": src_idx,
                "source_title": title,
                "source_url": url,
                "table": merged_table.model_dump(),
                "chart": chart,
                "conclusion": conclusion,
                "algorithm_metrics": algo_metrics,
            }
        )

    logger.info(f"[SourceReportBuilder] 生成 {len(blocks)} 个分来源分析块")
    return blocks


def _group_by_source(analysis: AnalysisOutput) -> Dict[int, Dict[str, Any]]:
    by_source = {}
    metrics_root = analysis.metrics if isinstance(analysis.metrics, dict) else {}
    if isinstance(metrics_root.get("by_source"), dict):
        for key, block in metrics_root["by_source"].items():
            if not isinstance(block, dict):
                continue
            idx = int(block.get("source_index", key))
            by_source[idx] = {
                "source_title": block.get("source_title", ""),
                "metrics": block.get("metrics") or {},
                "tables": [],
                "findings": [],
            }

    for table in analysis.tables:
        idx = _parse_source_index(table.title)
        if idx is None:
            continue
        by_source.setdefault(
            idx,
            {"source_title": "", "metrics": {}, "tables": [], "findings": []},
        )
        by_source[idx]["tables"].append(table)

    for finding in analysis.key_findings:
        idx = _parse_finding_source_index(finding)
        if idx is None:
            continue
        by_source.setdefault(
            idx,
            {"source_title": "", "metrics": {}, "tables": [], "findings": []},
        )
        by_source[idx]["findings"].append(finding)

    if not by_source and (analysis.tables or analysis.key_findings):
        by_source[1] = {
            "source_title": analysis.search_refs[0].title if analysis.search_refs else "",
            "metrics": metrics_root if not metrics_root.get("by_source") else {},
            "tables": list(analysis.tables),
            "findings": list(analysis.key_findings),
        }

    for idx, ref in enumerate(analysis.search_refs, 1):
        if idx not in by_source:
            continue
        if not by_source[idx].get("source_title"):
            by_source[idx]["source_title"] = ref.title

    return by_source


def _parse_source_index(title: str) -> Optional[int]:
    match = re.search(r"来源\s*\[(\d+)\]", title or "")
    return int(match.group(1)) if match else None


def _parse_finding_source_index(finding: DataFinding) -> Optional[int]:
    match = re.search(r"\[来源(\d+)\]", finding.title or "")
    return int(match.group(1)) if match else None


def _pick_search_ref(refs: List[SearchReference], source_index: int) -> Optional[SearchReference]:
    if 1 <= source_index <= len(refs):
        return refs[source_index - 1]
    for ref in refs:
        if ref.title:
            return ref
    return None


def _source_content_map(
    search_results: List[Dict[str, Any]],
    search_refs: List[SearchReference],
) -> Dict[int, str]:
    content: Dict[int, str] = {}
    for i, item in enumerate(search_results[:8], 1):
        body = item.get("content") or item.get("snippet") or ""
        title = item.get("title") or ""
        if body or title:
            content[i] = f"{title}\n{body[:2000]}".strip()
    for i, ref in enumerate(search_refs, 1):
        if i not in content and ref.snippet:
            content[i] = f"{ref.title}\n{ref.snippet}"
    return content


def _pick_algorithm_table(tables: List[DataTable]) -> Optional[DataTable]:
    for table in tables:
        if "指标明细" in table.title:
            return table
    for table in tables:
        if "分季度" in table.title:
            return table
    return tables[0] if tables else None


def _fallback_table(
    source_index: int,
    source_title: str,
    algo_table: Optional[DataTable],
    metrics: Dict[str, Any],
) -> DataTable:
    if algo_table and algo_table.rows:
        return algo_table

    rows = []
    for key, value in metrics.items():
        label = _METRIC_LABELS.get(key, key)
        rows.append([label, _format_metric_cell(key, value), "-", "算法抽取"])
    if rows:
        return DataTable(
            title=f"来源 [{source_index}] {source_title[:24]} · 指标汇总",
            columns=["指标", "数值", "期间", "说明"],
            rows=rows,
        )
    return DataTable(
        title=f"来源 [{source_index}] {source_title[:24]} · 指标汇总",
        columns=["说明"],
        rows=[["未从该来源抽取到可量化指标"]],
    )


def _format_metric_cell(key: str, value: Any) -> str:
    if isinstance(value, (int, float)) and (
        key.endswith("_yoy")
        or "growth" in key
        or key.endswith("_rate")
        or key in ("gross_margin", "debt_ratio", "loan_growth", "asset_growth")
    ):
        return f"{value * 100:.2f}%"
    return str(value)


async def _merge_table_with_llm(
    *,
    query: str,
    source_index: int,
    source_title: str,
    source_content: str,
    algorithm_metrics: Dict[str, Any],
    algorithm_table: Optional[DataTable],
    llm_callback: Optional[LLMCallback],
) -> Optional[DataTable]:
    if not llm_callback or not source_content.strip():
        return None

    algo_table_payload = (
        algorithm_table.model_dump()
        if algorithm_table
        else {"title": "", "columns": [], "rows": []}
    )
    system_prompt = (
        "你是金融数据分析专家。请基于「来源正文」与「算法已抽取的 metrics/表格」"
        "整合为一张结构化 Markdown 数据表。\n"
        "要求：\n"
        "1. algorithm_metrics 中的数值必须原样保留，不得改写或编造\n"
        "2. 可补充来源正文中与 query 相关的其他量化或关键事实行\n"
        "3. 严格输出 JSON：{title, columns, rows}\n"
        "4. columns 为 2~4 列；rows 为二维数组"
    )
    user_prompt = json.dumps(
        {
            "query": query,
            "source_index": source_index,
            "source_title": source_title,
            "source_content": source_content[:2500],
            "algorithm_metrics": algorithm_metrics,
            "algorithm_table": algo_table_payload,
            "output_schema": {
                "title": f"来源 [{source_index}] 分析表",
                "columns": ["指标", "数值", "期间", "依据"],
                "rows": [["营收", "8621亿元", "2024", "年报正文"]],
            },
        },
        ensure_ascii=False,
        indent=2,
    )
    try:
        response = await llm_callback(user_prompt, system_prompt)
        parsed = _parse_json_block(response)
        if parsed and parsed.get("columns") and parsed.get("rows"):
            return DataTable(
                title=parsed.get("title") or f"来源 [{source_index}] {source_title[:24]} · 分析表",
                columns=[str(c) for c in parsed["columns"]],
                rows=[[str(cell) for cell in row] for row in parsed["rows"]],
            )
    except Exception as e:
        logger.warning(f"[SourceReportBuilder] LLM 整合表格失败（来源{source_index}）: {e}")
    return None


async def _generate_conclusion_with_llm(
    *,
    query: str,
    source_index: int,
    source_title: str,
    table: DataTable,
    metrics: Dict[str, Any],
    llm_callback: Optional[LLMCallback],
) -> str:
    if not llm_callback:
        return ""

    system_prompt = (
        "你是金融数据分析专家。请根据给定数据表与指标，"
        "撰写 2~4 句中文分析结论，聚焦用户 query。\n"
        "要求：数值须与表格/metrics 一致，不得编造；直接输出 JSON：{\"conclusion\": \"...\"}"
    )
    user_prompt = json.dumps(
        {
            "query": query,
            "source_index": source_index,
            "source_title": source_title,
            "table": table.model_dump(),
            "algorithm_metrics": metrics,
        },
        ensure_ascii=False,
        indent=2,
    )
    try:
        response = await llm_callback(user_prompt, system_prompt)
        parsed = _parse_json_block(response)
        if parsed and parsed.get("conclusion"):
            return str(parsed["conclusion"]).strip()
    except Exception as e:
        logger.warning(f"[SourceReportBuilder] LLM 生成结论失败（来源{source_index}）: {e}")
    return ""


def _fallback_conclusion(source_index: int, findings: List[DataFinding]) -> str:
    lines = []
    for f in findings[:4]:
        text = f"{f.title.replace(f'[来源{source_index}] ', '')}：{f.value}"
        lines.append(text)
    if lines:
        return "；".join(lines) + "。"
    return "该来源暂无足够量化数据支撑进一步结论。"


def _parse_json_block(text: str) -> Optional[Dict[str, Any]]:
    raw = (text or "").strip()
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            chunk = part.strip()
            if chunk.startswith("json"):
                chunk = chunk[4:].strip()
            if chunk.startswith("{"):
                raw = chunk
                break
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
