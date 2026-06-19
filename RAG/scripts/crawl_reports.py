from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "RAG" / "src"))

from rag_reports.pipeline import run_pdf_rag_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Download annual-report PDFs and build JSONL chunks.")
    parser.add_argument("--config", default="RAG/config/targets.json")
    parser.add_argument("--pdf-dir", default="RAG/data/pdfs")
    parser.add_argument("--jsonl", default="RAG/data/jsonl/annual_reports.jsonl")
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=150)
    parser.add_argument(
        "--company",
        action="append",
        help="Only process one company symbol. Can be used multiple times, e.g. --company AAPL --company MSFT.",
    )
    parser.add_argument("--limit-reports", type=int, default=None)
    parser.add_argument("--year", action="append", type=int, help="Only process one report year. Can be used multiple times.")
    parser.add_argument("--append", action="store_true", help="Append chunks to the JSONL instead of overwriting it.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    stats = run_pdf_rag_pipeline(
        config_path=args.config,
        pdf_dir=args.pdf_dir,
        jsonl_path=args.jsonl,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        dry_run=args.dry_run,
        companies=args.company,
        years=args.year,
        limit_reports=args.limit_reports,
        append=args.append,
    )
    print(stats)


if __name__ == "__main__":
    main()
