from ann_app.parse import (
    find_latest_digest,
    flatten_headlines,
    parse_digest,
)

SAMPLE = """## WSJ

1. [Story A](https://wsj.com/a)
2. [Story B](https://wsj.com/b)

Note: WSJ was not directly fetchable.

## NYT

1. A cross-verified summary with no link.
2. [Linked NYT story](https://nyt.com/x)

## NBC

1. [NBC story](https://nbc.com/1)

## AP

No headlines available for this outlet today.

## Note

No access limitations encountered this session.
"""


def test_parse_digest_extracts_outlets_in_config_order():
    sections = parse_digest(SAMPLE)
    assert [s.outlet for s in sections] == ["WSJ", "NYT", "NBC", "AP"]


def test_parse_digest_linked_and_plain_items():
    sections = parse_digest(SAMPLE)
    wsj = sections[0]
    assert wsj.headlines[0].title == "Story A"
    assert wsj.headlines[0].link == "https://wsj.com/a"
    assert wsj.headlines[0].rank == 1

    nyt = sections[1]
    assert nyt.headlines[0].link is None
    assert nyt.headlines[0].title == "A cross-verified summary with no link."
    assert nyt.headlines[1].link == "https://nyt.com/x"


def test_parse_digest_ignores_note_section_and_prose():
    sections = parse_digest(SAMPLE)
    titles = [h.title for s in sections for h in s.headlines]
    assert not any("access limitations" in t for t in titles)
    assert not any(t.startswith("WSJ was not") for t in titles)


def test_parse_digest_skips_placeholder_line():
    sections = parse_digest(SAMPLE)
    outlets = {s.outlet: s for s in sections}
    assert "AP" not in outlets or outlets["AP"].headlines == []


def test_flatten_preserves_outlet_order():
    sections = parse_digest(SAMPLE)
    flat = flatten_headlines(sections)
    assert flat[0].outlet == "WSJ"
    assert flat[-1].outlet == "NBC"
    assert len(flat) == 5


def test_find_latest_digest_picks_newest(tmp_path):
    (tmp_path / "headlines-2026-07-01.md").write_text("## WSJ\n")
    (tmp_path / "headlines-2026-07-02.md").write_text("## WSJ\n")
    latest = find_latest_digest(str(tmp_path))
    assert latest.endswith("headlines-2026-07-02.md")


def test_find_latest_digest_none_when_empty(tmp_path):
    assert find_latest_digest(str(tmp_path)) is None
