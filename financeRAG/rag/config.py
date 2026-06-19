import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


RAG_DIR = Path(__file__).resolve().parent
DEFAULT_RAG_ENV_FILE = RAG_DIR / ".env"


def _first_env(*names: str, default: Optional[str] = None) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


@dataclass(frozen=True)
class RAGConfig:
    """Runtime configuration for FinanceRAG indexing and retrieval."""

    llm_model: str
    llm_base_url: str
    llm_api_key: str
    embedding_model: str
    embedding_base_url: str
    embedding_api_key: str
    chroma_persist_dir: str
    chroma_collection: str

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "RAGConfig":
        env_path = Path(env_file) if env_file else DEFAULT_RAG_ENV_FILE
        if env_path.exists():
            load_dotenv(env_path, override=False)

        api_key = _first_env(
            "EMBEDDING_API_KEY",
            "DASHSCOPE_API_KEY",
            "QWEN_API_KEY",
            "LLM_API_KEY",
        )
        if not api_key:
            raise ValueError(
                "Missing embedding API key. Set EMBEDDING_API_KEY or DASHSCOPE_API_KEY."
            )

        embedding_model = _first_env(
            "EMBEDDING_MODEL",
            default="text-embedding-v4",
        )
        if embedding_model:
            embedding_model = embedding_model.replace(" ", "")

        return cls(
            llm_model=_first_env("LLM_MODEL", "DEFAULT_LLM_MODEL", default="qwen3.6-plus"),
            llm_base_url=_first_env(
                "LLM_BASE_URL",
                default="https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
            llm_api_key=_first_env(
                "LLM_API_KEY",
                "DASHSCOPE_API_KEY",
                "QWEN_API_KEY",
                default=api_key,
            ),
            embedding_model=embedding_model or "text-embedding-v4",
            embedding_base_url=_first_env(
                "EMBEDDING_BASE_URL",
                "LLM_BASE_URL",
                default="https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
            embedding_api_key=api_key,
            chroma_persist_dir=_first_env(
                "CHROMA_PERSIST_DIR",
                default=str(Path("financeRAG") / "rag" / "chroma_db"),
            ),
            chroma_collection=_first_env(
                "CHROMA_COLLECTION",
                default="finance_rag",
            ),
        )
