"""Bilingual assistant: reply language, localized fixed replies and source cards, Vietnamese rule fallback."""
from datetime import date

import pytest

from app.chat.answer import build_messages, build_sources, no_results
from app.chat.lang import reply_language, text
from app.chat.rules import parse

TODAY = "2026-11-19"


@pytest.mark.parametrize("q,ui,want", [
    ("Những bài báo mới nhất về học máy?", "en", "vi"),       # Vietnamese letters win over the UI language
    ("Most recent papers on robotics", "vi", "en"),            # an English sentence gets an English answer
    ("graphene", "vi", "vi"),                                  # no language signal: follow the UI
    ("graphene", "en", "en"),
    ("Giang vien nao nghien cuu robot", "en", "vi"),           # Vietnamese typed without accents
])
def test_reply_language(q, ui, want):
    assert reply_language(q, ui) == want


def test_fixed_replies_exist_in_both_languages():
    for key in ("out_of_scope", "broad"):
        assert "UIUC" in text("en", key) and "UIUC" in text("vi", key) and text("en", key) != text("vi", key)
    assert "học máy" in no_results({"concepts": [["học máy"]]}, "vi")
    assert "Tôi không tìm thấy" in no_results({"concepts": [["học máy"]]}, "vi")


def test_prompt_asks_for_reply_language():
    assert build_messages("q", None, "[1] x", "recent", reply_lang="vi")[-1]["content"].endswith("Answer in Vietnamese.")
    assert build_messages("q", None, "[1] x", "recent", reply_lang="en")[-1]["content"].endswith("Answer in English.")


def test_source_cards_localized():
    paper = {"id": "W1", "title": "T", "type": "conference-paper", "venue": "V", "publication_date": date(2025, 3, 2),
             "doi": None, "cited_by_count": 3, "abstract": "", "uiuc_authors": []}
    fac = {"id": 1, "name": "A", "position": "Professor", "primary_field": "Medicine", "matched_keywords": ["x"],
           "related_papers": []}
    ui_vi, prompt = build_sources([paper], [fac], lang="vi")
    assert ui_vi[0]["meta"] == "Bài hội nghị · tháng 3/2025 · V" and "khớp: x" in ui_vi[1]["meta"]
    assert "Conference paper" in prompt  # the model always reads English source text
    ui_en, _ = build_sources([paper], [fac])
    assert ui_en[0]["meta"] == "Conference paper · Mar 2025 · V"


def test_rules_understand_vietnamese():
    p = parse("Những bài báo mới nhất về học máy trong y tế", TODAY)
    assert p["intent"] == "papers" and p["sort"] == "recent" and p["concepts"][0][0] == "học máy"
    assert parse("Bài báo được trích dẫn nhiều nhất về robot", TODAY)["sort"] == "cited"
    assert parse("Giảng viên nào nghiên cứu về thị giác máy tính?", TODAY)["intent"] == "faculty"
    p = parse("Các công bố về năng lượng mặt trời năm 2025", TODAY)
    assert p["date_from"] == "2025-01-01" and p["date_to"] == "2025-12-31"
