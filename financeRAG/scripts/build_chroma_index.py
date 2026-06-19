"""Build a Chroma vector index from processed FinanceRAG JSONL documents."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from financeRAG.rag import RAGConfig, OpenAICompatibleEmbeddingClient
from financeRAG.rag.chroma_indexer import build_chroma_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Embed processed FinanceRAG JSONL files and write vectors to Chroma."
    )
    parser.add_argument(
        "--profile",
        choices=["custom", "news-random-call-2025-2026"],
        default="news-random-call-2025-2026",
        help="Preset indexing profile. Default: random 10,000 news docs plus 2025-2026 earning calls.",
    )
    parser.add_argument(
        "--input",
        default="financeRAG/processed_data_optimized",
        help="Processed JSONL file or directory.",
    )
    parser.add_argument(
        "--pattern",
        default="*_batch_*.jsonl",
        help="Glob pattern when --input is a directory. Default avoids combined_documents.jsonl duplicates.",
    )
    parser.add_argument(
        "--persist-dir",
        default=None,
        help="Chroma persistent directory. Defaults to CHROMA_PERSIST_DIR or financeRAG/rag/chroma_db.",
    )
    parser.add_argument(
        "--collection",
        default=None,
        help="Chroma collection name. Defaults to CHROMA_COLLECTION or finance_rag.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Chroma write batch size.",
    )
    parser.add_argument(
        "--embedding-batch-size",
        type=int,
        default=None,
        help="Embedding API batch size. Defaults to EMBEDDING_MAX_BATCH_SIZE or 10.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of chunks to index for testing.",
    )
    parser.add_argument(
        "--source",
        choices=["stock_news", "stock_earning_call"],
        default=None,
        help="Optional source filter.",
    )
    parser.add_argument("--year-from", type=int, default=None, help="Minimum report_date year.")
    parser.add_argument("--year-to", type=int, default=None, help="Maximum report_date year.")
    parser.add_argument("--random-sample", type=int, default=None, help="Random sample size for custom mode.")
    parser.add_argument("--random-seed", type=int, default=42, help="Random sample seed.")
    parser.add_argument("--news-sample", type=int, default=10_000, help="News random sample size for preset mode.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate the Chroma collection before indexing.",
    )
    parser.add_argument(
        "--embedding-model",
        default=None,
        help="Embedding model override. Defaults to EMBEDDING_MODEL or text-embedding-v3.",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="RAG env file. Defaults to financeRAG/rag/.env.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = RAGConfig.from_env(args.env_file)

    embedding_model = _normalize_model(args.embedding_model or config.embedding_model)
    persist_dir = args.persist_dir or config.chroma_persist_dir
    collection_name = args.collection or config.chroma_collection

    logger.info(f"Embedding model: {embedding_model}")
    logger.info(f"Embedding base URL: {config.embedding_base_url}")
    logger.info(f"Chroma persist dir: {persist_dir}")
    logger.info(f"Chroma collection: {collection_name}")
    logger.info(f"Input: {args.input} ({args.pattern})")

    embedding_client = OpenAICompatibleEmbeddingClient(
        api_key=config.embedding_api_key,
        base_url=config.embedding_base_url,
        model=embedding_model,
        max_batch_size=args.embedding_batch_size or config.embedding_max_batch_size,
    )

    if args.profile == "news-random-call-2025-2026":
        stats = _build_news_random_call_recent(
            args=args,
            persist_dir=persist_dir,
            collection_name=collection_name,
            embedding_client=embedding_client,
        )
    else:
        stats = build_chroma_index(
            input_path=args.input,
            pattern=args.pattern,
            persist_dir=persist_dir,
            collection_name=collection_name,
            embedding_client=embedding_client,
            batch_size=args.batch_size,
            source_filter=args.source,
            year_from=args.year_from,
            year_to=args.year_to,
            limit=args.limit,
            random_sample=args.random_sample,
            random_seed=args.random_seed,
            reset=args.reset,
        )

    logger.info(f"Done. Indexed chunks: {stats.indexed_documents:,}")
    return 0


def _build_news_random_call_recent(
    args: argparse.Namespace,
    persist_dir: str,
    collection_name: str,
    embedding_client: OpenAICompatibleEmbeddingClient,
):
    logger.info(
        f"Preset profile: random {args.news_sample:,} stock_news docs + "
        "stock_earning_call docs from 2025-2026"
    )
    logger.info("Preset patterns: stock_news_batch_*.jsonl, stock_earning_call_batch_*.jsonl")

    news_stats = build_chroma_index(
        input_path=args.input,
        pattern="stock_news_batch_*.jsonl",
        persist_dir=persist_dir,
        collection_name=collection_name,
        embedding_client=embedding_client,
        batch_size=args.batch_size,
        source_filter="stock_news",
        random_sample=args.news_sample,
        random_seed=args.random_seed,
        reset=args.reset,
    )

    call_stats = build_chroma_index(
        input_path=args.input,
        pattern="stock_earning_call_batch_*.jsonl",
        persist_dir=persist_dir,
        collection_name=collection_name,
        embedding_client=embedding_client,
        batch_size=args.batch_size,
        source_filter="stock_earning_call",
        year_from=2025,
        year_to=2026,
        limit=args.limit,
        reset=False,
    )

    news_stats.indexed_documents += call_stats.indexed_documents
    news_stats.indexed_batches += call_stats.indexed_batches
    return news_stats


def _normalize_model(model: Optional[str]) -> str:
    return (model or "text-embedding-v3").replace(" ", "")


if __name__ == "__main__":
    raise SystemExit(main())
