"""按用户 query 筛选与数据分析最相关的搜索结果。"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

_STOPWORDS = {
    "分析", "研究", "报告", "关于", "如何", "什么", "情况", "发展", "市场",
    "行业", "公司", "企业", "的", "与", "和", "及", "对", "为", "在", "年",
    "进行", "综合", "深度", "简要", "详细", "测试", "查询", "数据", "金融",
    "趋势", "变化", "概况", "概述", "中国", "全球", "产业", "新闻", "资讯",
    "报道", "记者", "来源", "新浪", "腾讯", "搜狐",
}

_TOPIC_KEYWORDS = (
    "营收", "收入", "营业收入", "利润", "净利润", "毛利", "毛利率",
    "资产", "负债", "增长", "趋势", "同比", "环比", "财务", "业绩",
    "财报", "估值", "市占率", "现金流",
)

_FINANCIAL_SIGNAL_RE = re.compile(
    r"(?:营业收入|销售收入|营收|净利润|归母净利润|业绩|毛利率|同比(?:增长|增幅)?|环比增长)"
)
_NUMERIC_FINANCIAL_RE = re.compile(
    r"(?:营收|收入|净利润|利润)[^。\n]{0,25}\d+(?:\.\d+)?(?:%|亿|万)"
    r"|\d+(?:\.\d+)?(?:亿|万)[^。\n]{0,20}(?:营收|收入|元)"
    r"|(?:同比|环比)[^。\n]{0,20}\d+(?:\.\d+)?\s*%"
)
_WEAK_TOPIC_WORDS = frozenset({"趋势", "增长", "同比", "环比"})
_FINANCIAL_TOPIC_WORDS = frozenset({
    "营收", "收入", "营业收入", "利润", "净利润", "财报", "业绩", "财务", "毛利率", "现金流",
})

_COMPANY_PATTERN = re.compile(r"([\u4e00-\u9fffA-Za-z]{2,10})\s*公司")
_TITLE_SUBJECT_PATTERN = re.compile(
    r"^[\s【\[\(\"']*([\u4e00-\u9fffA-Za-z·]{2,10})(?:公司|\s*[-－—:|：|｜])"
)


@dataclass
class QueryTerms:
    raw_query: str
    entities: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    years: List[str] = field(default_factory=list)


@dataclass
class SearchSelectionMeta:
    total_count: int
    selected_count: int
    query: str
    entity_terms: List[str]
    top_titles: List[str] = field(default_factory=list)

    def methodology_note(self) -> str:
        if self.selected_count == 0:
            ent = "、".join(self.entity_terms) or "查询主题"
            return (
                f"已从 {self.total_count} 条搜索结果中筛选，"
                f"未找到以「{ent}」为核心主体且与 prompt 相关的条目，故未进行数值分析。"
            )
        ent_part = ""
        if self.entity_terms:
            ent_part = f"（核心主体：{'、'.join(self.entity_terms)}）"
        titles = "；".join(self.top_titles[:3]) if self.top_titles else ""
        return (
            f"已从 {self.total_count} 条搜索结果中筛选出 {self.selected_count} 条"
            f"以目标主体为核心且与 prompt 相关的结果{ent_part}进行分析"
            + (f"，包括：{titles}" if titles else "")
            + "。"
        )


def _strip_query_noise(text: str, years: List[str]) -> str:
    work = text
    for y in years:
        work = work.replace(f"{y}年", " ").replace(y, " ")
    for kw in _STOPWORDS:
        work = work.replace(kw, " ")
    return re.sub(r"\s+", " ", work).strip()


def primary_entities(entities: List[str]) -> List[str]:
    short = [e for e in entities if not e.endswith("公司")]
    return short or list(entities)


def parse_query_terms(query: str) -> QueryTerms:
    q = (query or "").strip()
    years = sorted(set(re.findall(r"(20\d{2})", q)))

    entities: List[str] = []
    seen_ent: set = set()

    q_for_company = re.sub(r"20\d{2}年?", " ", q)
    for match in _COMPANY_PATTERN.finditer(q_for_company):
        name = match.group(1).strip().lstrip("年第")
        if re.search(r"\d", name) or len(name) < 2 or name in _STOPWORDS:
            continue
        if name.startswith("年"):
            continue
        for token in (name, f"{name}公司"):
            if token not in seen_ent:
                seen_ent.add(token)
                entities.append(token)

    work = _strip_query_noise(q, years)
    if not entities:
        for token in re.findall(r"[\u4e00-\u9fffA-Za-z]{2,10}", work):
            if token in _STOPWORDS or token in _TOPIC_KEYWORDS or re.search(r"\d", token):
                continue
            if token not in seen_ent:
                seen_ent.add(token)
                entities.append(token)

    topics = [kw for kw in _TOPIC_KEYWORDS if kw in q]
    return QueryTerms(raw_query=q, entities=entities, topics=topics, years=years)


def entity_terms_from_query(query: str) -> List[str]:
    return primary_entities(parse_query_terms(query).entities)


def _entity_matches_name(name: str, entities: List[str]) -> bool:
    if not name or not entities:
        return False
    for e in entities:
        if name == e:
            return True
        if name == f"{e}公司":
            return True
        if name.endswith("公司") and name[:-2] == e:
            return True
        if e.endswith("公司") and e[:-2] == name:
            return True
    return False


def _title_leading_brand(title: str) -> Optional[str]:
    match = re.match(r"^[\s【\[\(\"']*([\u4e00-\u9fffA-Za-z·]{2,10})", title.strip())
    if not match:
        return None
    name = re.split(r"[因被的对与和向给]", match.group(1))[0]
    return name if len(name) >= 2 else match.group(1)[:6]


def extract_title_subject(title: str) -> Optional[str]:
    if not title:
        return None
    head = title.strip()[:50]
    match = _TITLE_SUBJECT_PATTERN.match(head)
    if match:
        return match.group(1).strip()
    match = re.search(
        r"^[\s【\[\(\"']*([\u4e00-\u9fffA-Za-z·]{2,10})公司",
        head,
    )
    if match:
        return match.group(1).strip()
    return None


def _is_financial_query(topics: List[str]) -> bool:
    return bool(_FINANCIAL_TOPIC_WORDS.intersection(topics))


def _query_financial_topics(topics: List[str]) -> List[str]:
    return [t for t in topics if t in _FINANCIAL_TOPIC_WORDS and t not in _WEAK_TOPIC_WORDS]


def _has_financial_signal(text: str, topics: List[str]) -> bool:
    """与 prompt 主题一致：问营收则正文须出现营收/收入/可抽取数值，不接受「财务报表」等泛词。"""
    query_topics = _query_financial_topics(topics)
    if query_topics:
        if any(t in text for t in query_topics):
            return True
        if "营收" in query_topics and ("销售收入" in text or "营业收入" in text):
            return True
        if "收入" in query_topics and "销售收入" in text:
            return True
        return bool(_NUMERIC_FINANCIAL_RE.search(text))
    return bool(_FINANCIAL_SIGNAL_RE.search(text) or _NUMERIC_FINANCIAL_RE.search(text))


def _is_passing_mention(title: str, primaries: List[str]) -> bool:
    """标题以其他品牌为主、目标主体仅顺带出现（如「博世因向华为出货」）。"""
    leading = _title_leading_brand(title)
    if leading and not _entity_matches_name(leading, primaries):
        if any(e in title for e in primaries) and not any(
            title.startswith(e) for e in primaries
        ):
            return True
    return False


def _entity_finance_in_text(text: str, primaries: List[str]) -> bool:
    finance_words = r"(?:营收|收入|销售收入|营业收入|净利润|归母净利润|业绩)"
    for e in primaries:
        if re.search(
            rf"{re.escape(e)}(?:公司)?[^。\n]{{0,40}}{finance_words}",
            text,
        ):
            return True
        if re.search(
            rf"{finance_words}[^。\n]{{0,40}}{re.escape(e)}(?:公司)?",
            text,
        ):
            return True
    return False


def is_entity_core_subject(
    item: Dict[str, Any],
    entities: List[str],
    topics: Optional[List[str]] = None,
) -> bool:
    """目标主体须为文档核心；金融类 query 还须含财务/营收信号。"""
    primaries = primary_entities(entities)
    if not primaries:
        return True

    topics = topics or []
    financial_query = _is_financial_query(topics)
    title = item.get("title") or ""
    body = (item.get("content") or item.get("snippet") or "")[:1500]
    text = f"{title}\n{body}"

    if not any(e in text for e in primaries):
        return False

    if _is_passing_mention(title, primaries):
        return False

    if _entity_finance_in_text(text, primaries):
        return _has_financial_signal(text, topics) if financial_query else True

    if any(title.startswith(e) for e in primaries):
        if financial_query:
            return _entity_finance_in_text(text, primaries) and _has_financial_signal(
                text, topics
            )
        return True

    lead = body[:800]
    if sum(lead.count(e) for e in primaries) >= 2:
        return _has_financial_signal(text, topics) if financial_query else True

    return False


def _passes_selection_filters(
    item: Dict[str, Any],
    terms: QueryTerms,
    *,
    strict_core: bool,
    require_financial: bool,
) -> bool:
    text = _item_full_text(item)
    primaries = primary_entities(terms.entities)
    title = item.get("title") or ""

    if terms.entities:
        if not any(e in text for e in primaries):
            return False
        if _is_passing_mention(title, primaries):
            return False
        if strict_core:
            if not is_entity_core_subject(item, terms.entities, terms.topics):
                return False
        else:
            has_bind = _entity_finance_in_text(text, primaries) or (
                _NUMERIC_FINANCIAL_RE.search(text)
                and any(e in text for e in primaries)
            )
            if not has_bind:
                return False

    if require_financial and not _has_financial_signal(text, terms.topics):
        return False

    return True


def _item_full_text(item: Dict[str, Any]) -> str:
    title = item.get("title") or ""
    body = item.get("content") or item.get("snippet") or ""
    return f"{title}\n{body}"


def _year_in_text(text: str, years: List[str]) -> bool:
    if not years:
        return True
    return any(y in text or f"{y}年" in text for y in years)


def score_search_result(
    item: Dict[str, Any],
    terms: QueryTerms,
    *,
    apply_core_filter: bool = True,
) -> float:
    title = item.get("title") or ""
    body = item.get("content") or item.get("snippet") or ""
    text = _item_full_text(item)

    if not text.strip():
        return 0.0

    if apply_core_filter and terms.entities and not is_entity_core_subject(
        item, terms.entities, terms.topics
    ):
        return 0.0

    score = 0.0
    primaries = primary_entities(terms.entities)
    title_subject = extract_title_subject(title)

    for entity in primaries:
        if entity in title:
            score += 15.0
        if title_subject and _entity_matches_name(title_subject, [entity]):
            score += 20.0
        if entity in body:
            score += 8.0
        if _entity_finance_in_text(text, [entity]):
            score += 25.0

    for topic in terms.topics:
        if topic in title:
            score += 4.0
        if topic in body:
            score += 5.0

    for year in terms.years:
        if year in body or f"{year}年" in body:
            score += 6.0
        elif year in title or f"{year}年" in title:
            score += 4.0

    if terms.entities and terms.years and _year_in_text(text, terms.years):
        score += 5.0

    if _has_financial_signal(text, terms.topics):
        score += 10.0

    if item.get("source") == "user_document":
        score += 100.0

    if len(body) > 800:
        score += 1.0
    elif len(body) > 200:
        score += 0.5

    return score


def select_relevant_search_results(
    query: str,
    search_results: List[Dict[str, Any]],
    *,
    max_items: int = 8,
    min_score: float = 8.0,
    strict_core: bool = True,
    require_financial: Optional[bool] = None,
) -> Tuple[List[Dict[str, Any]], SearchSelectionMeta]:
    """返回与 query 最相关的搜索结果；金融类 prompt 默认要求正文含财务信号。"""
    terms = parse_query_terms(query)
    if require_financial is None:
        require_financial = _is_financial_query(terms.topics)

    total = len(search_results)
    display_entities = primary_entities(terms.entities) or terms.entities

    if not search_results:
        return [], SearchSelectionMeta(
            total_count=0, selected_count=0, query=query, entity_terms=display_entities
        )

    scored: List[Tuple[float, Dict[str, Any]]] = []
    for item in search_results:
        if not _passes_selection_filters(
            item, terms, strict_core=strict_core, require_financial=require_financial
        ):
            continue
        s = score_search_result(item, terms, apply_core_filter=False)
        if s > 0:
            scored.append((s, item))

    scored.sort(key=lambda x: x[0], reverse=True)

    if terms.entities and not scored:
        mode = "严格" if strict_core else "放宽"
        logger.warning(
            f"[SearchRelevance] ({mode}) 主体 {display_entities} 无匹配条目"
            f"（require_financial={require_financial}，共 {total} 条）"
        )
        return [], SearchSelectionMeta(
            total_count=total,
            selected_count=0,
            query=query,
            entity_terms=display_entities,
        )

    selected: List[Dict[str, Any]] = []
    for s, item in scored:
        if s < min_score:
            continue
        selected.append(item)
        if len(selected) >= max_items:
            break

    if not selected and scored:
        selected = [item for _, item in scored[:max_items]]

    meta = SearchSelectionMeta(
        total_count=total,
        selected_count=len(selected),
        query=query,
        entity_terms=display_entities,
        top_titles=[(i.get("title") or "")[:60] for i in selected[:5]],
    )

    if total > len(selected):
        mode = "严格" if strict_core else "放宽"
        logger.info(
            f"[SearchRelevance] ({mode}) 筛选 {len(selected)}/{total} 条"
            f"（主体={display_entities or '无'}，财务信号={require_financial}）"
        )

    return selected, meta


def expand_candidates_for_extraction(
    query: str,
    search_results: List[Dict[str, Any]],
    *,
    max_items: int = 8,
) -> Tuple[List[Dict[str, Any]], SearchSelectionMeta]:
    """从全部搜索中挑选「主体 + prompt 财务主题 + 可抽取数值语义」的候选。"""
    terms = parse_query_terms(query)
    primaries = primary_entities(terms.entities) or terms.entities
    total = len(search_results)
    scored: List[Tuple[float, Dict[str, Any]]] = []

    for item in search_results:
        text = _item_full_text(item)
        title = item.get("title") or ""
        if terms.entities:
            if not any(e in text for e in primaries):
                continue
            if _is_passing_mention(title, primaries):
                continue
        if not _has_financial_signal(text, terms.topics):
            continue
        if terms.entities and not (
            _entity_finance_in_text(text, primaries)
            or (_NUMERIC_FINANCIAL_RE.search(text) and any(e in text for e in primaries))
        ):
            continue
        s = score_search_result(item, terms, apply_core_filter=False)
        if s > 0:
            scored.append((s, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [item for _, item in scored[:max_items]]
    meta = SearchSelectionMeta(
        total_count=total,
        selected_count=len(selected),
        query=query,
        entity_terms=primaries,
        top_titles=[(i.get("title") or "")[:60] for i in selected[:5]],
    )
    if selected:
        logger.info(
            f"[SearchRelevance] 抽取扩展筛选 {len(selected)}/{total} 条"
            f"（主体={primaries}）"
        )
    return selected, meta


def select_relevant_search_results_with_fallback(
    query: str,
    search_results: List[Dict[str, Any]],
    **kwargs: Any,
) -> Tuple[List[Dict[str, Any]], SearchSelectionMeta]:
    """先严格筛选；无结果时逐级放宽。"""
    selected, meta = select_relevant_search_results(
        query, search_results, strict_core=True, max_items=8, **kwargs
    )
    if selected:
        return selected, meta

    logger.info("[SearchRelevance] 严格筛选无结果，尝试放宽（主体+财务语义）")
    selected, meta = select_relevant_search_results(
        query,
        search_results,
        strict_core=False,
        require_financial=True,
        min_score=5.0,
        max_items=8,
        **kwargs,
    )
    if selected:
        return selected, meta

    logger.info("[SearchRelevance] 放宽仍无结果，尝试抽取导向候选")
    return expand_candidates_for_extraction(query, search_results, max_items=8)
