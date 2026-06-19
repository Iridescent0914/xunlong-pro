from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "RAG" / "src"))

from rag_reports.pipeline import download_reports_only


def main() -> None:
    parser = argparse.ArgumentParser(description="Download annual-report PDFs only.")
    parser.add_argument("--config", default="RAG/config/targets.json")
    parser.add_argument("--pdf-dir", default="RAG/data/pdfs")
    parser.add_argument("--manifest", default="RAG/data/jsonl/download_manifest.json")
    parser.add_argument(
        "--company",
        action="append",
        help="Only process one company symbol. Can be used multiple times.",
    )
    parser.add_argument("--limit-reports", type=int, default=None)
    parser.add_argument("--year", action="append", type=int, help="Only download one report year. Can be used multiple times.")
    args = parser.parse_args()

    stats = download_reports_only(
        config_path=args.config,
        pdf_dir=args.pdf_dir,
        manifest_path=args.manifest,
        companies=args.company,
        years=args.year,
        limit_reports=args.limit_reports,
    )
    print(stats)


if __name__ == "__main__":
    main()
