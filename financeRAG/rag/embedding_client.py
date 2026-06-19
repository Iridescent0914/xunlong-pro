import re
import time
from typing import Iterable, List

from openai import OpenAI


class OpenAICompatibleEmbeddingClient:
    """Small wrapper around OpenAI-compatible embedding APIs."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        max_batch_size: int = 10,
        max_retries: int = 3,
        retry_sleep_seconds: float = 2.0,
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_batch_size = max_batch_size
        self.max_retries = max_retries
        self.retry_sleep_seconds = retry_sleep_seconds

    def embed_texts(self, texts: Iterable[str]) -> List[List[float]]:
        inputs = list(texts)
        if not inputs:
            return []

        embeddings: List[List[float]] = []
        for start in range(0, len(inputs), self.max_batch_size):
            batch = inputs[start:start + self.max_batch_size]
            embeddings.extend(self._embed_batch(batch))
        return embeddings

    def _embed_batch(self, inputs: List[str]) -> List[List[float]]:
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=inputs,
                )
                return [item.embedding for item in response.data]
            except Exception as exc:  # pragma: no cover - depends on network/API.
                fallback_limit = _extract_batch_limit(str(exc))
                if fallback_limit and len(inputs) > fallback_limit:
                    self.max_batch_size = min(self.max_batch_size, fallback_limit)
                    embeddings: List[List[float]] = []
                    for start in range(0, len(inputs), fallback_limit):
                        embeddings.extend(self._embed_batch(inputs[start:start + fallback_limit]))
                    return embeddings

                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(self.retry_sleep_seconds * attempt)

        raise RuntimeError(f"Embedding request failed after retries: {last_error}") from last_error


def _extract_batch_limit(error_message: str) -> int:
    match = re.search(r"not be larger than\s+(\d+)", error_message)
    if not match:
        return 0
    return int(match.group(1))
