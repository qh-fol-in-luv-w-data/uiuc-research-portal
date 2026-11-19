"""Query understanding contract (copied from finetune/qu.py, the training contract: keep the two in sync).

Pure stdlib so it can be imported on the Mac (API) and on the GPU server (training) alike.
"""
from __future__ import annotations

import json
import re
from datetime import date

INTENTS = ("papers", "faculty", "both", "out_of_scope")
SORTS = ("recent", "cited", "relevance")

SCHEMA: dict = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": list(INTENTS)},
        "standalone_question": {"type": "string"},
        "concepts": {
            "type": "array",
            "items": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        },
        "date_from": {"type": ["string", "null"]},
        "date_to": {"type": ["string", "null"]},
        "sort": {"type": "string", "enum": list(SORTS)},
        "limit": {"type": "integer", "minimum": 1, "maximum": 20},
    },
    "required": ["intent", "standalone_question", "concepts", "date_from", "date_to", "sort", "limit"],
}

SYSTEM_TEMPLATE = """You convert a user's question about University of Illinois Urbana-Champaign (UIUC) research into a JSON search plan.
Today is {today}.
Fields:
- intent: "papers" (publications), "faculty" (people/experts), "both", or "out_of_scope" (not about UIUC research).
- standalone_question: the question rewritten in English so it is understandable without the conversation history.
- concepts: list of concept groups. A paper must match every group (AND); terms inside a group are alternatives (OR). Put the core term first, then 2-5 English synonyms or closely related research terms, all lowercase. Use [] for out_of_scope.
- date_from / date_to: ISO dates (YYYY-MM-DD) when the question restricts publication time, else null. Resolve relative phrases ("last year", "past 6 months") against today.
- sort: "recent" for newest/latest, "cited" for most cited/influential/top, else "relevance".
- limit: number of results requested, default 5, max 20.
Answer with the JSON object only."""

FEWSHOT: list[tuple[str, dict]] = [
    (
        "Latest UIUC publications about quantum error correction",
        {"intent": "papers", "standalone_question": "What are the latest UIUC publications about quantum error correction?",
         "concepts": [["quantum error correction", "fault-tolerant quantum computing", "quantum codes", "logical qubits"]],
         "date_from": None, "date_to": None, "sort": "recent", "limit": 5},
    ),
    (
        "who at illinois are experts in soil microbiology?",
        {"intent": "faculty", "standalone_question": "Which UIUC faculty members are experts in soil microbiology?",
         "concepts": [["soil microbiology", "soil microbiome", "rhizosphere", "microbial ecology"]],
         "date_from": None, "date_to": None, "sort": "relevance", "limit": 5},
    ),
    (
        "Top 10 most cited papers on machine learning for climate modeling since 2025",
        {"intent": "papers", "standalone_question": "What are the 10 most cited UIUC papers on machine learning for climate modeling since 2025?",
         "concepts": [["machine learning", "deep learning", "neural networks"], ["climate modeling", "climate models", "climate change", "earth system model"]],
         "date_from": "2025-01-01", "date_to": None, "sort": "cited", "limit": 10},
    ),
    (
        "What's a good recipe for banana bread?",
        {"intent": "out_of_scope", "standalone_question": "What's a good recipe for banana bread?",
         "concepts": [], "date_from": None, "date_to": None, "sort": "relevance", "limit": 5},
    ),
]

_THINK = re.compile(r"<think>.*?</think>", re.S)
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def no_think(base_url: str) -> dict:
    """Request fields that disable Qwen3 thinking: Ollama /v1 uses reasoning_effort, vLLM the chat template kwarg."""
    if ":11434" in base_url:
        return {"reasoning_effort": "none"}
    return {"chat_template_kwargs": {"enable_thinking": False}}


def system_prompt(today: str) -> str:
    return SYSTEM_TEMPLATE.format(today=today)


def build_messages(question: str, today: str, history: list[dict] | None = None, fewshot: bool = False) -> list[dict]:
    """history: prior turns as [{"role": "user"|"assistant", "content": str}], oldest first (max 4 used)."""
    msgs = [{"role": "system", "content": system_prompt(today)}]
    if fewshot:
        for q, a in FEWSHOT:
            msgs += [{"role": "user", "content": q}, {"role": "assistant", "content": dump(a)}]
    if history:
        convo = "\n".join(f"{t['role']}: {t['content']}" for t in history[-4:])
        question = f"Conversation so far:\n{convo}\n\nNew question: {question}"
    msgs.append({"role": "user", "content": question})
    return msgs


def dump(plan: dict) -> str:
    return json.dumps(plan, ensure_ascii=False, separators=(", ", ": "))


def parse(text: str) -> dict | None:
    """Extract the JSON object from raw model output; None when it is not parseable."""
    s = _FENCE.sub("", _THINK.sub("", text).strip()).strip()
    if not s.startswith("{"):
        i, j = s.find("{"), s.rfind("}")
        if i < 0 or j <= i:
            return None
        s = s[i : j + 1]
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def schema_errors(p: dict) -> list[str]:
    errs = [f"missing {k}" for k in SCHEMA["required"] if k not in p]
    if errs:
        return errs
    if p["intent"] not in INTENTS:
        errs.append("intent")
    if p["sort"] not in SORTS:
        errs.append("sort")
    if not isinstance(p["standalone_question"], str) or not p["standalone_question"].strip():
        errs.append("standalone_question")
    c = p["concepts"]
    if not isinstance(c, list) or not all(isinstance(g, list) and g and all(isinstance(t, str) and t.strip() for t in g) for g in c):
        errs.append("concepts")
    for k in ("date_from", "date_to"):
        v = p[k]
        if v is not None and not (isinstance(v, str) and _ISO.match(v) and _valid_date(v)):
            errs.append(k)
    if not isinstance(p["limit"], int) or isinstance(p["limit"], bool) or not 1 <= p["limit"] <= 20:
        errs.append("limit")
    return errs


def _valid_date(s: str) -> bool:
    try:
        date.fromisoformat(s)
        return True
    except ValueError:
        return False


def _norm(t: str) -> str:
    """Lowercase, strip punctuation, crude singular form ("turbines" -> "turbine", "plants" -> "plant")."""
    words = re.sub(r"[^a-z0-9 ]+", " ", t.lower()).split()
    return " ".join(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in words)


def needs_fallback(plan: dict | None) -> bool:
    """Runtime guard for the finetuned model: unusable plan -> use the few-shot base model or the rule parser."""
    return plan is None or bool(schema_errors(plan)) or (plan["intent"] != "out_of_scope" and not plan["concepts"])


def concept_scores(gold: list[list[str]], pred: list[list[str]]) -> tuple[float, float]:
    """(recall, precision) at group level. A gold group is covered when some predicted group shares a term with it."""
    g = [{_norm(t) for t in grp} for grp in gold]
    p = [{_norm(t) for t in grp if isinstance(t, str)} for grp in pred if isinstance(grp, list)]
    p = [grp for grp in p if grp]
    if not g and not p:
        return 1.0, 1.0
    rec = sum(any(_overlap(a, b) for b in p) for a in g) / len(g) if g else 0.0
    prec = sum(any(_overlap(a, b) for b in g) for a in p) / len(p) if p else 0.0
    return rec, prec


def _overlap(a: set[str], b: set[str]) -> bool:
    """Same term, or one term contains the other as whole words ("computer vision" ~ "computer vision models")."""
    return any(x == y or (min(len(x), len(y)) >= 4 and (f" {x} " in f" {y} " or f" {y} " in f" {x} ")) for x in a for y in b)
