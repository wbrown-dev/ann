from datetime import date

import ann
from ann_app.fetch import Candidate, FetchResult


def _fetch_result():
    return FetchResult(
        candidates=[Candidate(outlet="WSJ", title="Story A", link="https://wsj.com/a")],
        errors={},
    )


def test_run_writes_digest_and_updates_readme(tmp_path, monkeypatch):
    readme = tmp_path / "README.md"
    readme.write_text("# ANN\n\n[Go to Today's Headlines.](headlines-old.md)\n", encoding="utf-8")

    monkeypatch.setattr(ann, "REPO_ROOT", str(tmp_path))
    monkeypatch.setattr(ann, "fetch_all", lambda within_hours: _fetch_result())
    monkeypatch.setattr(
        ann,
        "select_headlines",
        lambda candidates: {"WSJ": candidates, "NYT": [], "NBC": [], "AP": []},
    )

    rc = ann.run(date(2026, 7, 2), dry_run=False, within_hours=36)

    assert rc == 0
    digest = tmp_path / "headlines-2026-07-02.md"
    assert digest.exists()
    assert "Story A" in digest.read_text(encoding="utf-8")
    assert "[Go to Today's Headlines.](headlines-2026-07-02.md)" in readme.read_text(encoding="utf-8")


def test_run_refuses_empty_digest(tmp_path, monkeypatch):
    monkeypatch.setattr(ann, "REPO_ROOT", str(tmp_path))
    monkeypatch.setattr(ann, "fetch_all", lambda within_hours: _fetch_result())
    monkeypatch.setattr(
        ann,
        "select_headlines",
        lambda candidates: {"WSJ": [], "NYT": [], "NBC": [], "AP": []},
    )

    rc = ann.run(date(2026, 7, 2), dry_run=False, within_hours=36)

    assert rc == 2
    assert not (tmp_path / "headlines-2026-07-02.md").exists()
