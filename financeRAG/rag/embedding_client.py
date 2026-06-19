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
        max_retries: int = 3,
        retry_sleep_seconds: float = 2.0,
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_retries = max_retries
        self.retry_sleep_seconds = retry_sleep_seconds

    def embed_texts(self, texts: Iterable[str]) -> List[List[float]]:
        inputs = list(texts)
        if not inputs:
            return []

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=inputs,
                )
                return [item.embedding for item in response.data]
            except Exception as exc:  # pragma: no cover - depends on network/API.
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(self.retry_sleep_seconds * attempt)

        raise RuntimeError(f"Embedding request failed after retries: {last_error}") from last_error
