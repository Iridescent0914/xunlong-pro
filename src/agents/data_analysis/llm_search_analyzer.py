"""将网页搜索结果直接交给 LLM，抽取与用户 query 相关的数值表格。"""

import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

from loguru import logger

from .schemas import DataTable, SearchReference

LLMCallback = Callable[[str, str], Awaitable[str]]

_MAX_SOURCES = 10
_MAX_CHARS_PER_SOURCE = 2500

_SYSTEM_PROMPT = """你是专业的金融与商业数据分析助手。

任务：阅读用户提供的多篇网页搜索结果，针对用户的「分析问题」，抽取所有在原文中有明确文字依据的数值指标，整理成一张 Markdown 数据表。

## 抽取规则（必须严格遵守）

1. **禁止编造**：所有数值必须能在对应来源正文中找到原文依据；禁止估算、外推、补全或合并不同来源的冲突数字。
2. **主题相关**：只抽取与用户 query 直接相关的指标（例如 query 问「华为2024年营收」→ 抽营收、收入、净利润、同比增长、研发投入等；不要抽无关公司的数据）。
3. **保留单位与期间**：数值列保留原文单位（亿元、%、美元等）；有年份/季度则写入「期间」列。
4. **来源可追溯**：每行必须在「来源」列标注 `[N]`（对应搜索结果编号），在「原文依据」列摘录 ≤40 字的原文片段。
5. **冲突处理**：若不同来源对同一指标给出不同数值，分多行列出，不要取平均或自行选择。
6. **空结果**：若所有来源均无相关数值，`rows` 返回空数组，`conclusion` 说明原因。

## 输出格式

只输出一个 JSON 对象，不要 markdown 代码块以外的任何文字：

{
  "table": {
    "title": "表标题，体现 query 主题",
    "columns": ["指标", "数值", "期间", "来源", "原文依据"],
    "rows": [
      ["2024年营业收入", "8621亿元", "2024", "[1]", "销售收入8,621亿"]
    ]
  },
  "conclusion": "基于上表 2~4 句中文分析，数值须与表格一致",
  "methodology": "一句话说明本次从 N 条搜索结果中抽取了哪些类型的指标"
}
"""


@dataclass
class LLMSearchAnalysis:
    table: DataTable
    conclusion: str
    methodology: str
    search_refs: List[SearchReference]


async def extract_table_from_search(
    query: str,
    search_results: List[Dict[str, Any]],
    llm_callback: LLMCallback,
) -> Optional[LLMSearchAnalysis]:
    """把搜到的网页正文交给 LLM，返回数值表格与分析结论。"""
    if not search_results:
        return None

    pages = _format_search_pages(search_results)
    if not pages:
        return None

    user_prompt = json.dumps(
        {
            "query": query,
            "search_result_count": len(pages),
            "search_results": pages,
        },
        ensure_ascii=False,
        indent=2,
    )

    try:
        response = await llm_callback(user_prompt, _SYSTEM_PROMPT)
        parsed = _parse_json_response(response)
        if not parsed:
            logger.warning("[LLMSearchAnalyzer] LLM 返回无法解析为 JSON")
            return None

        table_raw = parsed.get("table") or {}
        columns = [str(c) for c in (table_raw.get("columns") or [])]
        rows = [
            [str(cell) for cell in row]
            for row in (table_raw.get("rows") or [])
            if isinstance(row, list)
        ]
        table = DataTable(
            title=table_raw.get("title") or f"「{query}」相关数值",
            columns=columns or ["指标", "数值", "期间", "来源", "原文依据"],
            rows=rows,
        )
        conclusion = str(parsed.get("conclusion") or "").strip()
        methodology = str(parsed.get("methodology") or "").strip()
        if not methodology:
            methodology = (
                f"基于 {len(pages)} 条网页搜索结果，"
                f"由 LLM 从正文中抽取与「{query}」相关的数值指标。"
            )

        refs = _build_search_refs(search_results)
        logger.info(
            f"[LLMSearchAnalyzer] 抽取完成：{len(rows)} 行数值，"
            f"来源 {len(refs)} 条"
        )
        return LLMSearchAnalysis(
            table=table,
            conclusion=conclusion,
            methodology=methodology,
            search_refs=refs,
        )
    except Exception as e:
        logger.error(f"[LLMSearchAnalyzer] LLM 抽取失败: {e}")
        return None


def _format_search_pages(search_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    pages: List[Dict[str, str]] = []
    for i, item in enumerate(search_results[:_MAX_SOURCES], 1):
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        body = (item.get("content") or item.get("snippet") or "").strip()
        if not title and not body:
            continue
        pages.append(
            {
                "index": str(i),
                "title": title or f"来源{i}",
                "url": url,
                "content": body[:_MAX_CHARS_PER_SOURCE],
            }
        )
    return pages


def _build_search_refs(search_results: List[Dict[str, Any]]) -> List[SearchReference]:
    refs: List[SearchReference] = []
    for item in search_results[:_MAX_SOURCES]:
        snippet = item.get("snippet") or item.get("content") or ""
        refs.append(
            SearchReference(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=snippet[:300] if snippet else "",
            )
        )
    return refs


def _parse_json_response(text: str) -> Optional[Dict[str, Any]]:
    raw = (text or "").strip()
    if "```" in raw:
        for part in raw.split("```"):
            chunk = part.strip()
            if chunk.startswith("json"):
                chunk = chunk[4:].strip()
            if chunk.startswith("{"):
                raw = chunk
                break
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None
