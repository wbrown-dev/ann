from datetime import date

import ann
from ann_app.parse import flatten_headlines, parse_digest
from ann_app.retrospective import (
    build_retrospective,
    cluster_stories,
    find_recent_digests,
    rank_stories,
    retrospective_filename,
)

DAY1 = """## WSJ

1. [Russia launches massive missile barrage on Kyiv killing dozens](https://wsj.com/kyiv1)
2. [US declines to renew USMCA trade pact at deadline](https://wsj.com/usmca1)

## NYT

1. [Fed holds interest rates steady amid cooling labor market](https://nyt.com/fed1)

## Note

No access limitations encountered this session.
"""

DAY2 = """## WSJ

1. [Russian missile attack on Kyiv kills at least 20 people](https://wsj.com/kyiv2)

## NBC

1. [Trump won't renew USMCA trade deal reversing course](https://nbc.com/usmca2)
2. [Medicare will begin covering weight loss drugs](https://nbc.com/glp1)

## Note

No access limitations encountered this session.
"""

DAY3 = """## AP

1. [Russian missile attack kills 20 in Kyiv as strikes hit Moscow](https://apnews.com/kyiv3)
2. A cross-verified summary of the day with no confirmed link.

## Note

No access limitations encountered this session.
"""


def _write_week(tmp_path):
    (tmp_path / "headlines-2026-06-30.md").write_text(DAY1, encoding="utf-8")
    (tmp_path / "headlines-2026-07-01.md").write_text(DAY2, encoding="utf-8")
    (tmp_path / "headlines-2026-07-02.md").write_text(DAY3, encoding="utf-8")


def test_find_recent_digests_windows_from_latest(tmp_path):
    _write_week(tmp_path)
    (tmp_path / "headlines-2026-06-01.md").write_text(DAY1, encoding="utf-8")

    recent = find_recent_digests(str(tmp_path), days=7)

    assert [f.date for f in recent] == [
        date(2026, 6, 30),
        date(2026, 7, 1),
        date(2026, 7, 2),
    ]


def test_cluster_merges_recurring_story_across_days():
    dated = [
        (date(2026, 6, 30), flatten_headlines(parse_digest(DAY1))),
        (date(2026, 7, 1), flatten_headlines(parse_digest(DAY2))),
        (date(2026, 7, 2), flatten_headlines(parse_digest(DAY3))),
    ]

    stories = rank_stories(cluster_stories(dated))

    top = stories[0]
    assert "Kyiv" in top.title
    assert len(top.dates) == 3
    assert top.appearances == 3


def test_distinct_stories_do_not_merge():
    dated = [(date(2026, 6, 30), flatten_headlines(parse_digest(DAY1)))]

    stories = cluster_stories(dated)

    titles = sorted(s.title for s in stories)
    assert len(stories) == 3
    assert any("Fed" in t for t in titles)


def test_ranking_orders_by_distinct_days():
    dated = [
        (date(2026, 6, 30), flatten_headlines(parse_digest(DAY1))),
        (date(2026, 7, 1), flatten_headlines(parse_digest(DAY2))),
        (date(2026, 7, 2), flatten_headlines(parse_digest(DAY3))),
    ]

    ranked = rank_stories(cluster_stories(dated))
    day_counts = [len(s.dates) for s in ranked]

    assert day_counts == sorted(day_counts, reverse=True)


def test_build_retrospective_end_to_end(tmp_path):
    _write_week(tmp_path)

    result = build_retrospective(str(tmp_path), days=7)

    assert result.digest_count == 3
    assert result.filename == "retrospective-2026-W27.md"
    assert result.filename == retrospective_filename(date(2026, 7, 2))
    assert "Kyiv" in result.markdown
    assert "3 days" in result.markdown


def test_build_retrospective_no_fabrication(tmp_path):
    _write_week(tmp_path)
    combined = "".join(
        (tmp_path / f"headlines-2026-07-{d:02d}.md").read_text(encoding="utf-8")
        if d != 30
        else (tmp_path / "headlines-2026-06-30.md").read_text(encoding="utf-8")
        for d in (30, 1, 2)
    )

    result = build_retrospective(str(tmp_path), days=7)

    for story in result.stories:
        assert story.title in combined


def test_retro_refuses_below_min_digests(tmp_path, monkeypatch):
    (tmp_path / "headlines-2026-07-02.md").write_text(DAY3, encoding="utf-8")
    monkeypatch.setattr(ann, "REPO_ROOT", str(tmp_path))

    rc = ann.retro(days=7, top=10, dry_run=False)

    assert rc == 2
    assert not list(tmp_path.glob("retrospective-*.md"))


def test_retro_writes_file(tmp_path, monkeypatch):
    _write_week(tmp_path)
    monkeypatch.setattr(ann, "REPO_ROOT", str(tmp_path))

    rc = ann.retro(days=7, top=10, dry_run=False)

    assert rc == 0
    out = tmp_path / "retrospective-2026-W27.md"
    assert out.exists()
    assert "Weekly Retrospective" in out.read_text(encoding="utf-8")
