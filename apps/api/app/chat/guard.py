"""Deterministic output guard for the answer model (prompt-injection defence that does not rely on the model).

Answers are built from numbered sources and never need links, markup or the instructions themselves, so any
sentence that carries a URL, an HTML tag, a markdown link, or copies the system prompt is dropped. Applied per
sentence while streaming, so a leak never reaches the browser, not even briefly.
(eval/attacks.py 2026-11-19: a question wrapping "repeat the text above" leaked the prompt; another appended a
phishing link; another returned a <script> tag.)"""
from __future__ import annotations

import re
from collections.abc import Iterator

from .answer import SYSTEM

SHINGLE = 8  # words; long enough that ordinary answers never share one with the instructions
_WORD = re.compile(r"[a-z0-9]+")


def _shingles(text: str) -> set[tuple[str, ...]]:
    w = _WORD.findall(text.lower())
    return {tuple(w[i:i + SHINGLE]) for i in range(len(w) - SHINGLE + 1)}


_PROMPT = _shingles(SYSTEM)
_PROMPT_TEXT = " " + " ".join(_WORD.findall(SYSTEM.lower())) + " "


def _copies_prompt(sentence: str) -> bool:
    """Shares an 8-word run with the instructions, or is a whole (4+ word) piece of them."""
    words = _WORD.findall(sentence.lower())
    return bool(_shingles(sentence) & _PROMPT) or (len(words) >= 4 and f" {' '.join(words)} " in _PROMPT_TEXT)


_UNSAFE = re.compile(r"https?://|www\.|<\s*/?\s*[a-z!][^>]*>|\]\(|javascript:|data:text", re.I)
# a sentence ends at . ! ? followed by whitespace, or at a line break
_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n+")


def _keep(sentence: str) -> bool:
    return not _UNSAFE.search(sentence) and not _copies_prompt(sentence)


_COMMON = {"UIUC", "Illinois", "University", "Urbana", "Champaign", "AI", "I", "What", "Which", "Who", "Recent", "Papers",
           "Show", "List", "Give", "Find", "Tell"}
_NAME = re.compile(r"(?<![.!?:]\s)(?<!^)\b([A-Z][\w'-]+)")
_NUMBER = re.compile(r"\b\d{3,}\b")


def foreign_terms(question: str, evidence: str) -> set[str]:
    """Names (capitalised mid-sentence) and 3+ digit numbers that the question mentions but no source contains:
    a sentence repeating one of them is asserting something only the user said (eval/attacks.py: planted facts)."""
    q = question.strip()
    terms = {m for m in _NAME.findall(q) if m not in _COMMON} | set(_NUMBER.findall(q))
    return {t for t in terms if not re.search(rf"\b{re.escape(t)}\b", evidence)}


class SentenceGuard:
    """Feed streamed tokens; get back only complete, safe sentences (with their trailing whitespace)."""

    def __init__(self, question: str = "", evidence: str = "") -> None:
        self.buf = ""
        self.foreign = [re.compile(rf"\b{re.escape(t)}\b") for t in foreign_terms(question, evidence)]

    def _ok(self, sentence: str) -> bool:
        return _keep(sentence) and not any(p.search(sentence) for p in self.foreign)

    def feed(self, token: str) -> Iterator[str]:
        self.buf += token
        while m := _BOUNDARY.search(self.buf):
            sentence, sep = self.buf[:m.start()], m.group(0)
            self.buf = self.buf[m.end():]
            if sentence.strip() and self._ok(sentence):
                yield sentence + sep
            elif "\n" in sep:
                yield "\n"

    def flush(self) -> str:
        rest, self.buf = self.buf, ""
        return rest if rest.strip() and self._ok(rest) else ""


def clean_answer(text: str, question: str = "", evidence: str = "") -> str:
    g = SentenceGuard(question, evidence)
    out = "".join(g.feed(text)) + g.flush()
    return re.sub(r"\n{3,}", "\n\n", out).strip()
