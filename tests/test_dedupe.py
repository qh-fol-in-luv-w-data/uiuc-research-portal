from ingest.dedupe import mark_duplicates, normalize_title
from ingest.works import parse_work
from tests.factories import UIUC, make_author, make_work


def test_normalize_title():
    assert normalize_title("  Deep-Learning: A Survey!! ") == "deep learning a survey"


def test_preprint_and_article_with_shared_author_collapse_to_article():
    pre = parse_work(make_work(id="W1", type="preprint", title="Deep learning for drone detection", cited=3))
    art = parse_work(make_work(id="W2", type="article", title="Deep Learning for Drone Detection.", cited=1))
    other = parse_work(make_work(id="W3", type="article", title="Deep learning for drone detection",
                                 authorships=[make_author("A9", "Someone Else", [UIUC], "UIUC")]))
    n = mark_duplicates([pre, art, other])
    assert n == 1
    assert pre.work["duplicate_of"] == "W2"
    assert art.work["duplicate_of"] is None
    assert other.work["duplicate_of"] is None  # same title, no shared author: different work
