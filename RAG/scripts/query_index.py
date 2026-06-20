from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "RAG" / "src"))

from rag_reports.indexer import build_evidence_pack, print_query_results, query_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the annual-report Chroma index.")
    parser.add_argument("query")
    parser.add_argument("--persist-dir", default="RAG/data/chroma_db")
    parser.add_argument("--collection", default="annual_report_rag")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--pack-json", action="store_true", help="Output docs/rag输出格式.md evidence pack JSON.")
    parser.add_argument("--output", help="Optional path to write evidence pack JSON.")
    args = parser.parse_args()

    rows = query_index(
        query=args.query,
        persist_dir=args.persist_dir,
        collection_name=args.collection,
        env_file=args.env_file,
        top_k=args.top_k,
    )
    if args.pack_json:
        pack = build_evidence_pack(args.query, rows, top_k=args.top_k)
        text = json.dumps(pack, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(text, encoding="utf-8")
        print(text)
    else:
        print_query_results(rows)


if __name__ == "__main__":
    main()
