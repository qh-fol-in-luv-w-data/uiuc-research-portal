import json

import httpx
import numpy as np
import pytest

from ingest.embedder import EmbedderUnavailable, OllamaEmbedder


def test_embed_batches_and_truncates():
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        return httpx.Response(200, json={"embeddings": [[float(len(t)), 0.0] for t in body["input"]]})

    e = OllamaEmbedder(httpx.Client(transport=httpx.MockTransport(handler)), "http://o", "bge-m3", batch_size=2)
    out = e.embed(["a", "bb", "x" * 5000])
    assert [len(b["input"]) for b in seen] == [2, 1]
    assert seen[0]["model"] == "bge-m3"
    assert [v[0] for v in out] == [1.0, 2.0, 2000.0]
    assert out[0].dtype == np.float32


def test_missing_model_raises_with_hint():
    e = OllamaEmbedder(httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404))), "http://o", "bge-m3")
    with pytest.raises(EmbedderUnavailable, match="ollama pull bge-m3"):
        e.embed(["a"])


def test_connection_error_raises_unavailable():
    def handler(request):
        raise httpx.ConnectError("refused")
    e = OllamaEmbedder(httpx.Client(transport=httpx.MockTransport(handler)), "http://o", "bge-m3")
    with pytest.raises(EmbedderUnavailable, match="Ollama"):
        e.embed(["a"])
