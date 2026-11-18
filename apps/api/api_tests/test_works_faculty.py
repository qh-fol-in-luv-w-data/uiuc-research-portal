def test_works_sorted_and_excluding_outliers(client):
    body = client.get("/api/works?sort=cited").json()
    assert [w["id"] for w in body["items"]] == ["W1", "W3", "W2"]  # W4 is an outlier
    assert body["total"] == 3
    w1 = body["items"][0]
    assert w1["uiuc_authors"] == [{"name": "Jane Doe", "faculty_id": 1}]
    assert w1["field"] == "Computer Science"


def test_works_recent_field_and_query(client):
    assert [w["id"] for w in client.get("/api/works?sort=recent").json()["items"]] == ["W2", "W3", "W1"]
    assert [w["id"] for w in client.get("/api/works?field=Chemistry").json()["items"]] == ["W3"]
    assert [w["id"] for w in client.get("/api/works?q=radiology&sort=relevance").json()["items"]] == ["W2"]


def test_works_pagination_bounds(client):
    body = client.get("/api/works?sort=cited&page=2&page_size=2").json()
    assert [w["id"] for w in body["items"]] == ["W2"] and body["page"] == 2
    assert client.get("/api/works?page_size=500").status_code == 422


def test_faculty_search_with_matched_keywords(client):
    body = client.get("/api/faculty?q=medical imaging").json()
    assert [f["name"] for f in body["items"]] == ["Jane Doe"]
    assert body["items"][0]["matched_keywords"] == ["medical imaging"]
    assert body["items"][0]["link_confidence"] == 0.9
    assert [f["name"] for f in client.get("/api/faculty?position=Assistant").json()["items"]] == ["Bob Smith"]


def test_faculty_profile_and_404(client):
    p = client.get("/api/faculty/1").json()
    assert p["link_method"] == "exact" and p["openalex_author_ids"] == ["A1"]
    assert [w["id"] for w in p["recent_works"]] == ["W2", "W1"]
    assert p["topics"][0] == {"name": "Computer Vision", "count": 2}
    r = client.get("/api/faculty/999")
    assert r.status_code == 404 and r.json()["error"] == "not_found"
