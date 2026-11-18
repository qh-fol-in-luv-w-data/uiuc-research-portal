from ingest.works import cap_by_date, drop_reason, mark_outliers, parse_work, rebuild_abstract, short_id
from tests.factories import HERZEN, UIUC, make_author, make_work


def test_short_id():
    assert short_id("https://openalex.org/W123") == "W123"
    assert short_id(None) is None


def test_rebuild_abstract_orders_by_position():
    assert rebuild_abstract({"world": [1], "hello": [0, 2]}) == "hello world hello"
    assert rebuild_abstract(None) is None
    assert rebuild_abstract({}) is None


def test_drop_reason():
    assert drop_reason(make_work()) is None
    assert drop_reason(make_work(retracted=True)) == "retracted"
    assert drop_reason(make_work(paratext=True)) == "paratext"
    assert drop_reason(make_work(title="  ")) == "no_title"
    assert drop_reason(make_work(type="erratum")) == "type:erratum"
    assert drop_reason(make_work(type="other", source_type="conference")) is None
    assert drop_reason(make_work(type="preprint")) is None


def test_parse_work_maps_tables():
    w = make_work(authorships=[
        make_author("A1", "John A. Smith", [UIUC], "UIUC"),
        make_author("A2", "Ivan Petrov", [HERZEN], "Herzen University", position="last"),
        make_author("A2", "Ivan Petrov", [HERZEN], "dup", position="last"),
    ])
    p = parse_work(w)
    assert p.work["id"] == "W1"
    assert p.work["abstract"] == "Deep learning works"
    assert p.work["primary_topic_id"] == "T1"
    assert p.work["venue_type"] == "journal"
    assert [a["author_id"] for a in p.authorships] == ["A1", "A2"]
    assert p.authorships[0]["is_uiuc"] is True and p.authorships[1]["is_uiuc"] is False
    assert sorted(p.work_institutions) == ["I157725225", "I999"]
    assert p.work_topics == [("T1", 0.9)]
    assert p.topics[0]["field"] == "Computer Science"


def test_mark_outliers_flags_non_english_top_citation_and_missing_affiliation():
    items = [parse_work(make_work(id=f"W{i}", cited=i)) for i in range(1, 201)]
    ru = parse_work(make_work(id="WRU", language="ru", cited=8198, authorships=[
        make_author("A9", "Ниводничева М. Р.", [UIUC, HERZEN], "Herzen; University of Illinois")]))
    stray = parse_work(make_work(id="WX", authorships=[make_author("A8", "X Y", [HERZEN], "Herzen University")]))
    mention = parse_work(make_work(id="WM", authorships=[
        make_author("A7", "Z Q", [HERZEN], "Dept of CS, University of Illinois")]))
    counts = mark_outliers(items + [ru, stray, mention])
    assert ru.work["is_outlier"] and ru.work["outlier_reason"] == "non_english_high_citation"
    assert stray.work["is_outlier"] and stray.work["outlier_reason"] == "no_uiuc_affiliation"
    assert not mention.work["is_outlier"]
    assert not items[-1].work["is_outlier"]  # top English paper is not an outlier
    assert counts == {"no_uiuc_affiliation": 1, "non_english_high_citation": 1, "citations_predate_publication": 0}


def test_cap_by_date_keeps_newest():
    items = [parse_work(make_work(id="W1", date="2024-01-01")),
             parse_work(make_work(id="W2", date="2025-01-01")),
             parse_work(make_work(id="W3", date=None))]
    assert [p.work["id"] for p in cap_by_date(items, limit=1)] == ["W2"]
    assert len(cap_by_date(items, limit=10)) == 3


def test_conference_paper_type_is_kept():
    assert drop_reason(make_work(type="conference-paper")) is None
    assert drop_reason(make_work(type="conference-abstract")) == "type:conference-abstract"


def test_is_uiuc_via_child_institution_lineage():
    child = {"id": "https://openalex.org/I555", "display_name": "Beckman Institute", "country_code": "US",
             "type": "facility", "lineage": ["https://openalex.org/I555", "https://openalex.org/I157725225"]}
    p = parse_work(make_work(authorships=[make_author("A1", "X Y", [child], "Beckman Institute")]))
    assert p.authorships[0]["is_uiuc"] is True
    mark_outliers([p])
    assert not p.work["is_outlier"]


def test_truncated_author_list_is_not_flagged_missing_affiliation():
    auths = [make_author(f"A{i}", f"P Q{i}", [HERZEN], "CERN") for i in range(100)]
    p = parse_work(make_work(authorships=auths))
    mark_outliers([p])
    assert not p.work["is_outlier"]


def test_authorship_without_author_id_still_counts_as_uiuc_evidence():
    anon = make_author("A0", "Unknown", [UIUC], "University of Illinois Urbana-Champaign")
    anon["author"]["id"] = None
    other = make_author("A2", "Ivan P", [HERZEN], "Herzen University", position="last")
    p = parse_work(make_work(authorships=[anon, other]))
    assert [a["author_id"] for a in p.authorships] == ["A2"]
    assert "I157725225" in p.work_institutions
    mark_outliers([p])
    assert not p.work["is_outlier"]


def test_truncated_list_counted_before_dropping_unattributed():
    auths = [make_author(f"A{i}", f"P Q{i}", [HERZEN], "CERN") for i in range(100)]
    for a in auths[:10]:
        a["author"]["id"] = None
    p = parse_work(make_work(authorships=auths))
    assert p.raw_authorship_count == 100
    mark_outliers([p])
    assert not p.work["is_outlier"]


def test_curated_unit_authorship_counts_as_uiuc():
    woese = {"id": "https://openalex.org/I4405271866", "display_name": "Carl R. Woese Institute for Genomic Biology",
             "country_code": "US", "type": "facility", "lineage": ["https://openalex.org/I4405271866"]}
    p = parse_work(make_work(authorships=[make_author("A1", "X Y", [woese], "IGB")]),
                   uiuc_units=frozenset({"I157725225", "I4405271866"}))
    assert p.authorships[0]["is_uiuc"] is True
    assert p.institutions[0]["is_uiuc_unit"] is True


def test_citations_predating_publication_flag_reissued_work():
    old = make_work(id="WOLD", date="2026-04-29", cited=1633)
    old["counts_by_year"] = [{"year": 2026, "cited_by_count": 50}, {"year": 2019, "cited_by_count": 120}]
    online_first = make_work(id="WNEW", date="2026-01-10", cited=40)
    online_first["counts_by_year"] = [{"year": 2025, "cited_by_count": 40}]
    items = [parse_work(old), parse_work(online_first)]
    counts = mark_outliers(items)
    assert items[0].work["outlier_reason"] == "citations_predate_publication"
    assert not items[1].work["is_outlier"]
    assert counts["citations_predate_publication"] == 1


def test_journal_version_of_recent_preprint_is_not_a_reissue():
    w = make_work(id="WJ", date="2026-01-01", cited=213)
    w["counts_by_year"] = [{"year": 2024, "cited_by_count": 28}, {"year": 2025, "cited_by_count": 100},
                           {"year": 2026, "cited_by_count": 85}]
    items = [parse_work(w)]
    mark_outliers(items)
    assert not items[0].work["is_outlier"]  # 13% of citations predate, earliest only 2 years before
