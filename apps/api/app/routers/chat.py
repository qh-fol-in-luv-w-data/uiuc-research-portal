from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from pydantic import AfterValidator, BaseModel, Field
from starlette.concurrency import run_in_threadpool

from ..chat.answer import build_messages, build_sources, clean_citations, no_results
from ..chat.guard import SentenceGuard, clean_answer
from ..chat.lang import reply_language, text
from ..chat.ollama import OllamaError
from ..chat.retrieve import FacultyIndex, search_faculty, search_papers
from ..chat.understand import understand

router = APIRouter(prefix="/api")


def _no_nul(v: str) -> str:
    return v.replace("\x00", "")


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: Annotated[str, AfterValidator(_no_nul), Field(max_length=4000)]


class ChatRequest(BaseModel):
    question: Annotated[str, AfterValidator(_no_nul), Field(min_length=1, max_length=500)]
    history: list[Turn] = Field(default_factory=list, max_length=8)
    lang: Literal["en", "vi"] = "en"  # page language: source-card labels, and the reply language when the question is ambiguous


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
    reply = reply_language(body.question, body.lang)
    slots = request.app.state.chat_slots
    if slots.locked():
        raise HTTPException(429, "The assistant is answering other questions. Try again in a few seconds.")
    await slots.acquire()  # released when the stream ends, also if the client disconnects

    released = False

    def release() -> None:  # exactly once: from the stream's finally, or the background task if it never started
        nonlocal released
        if not released:
            released = True
            slots.release()

    async def stream() -> AsyncIterator[str]:
        try:
            async for event in _answer(body, request, history, reply):
                yield event
        finally:
            release()

    return StreamingResponse(stream(), media_type="text/event-stream", background=BackgroundTask(release),
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


async def _answer(body: ChatRequest, request: Request, history: list[dict], reply: str) -> AsyncIterator[str]:
    """The SSE events for one question: plan, sources, tokens, done (or error)."""
    ollama, cfg = request.app.state.chat_ollama, request.app.state.chat_cfg
    try:
        plan, source = await understand(body.question, history, date.today().isoformat(), ollama, cfg)
        yield sse("plan", {"intent": plan["intent"], "concepts": plan["concepts"], "sort": plan["sort"],
                           "source": source})
        if plan["intent"] == "out_of_scope":
            yield sse("sources", {"sources": []})
            msg = text(reply, "broad" if plan.get("broad") else "out_of_scope")
            yield sse("token", {"text": msg})
            yield sse("done", {"answer": msg})
            return
        groups = [g for g in plan["concepts"] if g]
        qv, cv = await ollama.embed(cfg.embed_model, [plan["standalone_question"],
                                                      " — ".join(", ".join(g[:3]) for g in groups) or body.question])
        papers, faculty = await run_in_threadpool(_retrieve, request, plan, qv, cv)
        sources, context = build_sources(papers, faculty, cfg.abstract_chars, lang=body.lang)
        yield sse("sources", {"sources": sources})
        if not sources:
            msg = no_results(plan, reply)
            yield sse("token", {"text": msg})
            yield sse("done", {"answer": msg})
            return
        # Prompt-injection isolation: the answer model sees the planner's rewritten standalone question (which already
        # folds in the conversation), never the raw user text or history; its output passes a sentence guard.
        messages = build_messages(plan["standalone_question"], None, context, plan["sort"], reply)
        guard, answer = SentenceGuard(body.question, context), []
        async for tok in ollama.chat_stream(cfg.chat_model, messages, cfg.gen_timeout):
            for safe in guard.feed(tok):
                answer.append(safe)
                yield sse("token", {"text": safe})
        if tail := guard.flush():
            answer.append(tail)
            yield sse("token", {"text": tail})
        final = clean_citations(clean_answer("".join(answer), body.question, context), len(sources))
        if not final:  # everything the model wrote was filtered out
            final = no_results(plan, reply)
            yield sse("token", {"text": final})
        yield sse("done", {"answer": final})
    except OllamaError as exc:
        yield sse("error", {"detail": text(reply, "error").format(exc=exc)})

