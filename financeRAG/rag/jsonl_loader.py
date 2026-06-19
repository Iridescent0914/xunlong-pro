import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, Optional


@dataclass(frozen=True)
class ProcessedDocument:
    doc_id: str
    content: str
    metadata: Dict[str, Any]


def _metadata_value(value: Any) -> Optional[Any]:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, ensure_ascii=False)


def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    clean: Dict[str, Any] = {}
    for key, value in metadata.items():
        clean_value = _metadata_value(value)
        if clean_value is not None:
            clean[str(key)] = clean_value
    return clean


def iter_jsonl_files(input_path: str, pattern: str = "*.jsonl") -> Iterator[Path]:
    path = Path(input_path)
    if path.is_file():
        yield path
        return

    yield from sorted(path.glob(pattern))


def iter_processed_documents(
    input_path: str,
    pattern: str = "*.jsonl",
    source_filter: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    strict: bool = False,
) -> Iterator[ProcessedDocument]:
    """Stream processed FinanceRAG JSONL documents from disk."""

    for file_path in iter_jsonl_files(input_path, pattern):
        with file_path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    if strict:
                        raise
                    continue

                doc_id = item.get("doc_id")
                content = item.get("content")
                metadata = item.get("metadata") or {}

                if not doc_id or not content:
                    continue
                if source_filter and metadata.get("source") != source_filter:
                    continue
                if not _year_in_range(metadata.get("report_date"), year_from, year_to):
                    continue

                metadata = {
                    **metadata,
                    "chunk_index": item.get("chunk_index", 0),
                    "chunk_size": item.get("chunk_size", 0),
                    "chunk_overlap": item.get("chunk_overlap", 0),
                    "jsonl_file": file_path.name,
                    "jsonl_line": line_number,
                }

                yield ProcessedDocument(
                    doc_id=str(doc_id),
                    content=str(content),
                    metadata=sanitize_metadata(metadata),
                )


def _year_in_range(
    report_date: Optional[Any],
    year_from: Optional[int],
    year_to: Optional[int],
) -> bool:
    if year_from is None and year_to is None:
        return True
    if not report_date:
        return False

    year_text = str(report_date).strip()[:4]
    if not year_text.isdigit():
        return False

    year = int(year_text)
    if year_from is not None and year < year_from:
        return False
    if year_to is not None and year > year_to:
        return False
    return True
