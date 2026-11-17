import pytest

from ingest.__main__ import build_parser


def test_parser_accepts_all_steps():
    p = build_parser()
    for cmd in ["migrate", "fetch-works", "clean-works", "load-faculty", "embed-profiles", "link-faculty",
                "embed", "aggregate", "all"]:
        assert p.parse_args([cmd]).cmd == cmd
    assert p.parse_args(["embed", "--force"]).force is True
    with pytest.raises(SystemExit):
        p.parse_args(["nope"])
