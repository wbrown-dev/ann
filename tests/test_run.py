from datetime import date

import ann
from ann_app.cache import save_candidates
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
        lambda candidates, **kwargs: {"WSJ": candidates, "NYT": [], "NBC": [], "AP": []},
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
        lambda candidates, **kwargs: {"WSJ": [], "NYT": [], "NBC": [], "AP": []},
    )

    rc = ann.run(date(2026, 7, 2), dry_run=False, within_hours=36)

    assert rc == 2
    assert not (tmp_path / "headlines-2026-07-02.md").exists()


def test_run_use_cache_skips_fetch(tmp_path, monkeypatch):
    cache_dir = tmp_path / ".cache"
    target = date(2026, 7, 2)
    save_candidates(
        [Candidate(outlet="WSJ", title="Cached Story", link="https://wsj.com/c")],
        target,
        cache_dir=str(cache_dir),
    )

    readme = tmp_path / "README.md"
    readme.write_text("# ANN\n\n[Go to Today's Headlines.](headlines-old.md)\n", encoding="utf-8")

    def _fail_fetch(within_hours):
        raise AssertionError("fetch_all must not be called with --use-cache")

    monkeypatch.setattr(ann, "REPO_ROOT", str(tmp_path))
    monkeypatch.setattr(ann, "fetch_all", _fail_fetch)
    monkeypatch.setattr("ann_app.cache.DEFAULT_CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(
        ann,
        "select_headlines",
        lambda candidates, **kwargs: {"WSJ": candidates, "NYT": [], "NBC": [], "AP": []},
    )

    rc = ann.run(target, dry_run=False, within_hours=36, use_cache=True)

    assert rc == 0
    digest = tmp_path / "headlines-2026-07-02.md"
    assert digest.exists()
    assert "Cached Story" in digest.read_text(encoding="utf-8")


def test_run_passes_model_provider_and_model(tmp_path, monkeypatch):
    seen = {}

    monkeypatch.setattr(ann, "REPO_ROOT", str(tmp_path))
    monkeypatch.setattr(ann, "fetch_all", lambda within_hours: _fetch_result())

    def _select(candidates, **kwargs):
        seen.update(kwargs)
        return {"WSJ": candidates, "NYT": [], "NBC": [], "AP": []}

    monkeypatch.setattr(ann, "select_headlines", _select)

    rc = ann.run(
        date(2026, 7, 2),
        dry_run=True,
        within_hours=36,
        model_provider="openai",
        model="gpt-test",
    )

    assert rc == 0
    assert seen == {"provider": "openai", "model": "gpt-test"}
