from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    corpus_dir: Path = Path(os.getenv("POLICY_CORPUS_DIR", ROOT / "policy_corpus"))
    mock_data_dir: Path = Path(os.getenv("MOCK_DATA_DIR", ROOT / "mock_data"))
    runtime_dir: Path = Path(os.getenv("RUNTIME_DIR", ROOT / "runtime"))
    chroma_dir: Path = Path(os.getenv("CHROMA_DIR", ROOT / "runtime" / "chroma"))
    rag_backend: str = os.getenv("RAG_BACKEND", "chroma").strip().lower()
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "4"))
    llm_enabled: bool = os.getenv("LLM_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    mcp_transport: str = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
    app_name: str = "Morrowfen People Desk"

    def ensure_dirs(self) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
