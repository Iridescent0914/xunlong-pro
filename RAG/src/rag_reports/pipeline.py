from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .chunker import chunk_pages
from .models import ReportRecord, load_crawl_config
from .pdf_parser import extract_pdf_pages
from .sources import discover_reports, download_report

logger = logging.getLogger(__name__)


def run_pdf_rag_pipeline(
    config_path: str,
    pdf_dir: str,
    jsonl_path: str,
    chunk_size: int = 1200,
    overlap: int = 150,
    dry_run: bool = False,
    companies: Optional[Iterable[str]] = None,
    years: Optional[Iterable[int]] = None,
    limit_reports: Optional[int] = None,
    append: bool = False,
) -> Dict[str, int]:
    """Discover annual-report PDFs, extract text, and write RAG JSONL chunks."""

    if dry_run:
        return discover_reports_only(
            config_path=config_path,
            manifest_path=str(Path(jsonl_path).with_suffix(".manifest.json")),
            companies=companies,
            years=years,
            limit_reports=limit_reports,
        )

    download_stats = download_reports_only(
        config_path=config_path,
        pdf_dir=pdf_dir,
        manifest_path=str(Path(jsonl_path).with_suffix(".manifest.json")),
        companies=companies,
        years=years,
        limit_reports=limit_reports,
    )
    extract_stats = extract_existing_pdfs(
        config_path=config_path,
        pdf_dir=pdf_dir,
        jsonl_path=jsonl_path,
        chunk_size=chunk_size,
        overlap=overlap,
        companies=companies,
        years=years,
        limit_reports=limit_reports,
        append=append,
    )
    return {**download_stats, **extract_stats}


def discover_reports_only(
    config_path: str,
    manifest_path: str,
    companies: Optional[Iterable[str]] = None,
    years: Optional[Iterable[int]] = None,
    limit_reports: Optional[int] = None,
) -> Dict[str, int]:
    """Discover report URLs and write a manifest without touching JSONL."""

    config = load_crawl_config(config_path)
    manifest_output = Path(manifest_path)
    manifest_output.parent.mkdir(parents=True, exist_ok=True)

    stats = {
        "companies": 0,
        "discovered_reports": 0,
    }
    manifest: List[Dict[str, object]] = _load_existing_manifest(manifest_path) if append else []
    company_filter = {item.upper() for item in companies or []}

    for company in config.companies:
        if company_filter and company.symbol.upper() not in company_filter:
            continue

        stats["companies"] += 1
        reports = _select_company_reports(company, _target_years(config.target_years, years), config.max_reports_per_company, limit_reports)
        stats["discovered_reports"] += len(reports)
        logger.info(f"{company.symbol}: discovered {len(reports)} reports")
        for report in reports:
            manifest.append({"report": asdict(report), "dry_run": True})

    manifest_output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Wrote manifest to {manifest_output}")
    return stats


def download_reports_only(
    config_path: str,
    pdf_dir: str,
    manifest_path: str,
    companies: Optional[Iterable[str]] = None,
    years: Optional[Iterable[int]] = None,
    limit_reports: Optional[int] = None,
) -> Dict[str, int]:
    """Discover and download annual-report PDFs without touching JSONL."""

    config = load_crawl_config(config_path)
    manifest_output = Path(manifest_path)
    manifest_output.parent.mkdir(parents=True, exist_ok=True)

    stats = {
        "companies": 0,
        "discovered_reports": 0,
        "downloaded_reports": 0,
        "failed_reports": 0,
    }
    manifest: List[Dict[str, object]] = []
    company_filter = {item.upper() for item in companies or []}

    for company in config.companies:
        if company_filter and company.symbol.upper() not in company_filter:
            continue

        stats["companies"] += 1
        reports = _select_company_reports(company, _target_years(config.target_years, years), config.max_reports_per_company, limit_reports)
        stats["discovered_reports"] += len(reports)
        logger.info(f"{company.symbol}: discovered {len(reports)} reports")

        for report in reports:
            try:
                downloaded = download_report(report, pdf_dir)
            except Exception as exc:
                stats["failed_reports"] += 1
                manifest.append(
                    {
                        "report": asdict(report),
                        "status": "download_failed",
                        "error": str(exc),
                    }
                )
                logger.warning(
                    "Skipped failed download for %s %s: %s",
                    report.symbol,
                    report.report_year,
                    exc,
                )
                continue

            stats["downloaded_reports"] += 1
            manifest.append({"report": asdict(downloaded), "status": "downloaded"})
            manifest_output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Wrote manifest to {manifest_output}")
    return stats


