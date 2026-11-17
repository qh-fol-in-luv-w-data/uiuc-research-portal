from ingest.names import AuthorIndex, NameParts, link_confidence, normalize_name


def test_normalize_name():
    assert normalize_name("José A. García") == NameParts("jose", ("a",), "garcia")
    assert normalize_name("Smith, John") == NameParts("john", (), "smith")
    assert normalize_name("Martin Luther King Jr.") == NameParts("martin", ("luther",), "king")
    assert normalize_name("Mary-Kate O'Neil") == NameParts("marykate", (), "oneil")
    assert normalize_name("Robert (Bob) Stone") == NameParts("robert", (), "stone")
    assert normalize_name("Plato") is None
    assert normalize_name(None) is None


def test_match_tiers():
    idx = AuthorIndex()
    idx.add("A1", "John A. Smith")
    idx.add("A2", "John Smith")
    idx.add("A3", "J. Smith")
    idx.add("A4", "Jane Smith")
    assert idx.match(normalize_name("John A Smith")) == ("exact", ["A1"])
    assert idx.match(normalize_name("John B Smith")) == ("first_last", ["A1", "A2"])
    assert idx.match(normalize_name("Jack Smith")) == ("initial_last", ["A3"])  # Jane excluded
    assert idx.match(normalize_name("Wei Zhang")) is None


def test_link_confidence():
    assert link_confidence("exact", [0.4]) == (0, 0.9)
    i, c = link_confidence("initial_last", [0.30, 0.71, 0.50])
    assert i == 1 and c == 0.6
    i, c = link_confidence("initial_last", [0.70, 0.69])
    assert i == 0 and c < 0.5
