from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    return os.environ.get(name) or default


@dataclass(frozen=True)
class ChatConfig:
    """Every assistant parameter in one place (models from env; retrieval values tuned in eval/)."""
    ollama_url: str = field(default_factory=lambda: _env("OLLAMA_URL", "http://localhost:11434"))
    qu_model: str = field(default_factory=lambda: _env("OLLAMA_QU_MODEL", "hodacquan2004/uiuc-qu:4b"))
    chat_model: str = field(default_factory=lambda: _env("OLLAMA_CHAT_MODEL", "qwen3:4b-instruct-2507-q4_K_M"))
    embed_model: str = field(default_factory=lambda: _env("OLLAMA_EMBED_MODEL", "bge-m3"))
    # memory: small contexts + a long keep-alive let Ollama keep all three models loaded instead of swapping
    # them per request (swapping cost 5-10 s per answer on an 18 GB laptop)
    qu_num_ctx: int = 2048
    chat_num_ctx: int = 4096
    embed_num_ctx: int = 1024
    keep_alive: str = field(default_factory=lambda: _env("OLLAMA_KEEP_ALIVE", "30m"))
    qu_timeout: float = 20.0
    gen_timeout: float = 90.0
    # retrieval
    pool: int = 200            # candidates from each of full-text and vector search
    k_rrf: int = 60            # reciprocal rank fusion constant
    related_k: int = 50        # papers used as faculty evidence
    w_keywords: float = 0.4
    w_vector: float = 0.4
    w_papers: float = 0.2
    max_papers: int = 8        # paper sources given to the answer step (it cites only the relevant ones)
    abstract_chars: int = 200  # per source in the answer prompt: shorter prompt = faster first token
    max_faculty: int = 6