def extract_existing_pdfs(
    config_path: str,
    pdf_dir: str,
    jsonl_path: str,
    chunk_size: int = 1200,
    overlap: int = 150,
    companies: Optional[Iterable[str]] = None,
    years: Optional[Iterable[int]] = None,
    limit_reports: Optional[int] = None,
    append: bool = False,
) -> Dict[str, int]:
    """Extract text chunks from already downloaded PDFs and write JSONL."""

    config = load_crawl_config(config_path)
    output_path = Path(jsonl_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = output_path.with_suffix(".manifest.json")

    stats = {
        "companies": 0,
        "discovered_reports": 0,
        "existing_pdfs": 0,
        "failed_reports": 0,
        "chunks": 0,
    }
    manifest: List[Dict[str, object]] = []
    company_filter = {item.upper() for item in companies or []}

    mode = "a" if append else "w"
    with output_path.open(mode, encoding="utf-8") as writer:
        for company in config.companies:
            if company_filter and company.symbol.upper() not in company_filter:
                continue

            stats["companies"] += 1
            reports = _select_company_reports(company, _target_years(config.target_years, years), config.max_reports_per_company, limit_reports)
            stats["discovered_reports"] += len(reports)

            for report in reports:
                local_pdf = Path(pdf_dir) / f"{report.symbol}_{report.report_year}_annual_report.pdf"
                if not local_pdf.exists() or local_pdf.stat().st_size == 0:
                    manifest.append(
                        {
                            "report": asdict(report),
                            "status": "missing_pdf",
                            "expected_pdf": str(local_pdf),
                        }
                    )
                    continue

                downloaded = ReportRecord(
                    symbol=report.symbol,
                    company=report.company,
                    country=report.country,
                    source=report.source,
                    report_year=report.report_year,
                    title=report.title,
                    url=report.url,
                    local_pdf=str(local_pdf),
                    metadata=report.metadata,
                )
                stats["existing_pdfs"] += 1

                try:
                    pages = extract_pdf_pages(local_pdf)
                except Exception as exc:
                    stats["failed_reports"] += 1
                    manifest.append(
                        {
                            "report": asdict(downloaded),
                            "status": "parse_failed",
                            "error": str(exc),
                        }
                    )
                    logger.warning(
                        "Skipped failed parse for %s %s: %s",
                        downloaded.symbol,
                        downloaded.report_year,
                        exc,
                    )
                    continue

                chunk_count = 0
                for chunk in chunk_pages(downloaded, pages, chunk_size=chunk_size, overlap=overlap):
                    writer.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                    chunk_count += 1

                stats["chunks"] += chunk_count
                manifest.append(
                    {
                        "report": asdict(downloaded),
                        "status": "extracted",
                        "pages": len(pages),
                        "chunks": chunk_count,
                    }
                )
                manifest_path.write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                logger.info(
                    f"{downloaded.symbol} {downloaded.report_year}: "
                    f"{len(pages)} pages, {chunk_count} chunks"
                )

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Wrote JSONL to {output_path}")
    logger.info(f"Wrote manifest to {manifest_path}")
    return stats


def _select_company_reports(
    company,
    target_years: List[int],
    max_reports_per_company: int,
    limit_reports: Optional[int],
) -> List[ReportRecord]:
    reports = discover_reports(company, target_years)
    reports = _latest_n_by_company(reports, max_reports_per_company)
    if limit_reports is not None:
        reports = reports[:limit_reports]
    return reports


def _target_years(default_years: List[int], years: Optional[Iterable[int]]) -> List[int]:
    if years is None:
        return default_years
    wanted = {int(year) for year in years}
    return [year for year in default_years if year in wanted]


def _load_existing_manifest(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return raw if isinstance(raw, list) else []


def _latest_n_by_company(reports: List[ReportRecord], limit: int) -> List[ReportRecord]:
    by_year: Dict[int, ReportRecord] = {}
    for report in sorted(reports, key=lambda item: item.report_year, reverse=True):
        by_year.setdefault(report.report_year, report)
    return list(by_year.values())[:limit]
