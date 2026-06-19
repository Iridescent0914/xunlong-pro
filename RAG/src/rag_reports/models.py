from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class CompanyTarget:
    symbol: str
    name: str
    country: str
    source: str
    landing_pages: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    market: Optional[str] = None
    org_id: Optional[str] = None
    known_reports: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class CrawlConfig:
    target_years: List[int]
    max_reports_per_company: int
    companies: List[CompanyTarget]


@dataclass(frozen=True)
class ReportRecord:
    symbol: str
    company: str
    country: str
    source: str
    report_year: int
    title: str
    url: str
    local_pdf: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def load_crawl_config(path: str | Path) -> CrawlConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return CrawlConfig(
        target_years=[int(year) for year in raw.get("target_years", [])],
        max_reports_per_company=int(raw.get("max_reports_per_company", 3)),
        companies=[
            CompanyTarget(
                symbol=item["symbol"],
                name=item["name"],
                country=item.get("country", ""),
                source=item["source"],
                landing_pages=list(item.get("landing_pages", [])),
                keywords=list(item.get("keywords", [])),
                market=item.get("market"),
                org_id=item.get("org_id"),
                known_reports=list(item.get("known_reports", [])),
            )
            for item in raw.get("companies", [])
        ],
    )
