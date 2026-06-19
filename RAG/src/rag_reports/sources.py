from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .models import CompanyTarget, ReportRecord


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _detect_year(text: str, target_years: Iterable[int]) -> int | None:
    cn_annual_match = re.search(r"(20\d{2})\s*年\s*年度报告", text)
    if cn_annual_match:
        year = int(cn_annual_match.group(1))
        if year in target_years:
            return year
        return None

    for year in target_years:
        if str(year) in text:
            return int(year)
    matches = re.findall(r"20\d{2}", text)
    for match in matches:
        year = int(match)
        if year in target_years:
            return year
    return None


def _looks_like_report(label: str, keywords: List[str]) -> bool:
    haystack = label.lower()
    if "proxy" in haystack and "annual report" not in haystack:
        return False
    if keywords and any(keyword.lower() in haystack for keyword in keywords):
        return True
    return "annual report" in haystack or "10-k" in haystack or "年度报告" in haystack


class IRPdfCrawler:
    """Generic crawler for investor-relations pages that link annual-report PDFs."""

    def discover(self, company: CompanyTarget, target_years: List[int]) -> List[ReportRecord]:
        reports = self._known_reports(company, target_years)

        for page_url in company.landing_pages:
            response = requests.get(page_url, headers=DEFAULT_HEADERS, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            for anchor in soup.find_all("a", href=True):
                href = str(anchor["href"]).strip()
                text = " ".join(anchor.get_text(" ", strip=True).split())
                absolute_url = urljoin(page_url, href)
                label = f"{text} {absolute_url}"
                if ".pdf" not in absolute_url.lower():
                    continue
                if not _looks_like_report(label, company.keywords):
                    continue

                year = _detect_year(label, target_years)
                if year is None:
                    continue

                reports.append(
                    ReportRecord(
                        symbol=company.symbol,
                        company=company.name,
                        country=company.country,
                        source=company.source,
                        report_year=year,
                        title=text or f"{company.name} {year} annual report",
                        url=absolute_url,
                        metadata={"landing_page": page_url},
                    )
                )

        return _dedupe_reports(reports)

    def _known_reports(
        self, company: CompanyTarget, target_years: List[int]
    ) -> List[ReportRecord]:
        reports: List[ReportRecord] = []
        for item in company.known_reports:
            year = int(item.get("year", 0))
            if year not in target_years:
                continue
            reports.append(
                ReportRecord(
                    symbol=company.symbol,
                    company=company.name,
                    country=company.country,
                    source=company.source,
                    report_year=year,
                    title=item.get("title") or f"{company.name} {year} annual report",
                    url=item["url"],
                    metadata={"configured": True},
                )
            )
        return reports


class CninfoCrawler:
    """Crawler for Chinese A-share annual-report PDFs exposed by CNINFO."""

    API_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
    PDF_BASE_URL = "http://static.cninfo.com.cn/"

    def discover(self, company: CompanyTarget, target_years: List[int]) -> List[ReportRecord]:
        reports: List[ReportRecord] = []
        headers = {
            **DEFAULT_HEADERS,
            "Referer": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch",
            "Origin": "http://www.cninfo.com.cn",
        }

        stock_values = [company.symbol]
        if company.org_id:
            stock_values.insert(0, f"{company.symbol},{company.org_id}")
        search_keys = ["", company.symbol, company.name]
        column = "sse" if company.market == "sh" else "szse"

        for stock_value in stock_values:
            reports.extend(
                self._query_company(
                    company,
                    target_years,
                    headers,
                    column=column,
                    stock=stock_value,
                    searchkey="",
                )
            )
            if reports:
                return _dedupe_reports(reports)

        for searchkey in search_keys:
            if not searchkey:
                continue
            reports.extend(
                self._query_company(
                    company,
                    target_years,
                    headers,
                    column=column,
                    stock="",
                    searchkey=searchkey,
                )
            )
            if reports:
                return _dedupe_reports(reports)

        return _dedupe_reports(reports)

    def _query_company(
        self,
        company: CompanyTarget,
        target_years: List[int],
        headers: Dict[str, str],
        column: str,
        stock: str,
        searchkey: str,
    ) -> List[ReportRecord]:
        reports: List[ReportRecord] = []
        for page_num in range(1, 4):
            data = {
                "pageNum": page_num,
                "pageSize": 30,
                "column": column,
                "tabName": "fulltext",
                "plate": "",
                "stock": stock,
                "searchkey": searchkey,
                "secid": "",
                "category": "category_ndbg_szsh",
                "trade": "",
                "seDate": "",
                "sortName": "",
                "sortType": "",
                "isHLtitle": "true",
            }
            response = requests.post(self.API_URL, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            payload = response.json()
            announcements = payload.get("announcements") or []
            if not announcements:
                break

            for item in announcements:
                title = re.sub(r"<.*?>", "", item.get("announcementTitle") or "")
                url_path = item.get("adjunctUrl") or ""
                year = _detect_year(title, target_years)
                if year is None:
                    continue
                if "摘要" in title or "英文" in title:
                    continue
                if not _looks_like_report(title, company.keywords):
                    continue

                reports.append(
                    ReportRecord(
                        symbol=company.symbol,
                        company=company.name,
                        country=company.country,
                        source=company.source,
                        report_year=year,
                        title=title,
                        url=urljoin(self.PDF_BASE_URL, url_path),
                        metadata={
                            "announcement_id": item.get("announcementId", ""),
                            "announcement_time": item.get("announcementTime", ""),
                        },
                    )
                )

        return reports


def discover_reports(company: CompanyTarget, target_years: List[int]) -> List[ReportRecord]:
    if company.source == "cninfo":
        return CninfoCrawler().discover(company, target_years)
    if company.source == "ir_pdf":
        return IRPdfCrawler().discover(company, target_years)
    raise ValueError(f"Unsupported report source: {company.source}")


def download_report(report: ReportRecord, output_dir: str | Path) -> ReportRecord:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    file_name = f"{report.symbol}_{report.report_year}_annual_report.pdf"
    pdf_path = output / file_name

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        response = requests.get(report.url, headers=DEFAULT_HEADERS, timeout=60)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "pdf" not in content_type and not report.url.lower().endswith(".pdf"):
            raise ValueError(f"URL did not return a PDF: {report.url}")
        pdf_path.write_bytes(response.content)

    return ReportRecord(
        symbol=report.symbol,
        company=report.company,
        country=report.country,
        source=report.source,
        report_year=report.report_year,
        title=report.title,
        url=report.url,
        local_pdf=str(pdf_path),
        metadata=report.metadata,
    )


def _dedupe_reports(reports: List[ReportRecord]) -> List[ReportRecord]:
    seen: Dict[tuple[str, int, str], ReportRecord] = {}
    for report in reports:
        key = (report.symbol, report.report_year, report.url)
        seen[key] = report
    return sorted(seen.values(), key=lambda item: (item.symbol, -item.report_year, item.url))
