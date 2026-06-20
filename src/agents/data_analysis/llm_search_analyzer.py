"""将网页搜索结果直接交给 LLM，抽取与用户 query 相关的数值表格。"""

import json
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

from loguru import logger

from .schemas import DataTable, SearchReference

LLMCallback = Callable[[str, str], Awaitable[str]]

_MAX_SOURCES = 10
_MAX_CHARS_PER_SOURCE = 2500
_VALUE_COL_CN = "数值"
_CNY_AMOUNT_RE = re.compile(
    r"(-?\d[\d,]*(?:\.\d+)?)\s*(万亿|亿元|亿|万元|万|元)?",
)

_SYSTEM_PROMPT = """你是专业的金融与商业数据分析助手。

任务：阅读用户提供的多篇网页搜索结果和 RAG 检索证据，针对用户的「分析问题」，抽取所有在原文中有明确文字依据的数值指标，整理成一张 Markdown 数据表。

## 抽取规则（必须严格遵守）

1. **禁止编造**：所有数值必须能在对应来源正文中找到原文依据；禁止估算、外推、补全或合并不同来源的冲突数字。
2. **主题相关**：只抽取与用户 query 直接相关的指标（例如 query 问「华为2024年营收」→ 抽营收、收入、净利润、同比增长、研发投入等；不要抽无关公司的数据）。
3. **单位统一**：同一表格中所有人民币金额必须使用同一种单位（亿元、万元或元），禁止混用；系统会按数值量级自动统一，大额指标优先用「亿元」，小额指标用「万元」或「元」；百分比仍保留 `%`。
4. **保留期间**：有年份/季度则写入「期间」列。
5. **来源可追溯**：每行必须在「来源」列标注 `[W1]` / `[W2]`（网页证据）或 `[R1]` / `[R2]`（RAG 证据），不要使用无前缀的 `[1]`，在「原文依据」列摘录 ≤40 字的原文片段。
6. **冲突处理**：若不同来源对同一指标给出不同数值，分多行列出，不要取平均或自行选择。
7. **英文金额单位**：`$1.86B` / `$1.86 billion` 必须保留为 `$1.86B` 或准确转换为 `18.6 亿美元`；禁止写成 `1.86 亿美元`。`$6.95B` 应为 `69.5 亿美元`，不是 `6.95 亿美元`。`$7.30B to $7.40B` 应为 `73 亿至 74 亿美元`。
8. **空结果**：若所有来源均无相关数值，`rows` 返回空数组，`conclusion` 说明原因。

## 输出格式

只输出一个 JSON 对象，不要 markdown 代码块以外的任何文字：

{
  "table": {
    "title": "表标题，体现 query 主题",
    "columns": ["指标", "数值", "期间", "来源", "原文依据"],
    "rows": [
      ["2024年营业收入", "8621亿元", "2024", "[W1]", "销售收入8,621亿"]
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
    rag_evidence: Optional[List[Any]] = None,
) -> Optional[LLMSearchAnalysis]:
    """把搜到的网页正文与 RAG 证据交给 LLM，返回数值表格与分析结论。"""
    pages = _format_search_pages(search_results)
    rag_pages = _format_rag_pages(rag_evidence or [])
    if not pages and not rag_pages:
        return None

    user_prompt = json.dumps(
        {
            "query": query,
            "search_result_count": len(pages),
            "search_results": pages,
            "rag_result_count": len(rag_pages),
            "rag_results": rag_pages,
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
        table = normalize_table_monetary_units(table)
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
                "index": f"W{i}",
                "title": title or f"来源{i}",
                "url": url,
                "content": body[:_MAX_CHARS_PER_SOURCE],
            }
        )
    return pages


def _format_rag_pages(rag_evidence: List[Any]) -> List[Dict[str, str]]:
    pages: List[Dict[str, str]] = []
    for i, item in enumerate(rag_evidence[:_MAX_SOURCES], 1):
        if hasattr(item, "model_dump"):
            raw = item.model_dump()
        elif isinstance(item, dict):
            raw = item
        else:
            continue

        title = str(raw.get("title") or raw.get("source") or f"RAG证据{i}").strip()
        source = str(raw.get("source") or raw.get("doc_type") or "financial_rag").strip()
        body = str(raw.get("content") or raw.get("summary") or "").strip()
        if not title and not body:
            continue
        pages.append(
            {
                "index": f"R{i}",
                "title": title or f"RAG证据{i}",
                "source": source,
                "url": str(raw.get("url") or ""),
                "score": str(raw.get("score") or ""),
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


def normalize_table_monetary_units(table: DataTable) -> DataTable:
    """将表格中的人民币金额统一为同一单位（亿元/万元/元），便于柱状图比较。"""
    if not table.rows:
        return table

    value_idx = _value_column_index(table.columns)
    if value_idx < 0:
        return table

    parsed_rows: List[tuple[List[str], Optional[float]]] = []
    max_yuan = 0.0

    for row in table.rows:
        cells = [str(cell) for cell in row]
        if value_idx >= len(cells):
            parsed_rows.append((cells, None))
            continue

        raw_value = cells[value_idx]
        if _is_percent_value(raw_value):
            parsed_rows.append((cells, None))
            continue

        yuan_value = _parse_cny_amount_to_yuan(raw_value)
        if yuan_value is None:
            parsed_rows.append((cells, None))
            continue

        max_yuan = max(max_yuan, abs(yuan_value))
        parsed_rows.append((cells, yuan_value))

    if max_yuan <= 0:
        return table

    unit_label = _choose_cny_display_unit(max_yuan)
    normalized_rows: List[List[str]] = []
    normalized_any = False

    for cells, yuan_value in parsed_rows:
        if yuan_value is None:
            normalized_rows.append(cells)
            continue
        cells[value_idx] = _format_cny_amount(yuan_value, unit_label)
        normalized_any = True
        normalized_rows.append(cells)

    if normalized_any:
        columns = [str(col) for col in table.columns]
        if value_idx < len(columns):
            columns[value_idx] = _ensure_unit_column_name(columns[value_idx], unit_label)
        table.columns = columns

    table.rows = normalized_rows
    return table


def _value_column_index(columns: List[str]) -> int:
    for idx, col in enumerate(columns):
        if _VALUE_COL_CN in col:
            return idx
    return 1 if len(columns) > 1 else -1


def _is_percent_value(text: str) -> bool:
    lowered = str(text)
    return "%" in lowered or "％" in lowered


def _parse_cny_amount_to_yuan(text: str) -> Optional[float]:
    raw = str(text or "").strip()
    if not raw or _is_percent_value(raw):
        return None
    if re.search(r"(?i)\$|usd|美元|美金", raw):
        return None

    cleaned = raw.replace(",", "").replace("，", "").replace(" ", "")
    match = _CNY_AMOUNT_RE.search(cleaned)
    if not match:
        return None

    try:
        number = float(match.group(1).replace(",", ""))
    except ValueError:
        return None

    unit = (match.group(2) or "").strip()
    if unit == "万亿":
        return number * 1_000_000_000_000
    if unit in ("亿", "亿元"):
        return number * 100_000_000
    if unit in ("万", "万元"):
        return number * 10_000
    if unit == "元":
        return number
    if unit == "" and number >= 1_000_000:
        return number
    return None


def _choose_cny_display_unit(max_yuan: float) -> str:
    """按表格最大金额选择展示单位，避免小额数据被写成极小亿元数。"""
    if max_yuan >= 100_000_000:
        return "亿元"
    if max_yuan >= 10_000:
        return "万元"
    return "元"


def _format_cny_amount(yuan: float, unit_label: str) -> str:
    if unit_label == "亿元":
        display = yuan / 100_000_000
    elif unit_label == "万元":
        display = yuan / 10_000
    else:
        display = yuan

    rounded = round(display, 2)
    if abs(rounded - round(rounded)) < 1e-9:
        return f"{int(round(rounded))}{unit_label}"
    text = f"{rounded:.2f}".rstrip("0").rstrip(".")
    return f"{text}{unit_label}"


def _ensure_unit_column_name(name: str, unit_label: str) -> str:
    if unit_label in name:
        return name
    base = re.sub(r"[（(][^）)]*[）)]", "", name).strip() or _VALUE_COL_CN
    if base == _VALUE_COL_CN:
        return f"数值（{unit_label}）"
    return f"{base}（{unit_label}）"
