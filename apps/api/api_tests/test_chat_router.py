import json

import numpy as np
from fastapi.testclient import TestClient

from app.chat import qu
from app.chat.answer import clean_citations
from app.chat.ollama import OllamaError
from app.main import create_app
from tests.conftest import TEST_URL

from .conftest import FakeOllama as FakeTags
from .conftest import seed


def plan(intent="papers", concepts=(("deep learning",), ("drone",))):
    return qu.dump({"intent": intent, "standalone_question": "Recent papers on deep learning for drones?",
                    "concepts": [list(g) for g in concepts], "date_from": None, "date_to": None,
                    "sort": "recent", "limit": 5})


class FakeChatOllama:
    def __init__(self, plan_json, answer_tokens=("Drones are covered ", "in [1] and [9]."), down=False):
        self.plan_json, self.answer_tokens, self.down = plan_json, answer_tokens, down
        self.streamed = self.embedded = False

    async def tags(self):
        if self.down:
            raise OllamaError("Ollama not reachable")
        return ["uiuc-qu:4b"]

    async def chat_json(self, model, messages, schema, num_predict=400):
        return self.plan_json

    async def embed(self, model, texts):
        self.embedded = True
        rng = np.random.default_rng(0)
        return [v / np.linalg.norm(v) for v in rng.random((len(texts), 1024)).astype(np.float32)]

    async def chat_stream(self, model, messages, timeout):
        self.streamed = True
        for t in self.answer_tokens:
            yield t


def events(body: str) -> list[tuple[str, dict]]:
    out = []
    for block in body.strip().split("\n\n"):
        ev = dict(line.split(": ", 1) for line in block.splitlines())
        out.append((ev["event"], json.loads(ev["data"])))
    return out


def client_with(db, tmp_path, fake):
    seed(db)
    app = create_app(database_url=TEST_URL, institution_path=tmp_path / "none.json", ollama=FakeTags(), chat_ollama=fake)
    return TestClient(app)


def test_stream_order_sources_and_clean_citations(db, tmp_path):
    with client_with(db, tmp_path, FakeChatOllama(plan())) as c:
        r = c.post("/api/chat", json={"question": "recent deep learning drone papers?", "history": []})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    ev = events(r.text)
    assert [e for e, _ in ev][:2] == ["plan", "sources"] and ev[-1][0] == "done"
    assert {e for e, _ in ev[2:-1]} == {"token"}
    sources = ev[1][1]["sources"]
    assert sources[0]["n"] == 1 and sources[0]["kind"] == "work" and "drone" in sources[0]["title"].lower()
    assert "[9]" not in ev[-1][1]["answer"] and "[1]" in ev[-1][1]["answer"]


def test_out_of_scope_skips_retrieval_and_generation(db, tmp_path):
    fake = FakeChatOllama(plan(intent="out_of_scope", concepts=()))
    with client_with(db, tmp_path, fake) as c:
        ev = events(c.post("/api/chat", json={"question": "banana bread recipe?"}).text)
    assert ev[1] == ("sources", {"sources": []}) and "UIUC" in ev[-1][1]["answer"]
    assert not fake.embedded and not fake.streamed


def test_faculty_intent_returns_faculty_sources(db, tmp_path):
    fake = FakeChatOllama(plan(intent="faculty", concepts=(("medical imaging", "computer vision"),)))
    with client_with(db, tmp_path, fake) as c:
        ev = events(c.post("/api/chat", json={"question": "who works on medical imaging?"}).text)
    kinds = [s["kind"] for s in ev[1][1]["sources"]]
    assert kinds and set(kinds) == {"faculty"} and ev[1][1]["sources"][0]["title"] == "Jane Doe"


def test_ollama_down_returns_503(db, tmp_path):
    with client_with(db, tmp_path, FakeChatOllama(plan(), down=True)) as c:
        r = c.post("/api/chat", json={"question": "anything"})
    assert r.status_code == 503 and r.json()["error"] == "unavailable" and "ollama" in r.json()["detail"].lower()


def test_clean_citations():
    assert clean_citations("A [1], B [3] and C [n].", 2) == "A [1], B and C."
