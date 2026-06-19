from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from pypdf import PdfReader


def extract_pdf_pages(pdf_path: str | Path) -> List[Dict[str, object]]:
    """Extract text page by page from a PDF annual report."""

    reader = PdfReader(str(pdf_path))
    pages: List[Dict[str, object]] = []
    for index, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append({"page": index, "text": text})
    return pages
