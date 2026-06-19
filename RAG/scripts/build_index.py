from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "RAG" / "src"))

from rag_reports.indexer import build_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Chroma index for annual-report chunks.")
    parser.add_argument("--jsonl", default="RAG/data/jsonl/annual_reports.jsonl")
    parser.add_argument("--persist-dir", default="RAG/data/chroma_db")
    parser.add_argument("--collection", default="annual_report_rag")
    parser.add_argument("--env-file", default="financeRAG/rag/.env")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Do not skip existing Chroma ids. By default interrupted runs resume from existing ids.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Embedding request batch size. Some DashScope embedding models allow at most 10.",
    )
    args = parser.parse_args()

    stats = build_index(
        jsonl_path=args.jsonl,
        persist_dir=args.persist_dir,
        collection_name=args.collection,
        env_file=args.env_file,
        reset=args.reset,
        batch_size=args.batch_size,
        resume=not args.no_resume,
    )
    print(stats)


if __name__ == "__main__":
    main()
