from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx
import numpy as np


class OllamaError(RuntimeError):
    """Ollama unreachable or failed."""


class ModelMissing(OllamaError):
    """The requested model is not installed in Ollama."""


class Ollama:
    def __init__(self, base_url: str, http: httpx.AsyncClient | None = None):
        self.base = base_url.rstrip("/")
        self.http = http or httpx.AsyncClient(timeout=None)

    async def _post(self, path: str, body: dict, timeout: float | None) -> httpx.Response:
        try:
            r = await self.http.post(f"{self.base}{path}", json=body, timeout=timeout)
        except httpx.TransportError as exc:
            raise OllamaError(f"Ollama not reachable at {self.base}") from exc
        if r.status_code == 404 and "not found" in r.text:
            raise ModelMissing(body.get("model", "?"))
        if r.status_code >= 400:
            raise OllamaError(f"Ollama error {r.status_code}: {r.text[:200]}")
        return r

    async def chat_json(self, model: str, messages: list[dict], schema: dict, num_predict: int = 400) -> str:
        r = await self._post("/api/chat", {"model": model, "messages": messages, "stream": False, "think": False,
                                           "format": schema, "options": {"temperature": 0, "num_predict": num_predict}}, 90)
        return r.json()["message"]["content"] or ""

    async def chat_stream(self, model: str, messages: list[dict], timeout: float) -> AsyncIterator[str]:
        body = {"model": model, "messages": messages, "stream": True,
                "options": {"temperature": 0.2, "num_predict": 500}}
        try:
            async with self.http.stream("POST", f"{self.base}/api/chat", json=body, timeout=timeout) as r:
                if r.status_code == 404:
                    raise ModelMissing(model)
                if r.status_code >= 400:
                    raise OllamaError(f"Ollama error {r.status_code}")
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    msg = json.loads(line)
                    if msg.get("error"):
                        raise OllamaError(msg["error"])
                    text = (msg.get("message") or {}).get("content")
                    if text:
                        yield text
                    if msg.get("done"):
                        return
        except httpx.TransportError as exc:
            raise OllamaError(f"Ollama not reachable at {self.base}") from exc

    async def embed(self, model: str, texts: list[str]) -> list[np.ndarray]:
        r = await self._post("/api/embed", {"model": model, "input": [t[:2000] for t in texts]}, 60)
        return [np.asarray(v, dtype=np.float32) for v in r.json()["embeddings"]]

    async def tags(self) -> list[str]:
        try:
            r = await self.http.get(f"{self.base}/api/tags", timeout=3)
            return [m["name"] for m in r.json().get("models", [])]
        except (httpx.TransportError, ValueError) as exc:
            raise OllamaError(f"Ollama not reachable at {self.base}") from exc
