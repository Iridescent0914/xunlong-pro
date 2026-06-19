"""Query the FinanceRAG Chroma index, optionally with an LLM answer."""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import chromadb
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from financeRAG.rag import RAGConfig, OpenAICompatibleEmbeddingClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query FinanceRAG Chroma index.")
    parser.add_argument("query", help="Question or search query.")
    parser.add_argument("--persist-dir", default=None)
    parser.add_argument("--collection", default=None)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--source", choices=["stock_news", "stock_earning_call"], default=None)
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--answer", action="store_true", help="Use LLM_MODEL to answer from retrieved context.")
    parser.add_argument("--env-file", default=None, help="RAG env file. Defaults to financeRAG/rag/.env.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = RAGConfig.from_env(args.env_file)

    embedding_client = OpenAICompatibleEmbeddingClient(
        api_key=config.embedding_api_key,
        base_url=config.embedding_base_url,
        model=config.embedding_model,
    )
    query_embedding = embedding_client.embed_texts([args.query])[0]

    chroma_client = chromadb.PersistentClient(
        path=args.persist_dir or config.chroma_persist_dir
    )
    collection = chroma_client.get_collection(
        name=args.collection or config.chroma_collection
    )

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=args.top_k,
        where=_build_where(args.source, args.symbol),
        include=["documents", "metadatas", "distances"],
    )

    docs = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    print("\n# Retrieved Context\n")
    for index, (doc, metadata, distance) in enumerate(zip(docs, metadatas, distances), 1):
        print(f"## {index}. distance={distance:.4f}")
        print(f"metadata={metadata}")
        print(doc[:1000])
        print()

    if args.answer:
        answer = answer_with_llm(args.query, docs, metadatas, config)
        print("\n# Answer\n")
        print(answer)

    return 0


def _build_where(source: Optional[str], symbol: Optional[str]) -> Optional[Dict[str, Any]]:
    filters = []
    if source:
        filters.append({"source": source})
    if symbol:
        filters.append({"symbol": symbol})
    if not filters:
        return None
    if len(filters) == 1:
        return filters[0]
    return {"$and": filters}


def answer_with_llm(
    query: str,
    docs,
    metadatas,
    config: RAGConfig,
) -> str:
    context_parts = []
    for i, (doc, metadata) in enumerate(zip(docs, metadatas), 1):
        context_parts.append(f"[{i}] metadata={metadata}\n{doc}")

    client = OpenAI(api_key=config.llm_api_key, base_url=config.llm_base_url)
    response = client.chat.completions.create(
        model=config.llm_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You answer financial questions using only the provided retrieved context. "
                    "If the context is insufficient, say so clearly."
                ),
            },
            {
                "role": "user",
                "content": f"Question: {query}\n\nContext:\n\n" + "\n\n".join(context_parts),
            },
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


if __name__ == "__main__":
    raise SystemExit(main())
