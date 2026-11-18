from __future__ import annotations

import httpx


class OllamaTags:
    """Lists the models installed in Ollama (used by /health)."""

    def __init__(self, base_url: str, timeout: float = 2.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def tags(self) -> list[str]:
        resp = httpx.get(f"{self.base_url}/api/tags", timeout=self.timeout)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]
