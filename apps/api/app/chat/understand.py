from __future__ import annotations

import asyncio

from . import qu, rules
from .config import ChatConfig
from .ollama import ModelMissing, OllamaError


async def understand(question: str, history: list[dict] | None, today: str, ollama, cfg: ChatConfig) -> tuple[dict, str]:
    """Search plan for a question. Returns (plan, source) where source is "model", "fewshot" or "rules"."""
    raw, source = None, "model"
    try:
        try:
            if cfg.qu_model == cfg.chat_model:
                raise ModelMissing(cfg.qu_model)  # single-model mode: few-shot on the chat model (no model swapping)
            raw = await asyncio.wait_for(
                ollama.chat_json(cfg.qu_model, qu.build_messages(question, today, history), qu.SCHEMA), cfg.qu_timeout)
        except ModelMissing:
            # finetuned model not installed: the generation model with few-shot examples (benchmarked fallback)
            source = "fewshot"
            raw = await asyncio.wait_for(
                ollama.chat_json(cfg.chat_model, qu.build_messages(question, today, history, fewshot=True), qu.SCHEMA),
                cfg.qu_timeout)
    except (asyncio.TimeoutError, OllamaError):
        raw = None
    plan = qu.parse(raw) if raw else None
    if qu.needs_fallback(plan):
        return rules.parse(question, today), "rules"
    if plan["intent"] == "out_of_scope":
        if rules.TOPIC_REQUEST.search(question.lower()):
            return rules.parse(question, today), "rules"
        if rules.BROAD.search(question):
            plan["broad"] = True  # "What research does UIUC do?": point to topics instead of refusing
    elif plan["intent"] == "papers" and rules.vietnamese_who(question):
        plan["intent"] = "faculty"
    if source == "fewshot":
        # few-shot models over-predict "recent" (sort 61-73% on held-out sets); explicit wording is reliable (89%+)
        plan["sort"] = rules.parse(question, today)["sort"]
    return plan, source
