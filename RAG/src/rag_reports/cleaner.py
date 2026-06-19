from __future__ import annotations

import re


_PAGE_NO_RE = re.compile(r"^\s*(?:page\s*)?\d+\s*(?:/|of)?\s*\d*\s*$", re.IGNORECASE)
_SPACE_RE = re.compile(r"[ \t\u00a0]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


def clean_report_text(text: str) -> str:
    """Normalize extracted report text while keeping paragraph boundaries."""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u200b", "").replace("\ufeff", "")
    lines = []
    for line in text.splitlines():
        line = _SPACE_RE.sub(" ", line).strip()
        if not line:
            lines.append("")
            continue
        if _PAGE_NO_RE.match(line):
            continue
        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = _MULTI_NEWLINE_RE.sub("\n\n", cleaned)
    return cleaned.strip()
