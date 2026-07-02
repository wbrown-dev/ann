from ann_app.config import (
    DEFAULT_OUTLET_FEEDS,
    resolve_outlet_config,
)


def test_default_config_is_the_four_outlets():
    feeds, display, accents = resolve_outlet_config(None)

    assert list(feeds) == list(DEFAULT_OUTLET_FEEDS)
    assert set(feeds) == {"WSJ", "NYT", "NBC", "AP"}
    assert set(display) == set(feeds)
    assert set(accents) == set(feeds)


def test_empty_env_leaves_defaults_unchanged():
    feeds, _display, _accents = resolve_outlet_config("   ")

    assert set(feeds) == {"WSJ", "NYT", "NBC", "AP"}


def test_enabling_extra_outlet_adds_feeds_display_and_accent():
    feeds, display, accents = resolve_outlet_config("GUARDIAN")

    assert "GUARDIAN" in feeds
    assert feeds["GUARDIAN"]
    assert display["GUARDIAN"] == "The Guardian"
    assert accents["GUARDIAN"].startswith("#")
    assert set(feeds) == {"WSJ", "NYT", "NBC", "AP", "GUARDIAN"}


def test_multiple_extras_case_and_whitespace_insensitive():
    feeds, _display, _accents = resolve_outlet_config(" guardian , Bbc ,npr ")

    assert set(feeds) == {"WSJ", "NYT", "NBC", "AP", "GUARDIAN", "BBC", "NPR"}


def test_unknown_extra_outlet_is_ignored():
    feeds, _display, _accents = resolve_outlet_config("REUTERS,GUARDIAN")

    assert "REUTERS" not in feeds
    assert "GUARDIAN" in feeds


def test_duplicate_extra_outlet_enabled_once():
    feeds, _display, _accents = resolve_outlet_config("BBC,bbc")

    assert set(feeds) == {"WSJ", "NYT", "NBC", "AP", "BBC"}


def test_resolver_does_not_mutate_default_feeds():
    feeds, _display, _accents = resolve_outlet_config("GUARDIAN")
    feeds["WSJ"].append("https://example.com/injected")

    assert "https://example.com/injected" not in DEFAULT_OUTLET_FEEDS["WSJ"]
