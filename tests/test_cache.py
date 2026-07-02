import json
from datetime import UTC, date, datetime

import pytest

from ann_app.cache import CacheError, load_candidates, save_candidates
from ann_app.fetch import Candidate

TARGET = date(2026, 7, 2)


def _candidates():
    return [
        Candidate(
            outlet="WSJ",
            title="Story A",
            link="https://wsj.com/a",
            summary="a summary",
            published=datetime(2026, 7, 2, 8, 30, tzinfo=UTC),
        ),
        Candidate(outlet="AP", title="Story B", link="https://apnews.com/b"),
    ]


def test_save_load_round_trip(tmp_path):
    save_candidates(_candidates(), TARGET, cache_dir=str(tmp_path))
    loaded = load_candidates(TARGET, cache_dir=str(tmp_path))

    assert loaded == _candidates()
    assert loaded[0].published == datetime(2026, 7, 2, 8, 30, tzinfo=UTC)
    assert loaded[1].published is None
    assert loaded[1].summary == ""


def test_load_missing_raises(tmp_path):
    with pytest.raises(CacheError, match="no candidate cache"):
        load_candidates(TARGET, cache_dir=str(tmp_path))


def test_load_version_mismatch_raises(tmp_path):
    path = save_candidates(_candidates(), TARGET, cache_dir=str(tmp_path))
    payload = json.loads((tmp_path / path.split("/")[-1]).read_text(encoding="utf-8"))
    payload["version"] = 999
    (tmp_path / path.split("/")[-1]).write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CacheError, match="version mismatch"):
        load_candidates(TARGET, cache_dir=str(tmp_path))
