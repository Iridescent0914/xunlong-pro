from dataclasses import dataclass
from typing import Iterable, List, Optional

import chromadb
from loguru import logger
from tqdm import tqdm

from .embedding_client import OpenAICompatibleEmbeddingClient
from .jsonl_loader import ProcessedDocument, iter_processed_documents


@dataclass
class IndexStats:
    indexed_documents: int = 0
    indexed_batches: int = 0


def _batched(items: Iterable[ProcessedDocument], batch_size: int):
    batch: List[ProcessedDocument] = []
    for item in items:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def build_chroma_index(
    input_path: str,
    persist_dir: str,
    collection_name: str,
    embedding_client: OpenAICompatibleEmbeddingClient,
    pattern: str = "*_batch_*.jsonl",
    batch_size: int = 64,
    source_filter: Optional[str] = None,
    limit: Optional[int] = None,
    reset: bool = False,
) -> IndexStats:
    """Embed processed JSONL documents and write vectors into Chroma."""

    chroma_client = chromadb.PersistentClient(path=persist_dir)
    if reset:
        try:
            chroma_client.delete_collection(collection_name)
            logger.info(f"Deleted existing Chroma collection: {collection_name}")
        except Exception:
            pass

    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    documents = iter_processed_documents(
        input_path=input_path,
        pattern=pattern,
        source_filter=source_filter,
    )

    if limit is not None:
        documents = _limited(documents, limit)

    stats = IndexStats()
    progress = tqdm(desc="Indexing Chroma", unit="doc")

    for batch in _batched(documents, batch_size):
        texts = [doc.content for doc in batch]
        embeddings = embedding_client.embed_texts(texts)

        collection.upsert(
            ids=[doc.doc_id for doc in batch],
            embeddings=embeddings,
            documents=texts,
            metadatas=[doc.metadata for doc in batch],
        )

        stats.indexed_batches += 1
        stats.indexed_documents += len(batch)
        progress.update(len(batch))

    progress.close()
    logger.info(
        f"Indexed {stats.indexed_documents:,} documents into "
        f"Chroma collection '{collection_name}' at {persist_dir}"
    )
    return stats


def _limited(items: Iterable[ProcessedDocument], limit: int):
    count = 0
    for item in items:
        if count >= limit:
            break
        yield item
        count += 1
