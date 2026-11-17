UIUC = {"id": "https://openalex.org/I157725225", "display_name": "University of Illinois Urbana-Champaign",
        "country_code": "US", "type": "education"}
UISYS = {"id": "https://openalex.org/I2801919071", "display_name": "University of Illinois System",
         "country_code": "US", "type": "education"}
HERZEN = {"id": "https://openalex.org/I999", "display_name": "Herzen University", "country_code": "RU",
          "type": "education"}


def make_author(aid: str, name: str, institutions: list[dict], raw: str, position: str = "first") -> dict:
    return {
        "author_position": position,
        "author": {"id": f"https://openalex.org/{aid}", "display_name": name, "orcid": None},
        "institutions": institutions,
        "raw_affiliation_strings": [raw],
    }


def make_topic(tid="T1", name="Computer Vision", subfield="Computer Vision and Pattern Recognition",
               field="Computer Science", domain="Physical Sciences", score=0.9) -> dict:
    return {"id": f"https://openalex.org/{tid}", "display_name": name, "score": score,
            "subfield": {"display_name": subfield}, "field": {"display_name": field},
            "domain": {"display_name": domain}}


def make_work(id="W1", title="Deep learning for drone detection", type="article", language="en", cited=10,
              date="2025-06-01", authorships=None, abstract=None, topic=None, source_type="journal",
              venue="Venue X", retracted=False, paratext=False, is_oa=True) -> dict:
    if authorships is None:
        authorships = [make_author("A1", "John A. Smith", [UIUC], "University of Illinois Urbana-Champaign")]
    if abstract is None:
        abstract = {"Deep": [0], "learning": [1], "works": [2]}
    t = topic or make_topic()
    return {
        "id": f"https://openalex.org/{id}", "doi": f"https://doi.org/10.1/{id}", "title": title,
        "publication_date": date, "type": type, "language": language, "cited_by_count": cited,
        "open_access": {"is_oa": is_oa, "oa_url": "https://example.org/x.pdf" if is_oa else None},
        "primary_location": {"source": {"display_name": venue, "type": source_type}},
        "primary_topic": t, "topics": [t], "authorships": authorships,
        "is_retracted": retracted, "is_paratext": paratext, "abstract_inverted_index": abstract,
    }
