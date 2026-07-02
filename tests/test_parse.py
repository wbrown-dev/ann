import os

from ann_app.parse import (
    find_latest_digest,
    find_latest_digest_state,
    find_latest_retrospective,
    find_latest_retrospective_state,
    flatten_headlines,
    parse_digest,
    parse_retrospective,
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

RETROSPECTIVE_SAMPLE = """# Weekly Retrospective — 2026 W27

The stories from the last 3 daily digest(s) (2026-06-30 to 2026-07-02) that recurred across the most days.

1. [Russian missile attack kills 20 in Kyiv as strikes hit Moscow](https://apnews.com/kyiv3) — 3 days · WSJ, AP
   Jun 30, Jul 1, Jul 2

2. A cross-verified summary with no confirmed link — 2 days · NYT
   Jul 1, Jul 2

## Note

Every item is a verbatim headline carried from a prior daily digest; nothing is rewritten or invented.
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


def test_find_latest_digest_state_includes_mtime(tmp_path):
    latest = tmp_path / "headlines-2026-07-02.md"
    latest.write_text("## WSJ\n")
    state = find_latest_digest_state(str(tmp_path))
    assert state is not None

    latest.write_text("## NYT\n")
    os.utime(latest, ns=(state.mtime_ns + 1_000_000, state.mtime_ns + 1_000_000))
    updated = find_latest_digest_state(str(tmp_path))

    assert updated is not None
    assert updated.path == str(latest)
    assert updated.mtime_ns > state.mtime_ns


def test_parse_retrospective_extracts_items_and_note():
    retrospective = parse_retrospective(RETROSPECTIVE_SAMPLE)

    assert retrospective.title == "Weekly Retrospective — 2026 W27"
    assert "last 3 daily digest" in retrospective.intro
    assert len(retrospective.items) == 2

    linked = retrospective.items[0]
    assert linked.rank == 1
    assert linked.title == "Russian missile attack kills 20 in Kyiv as strikes hit Moscow"
    assert linked.link == "https://apnews.com/kyiv3"
    assert linked.meta == "3 days · WSJ, AP"
    assert linked.dates == "Jun 30, Jul 1, Jul 2"

    plain = retrospective.items[1]
    assert plain.link is None
    assert plain.title == "A cross-verified summary with no confirmed link"
    assert plain.meta == "2 days · NYT"
    assert "verbatim headline" in retrospective.note


def test_find_latest_retrospective_picks_newest(tmp_path):
    (tmp_path / "retrospective-2026-W26.md").write_text(RETROSPECTIVE_SAMPLE, encoding="utf-8")
    (tmp_path / "retrospective-2026-W27.md").write_text(RETROSPECTIVE_SAMPLE, encoding="utf-8")

    latest = find_latest_retrospective(str(tmp_path))
    state = find_latest_retrospective_state(str(tmp_path))

    assert latest is not None
    assert latest.endswith("retrospective-2026-W27.md")
    assert state is not None
    assert state.path == latest


def test_find_latest_retrospective_none_when_empty(tmp_path):
    assert find_latest_retrospective(str(tmp_path)) is None
    assert find_latest_retrospective_state(str(tmp_path)) is None
