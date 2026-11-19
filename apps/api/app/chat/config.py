from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    return os.environ.get(name) or default


@dataclass(frozen=True)
class ChatConfig:
    """Every assistant parameter in one place (models from env; retrieval values tuned in eval/)."""
    ollama_url: str = field(default_factory=lambda: _env("OLLAMA_URL", "http://localhost:11434"))
    qu_model: str = field(default_factory=lambda: _env("OLLAMA_QU_MODEL", "uiuc-qu:4b"))
    chat_model: str = field(default_factory=lambda: _env("OLLAMA_CHAT_MODEL", "qwen3:4b-instruct-2507-q4_K_M"))
    embed_model: str = field(default_factory=lambda: _env("OLLAMA_EMBED_MODEL", "bge-m3"))
    qu_timeout: float = 20.0
    gen_timeout: float = 90.0
    # retrieval
    pool: int = 200            # candidates from each of full-text and vector search
    k_rrf: int = 60            # reciprocal rank fusion constant
    tau: float = 0.55          # min cosine for a concept group to count as matched by meaning
    related_k: int = 50        # papers used as faculty evidence
    w_keywords: float = 0.4
    w_vector: float = 0.3
    w_papers: float = 0.3
    max_papers: int = 8        # sources shown for intent=both are split between papers and faculty
