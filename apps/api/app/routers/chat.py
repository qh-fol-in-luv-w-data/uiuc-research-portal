from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from ..chat.answer import OUT_OF_SCOPE, build_messages, build_sources, clean_citations, no_results
from ..chat.ollama import OllamaError
from ..chat.retrieve import FacultyIndex, search_faculty, search_papers
from ..chat.understand import understand

router = APIRouter(prefix="/api")


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    history: list[Turn] = Field(default_factory=list, max_length=8)


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def _faculty_index(request: Request) -> FacultyIndex:
    state = request.app.state
    if getattr(state, "faculty_index", None) is None:
        with state.pool.connection() as conn:
            state.faculty_index = FacultyIndex.load(conn)
    return state.faculty_index


def _retrieve(request: Request, plan: dict, qv, cv) -> tuple[list[dict], list[dict]]:
    cfg = request.app.state.chat_cfg
    intent, papers, faculty = plan["intent"], [], []
    with request.app.state.pool.connection() as conn:
        if intent in ("papers", "both"):
            papers = search_papers(conn, plan, qv, cv, cfg, limit=cfg.max_papers if intent == "papers" else 5)
        if intent in ("faculty", "both"):
            related = search_papers(conn, {**plan, "sort": "relevance"}, qv, cv, cfg, limit=cfg.related_k)
            faculty = search_faculty(_faculty_index(request), plan, qv, related, cfg,
                                     limit=max(min(plan["limit"], 8), cfg.max_faculty), cvec=cv)
    return papers, faculty


@router.post("/chat")
async def chat(body: ChatRequest, request: Request) -> StreamingResponse:
    ollama, cfg = request.app.state.chat_ollama, request.app.state.chat_cfg
    try:
        await ollama.tags()
    except OllamaError as exc:
        raise HTTPException(503, f"The assistant's model server (Ollama) is not reachable: {exc}. Start Ollama and "
                                 f"pull the models: ollama pull {cfg.chat_model} && ollama pull {cfg.embed_model}")
    history = [t.model_dump() for t in body.history]

    async def stream() -> AsyncIterator[str]:
        try:
            plan, source = await understand(body.question, history, date.today().isoformat(), ollama, cfg)
            yield sse("plan", {"intent": plan["intent"], "concepts": plan["concepts"], "sort": plan["sort"],
                               "source": source})
            if plan["intent"] == "out_of_scope":
                yield sse("sources", {"sources": []})
                yield sse("token", {"text": OUT_OF_SCOPE})
                yield sse("done", {"answer": OUT_OF_SCOPE})
                return
            groups = [g for g in plan["concepts"] if g]
            qv, cv = await ollama.embed(cfg.embed_model, [plan["standalone_question"],
                                                          " — ".join(", ".join(g[:3]) for g in groups) or body.question])
            papers, faculty = await run_in_threadpool(_retrieve, request, plan, qv, cv)
            sources, context = build_sources(papers, faculty)
            yield sse("sources", {"sources": sources})
            if not sources:
                text = no_results(plan)
                yield sse("token", {"text": text})
                yield sse("done", {"answer": text})
                return
            answer = []
            async for tok in ollama.chat_stream(cfg.chat_model, build_messages(body.question, history, context),
                                                cfg.gen_timeout):
                answer.append(tok)
                yield sse("token", {"text": tok})
            yield sse("done", {"answer": clean_citations("".join(answer), len(sources))})
        except OllamaError as exc:
            yield sse("error", {"detail": f"The assistant could not finish: {exc}"})

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
