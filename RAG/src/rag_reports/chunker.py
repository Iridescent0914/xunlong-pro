from __future__ import annotations

import hashlib
from typing import Dict, Iterable, Iterator, List

from .cleaner import clean_report_text
from .models import ReportRecord


def _stable_id(parts: Iterable[object]) -> str:
    raw = "|".join(str(part) for part in parts)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def chunk_pages(
    report: ReportRecord,
    pages: List[Dict[str, object]],
    chunk_size: int = 1200,
    overlap: int = 150,
) -> Iterator[Dict[str, object]]:
    """Yield JSONL-ready chunks from extracted PDF pages."""

    chunk_index = 0
    carry = ""
    carry_start_page = None

    for page in pages:
        page_number = int(page["page"])
        text = clean_report_text(str(page.get("text") or ""))
        if not text:
            continue

        if carry:
            text = carry + "\n" + text
            start_page = carry_start_page or page_number
        else:
            start_page = page_number

        cursor = 0
        while cursor < len(text):
            end = min(cursor + chunk_size, len(text))
            chunk_text = text[cursor:end].strip()
            if len(chunk_text) >= 80:
                yield {
                    "doc_id": _stable_id(
                        [
                            report.symbol,
                            report.report_year,
                            report.url,
                            start_page,
                            page_number,
                            chunk_index,
                        ]
                    ),
                    "content": chunk_text,
                    "metadata": {
                        "source": "annual_report_pdf",
                        "company": report.company,
                        "symbol": report.symbol,
                        "country": report.country,
                        "report_year": report.report_year,
                        "report_type": "annual_report",
                        "title": report.title,
                        "source_url": report.url,
                        "local_pdf": report.local_pdf or "",
                        "page_start": start_page,
                        "page_end": page_number,
                        **report.metadata,
                    },
                    "chunk_index": chunk_index,
                    "chunk_size": chunk_size,
                    "chunk_overlap": overlap,
                }
                chunk_index += 1

            if end >= len(text):
                break
            cursor = max(end - overlap, cursor + 1)

        carry = text[-overlap:] if overlap > 0 else ""
        carry_start_page = page_number
