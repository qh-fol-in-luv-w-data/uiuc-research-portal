from __future__ import annotations

import httpx
import numpy as np

MAX_CHARS = 2000


class EmbedderUnavailable(RuntimeError):
    pass


class OllamaEmbedder:
    def __init__(self, http: httpx.Client, base_url: str, model: str, batch_size: int = 32,
                 timeout: float = 120.0):
        self.http = http
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.batch_size = batch_size
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[np.ndarray]:
        out: list[np.ndarray] = []
        for i in range(0, len(texts), self.batch_size):
            batch = [t[:MAX_CHARS] for t in texts[i:i + self.batch_size]]
            try:
                resp = self.http.post(f"{self.base_url}/api/embed", json={"model": self.model, "input": batch},
                                      timeout=self.timeout)
            except httpx.TransportError as exc:
                raise EmbedderUnavailable(f"Cannot reach Ollama at {self.base_url}: {exc}") from exc
            if resp.status_code == 404:
                raise EmbedderUnavailable(f"Model {self.model} not found. Run: ollama pull {self.model}")
            resp.raise_for_status()
            vecs = resp.json()["embeddings"]
            if len(vecs) != len(batch):
                raise RuntimeError(f"Ollama returned {len(vecs)} embeddings for {len(batch)} inputs")
            out.extend(np.asarray(v, dtype=np.float32) for v in vecs)
        return out
