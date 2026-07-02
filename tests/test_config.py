from ann_app.config import (
    DEFAULT_OUTLET_FEEDS,
    resolve_model_settings,
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


def test_resolve_model_settings_defaults_to_anthropic(monkeypatch):
    monkeypatch.delenv("ANN_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("ANN_MODEL", raising=False)

    provider, model = resolve_model_settings()

    assert provider == "anthropic"
    assert model == "claude-sonnet-5"


def test_resolve_model_settings_treats_blank_env_as_unset(monkeypatch):
    monkeypatch.setenv("ANN_MODEL_PROVIDER", "  ")
    monkeypatch.setenv("ANN_MODEL", "  ")

    provider, model = resolve_model_settings()

    assert provider == "anthropic"
    assert model == "claude-sonnet-5"


def test_resolve_model_settings_accepts_openai():
    provider, model = resolve_model_settings("openai", "gpt-test")

    assert provider == "openai"
    assert model == "gpt-test"


def test_resolve_model_settings_accepts_gemini_default_model(monkeypatch):
    monkeypatch.delenv("ANN_MODEL", raising=False)

    provider, model = resolve_model_settings("gemini")

    assert provider == "gemini"
    assert model == "gemini-2.5-flash"


def test_resolve_model_settings_rejects_unknown_provider():
    try:
        resolve_model_settings("local", "model")
    except ValueError as exc:
        assert "unsupported model provider" in str(exc)
    else:
        raise AssertionError("expected ValueError")
