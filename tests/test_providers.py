import pytest

from ann_app.providers import (
    AnthropicProvider,
    GeminiProvider,
    OpenAIProvider,
    ProviderError,
    _gemini_text,
    _openai_text,
    build_provider,
)


class _TextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _AnthropicMessage:
    def __init__(self, text):
        self.content = [_TextBlock(text)]


class _AnthropicClient:
    def __init__(self, text):
        self.text = text
        self.kwargs = None

    class _Messages:
        def __init__(self, outer):
            self._outer = outer

        def create(self, **kwargs):
            self._outer.kwargs = kwargs
            return _AnthropicMessage(self._outer.text)

    @property
    def messages(self):
        return self._Messages(self)


class _OpenAIResponse:
    def __init__(self, output_text):
        self.output_text = output_text


class _OpenAIClient:
    def __init__(self, text):
        self.text = text
        self.kwargs = None

    class _Responses:
        def __init__(self, outer):
            self._outer = outer

        def create(self, **kwargs):
            self._outer.kwargs = kwargs
            return _OpenAIResponse(self._outer.text)

    @property
    def responses(self):
        return self._Responses(self)


class _GeminiResponse:
    def __init__(self, text):
        self.text = text


class _GeminiClient:
    def __init__(self, text):
        self.text = text
        self.kwargs = None

    class _Models:
        def __init__(self, outer):
            self._outer = outer

        def generate_content(self, **kwargs):
            self._outer.kwargs = kwargs
            return _GeminiResponse(self._outer.text)

    @property
    def models(self):
        return self._Models(self)


def test_anthropic_provider_normalizes_text_and_request_shape():
    client = _AnthropicClient('{"WSJ": [0]}')
    provider = AnthropicProvider(client=client)

    text = provider.complete("prompt", "claude-test")

    assert text == '{"WSJ": [0]}'
    assert client.kwargs == {
        "model": "claude-test",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": "prompt"}],
    }


def test_openai_provider_normalizes_text_and_request_shape():
    client = _OpenAIClient('{"WSJ": [0]}')
    provider = OpenAIProvider(client=client)

    text = provider.complete("prompt", "gpt-test")

    assert text == '{"WSJ": [0]}'
    assert client.kwargs == {
        "model": "gpt-test",
        "input": "prompt",
        "max_output_tokens": 1024,
    }


def test_gemini_provider_normalizes_text_and_request_shape():
    client = _GeminiClient('{"WSJ": [0]}')
    provider = GeminiProvider(client=client)

    text = provider.complete("prompt", "gemini-test")

    assert text == '{"WSJ": [0]}'
    assert client.kwargs == {
        "model": "gemini-test",
        "contents": "prompt",
        "config": {"max_output_tokens": 1024},
    }


def test_gemini_text_can_fall_back_to_candidate_parts():
    class _Part:
        text = '{"WSJ": [1]}'

    class _Content:
        parts = [_Part()]

    class _Candidate:
        content = _Content()

    class _Response:
        text = None
        candidates = [_Candidate()]

    assert _gemini_text(_Response()) == '{"WSJ": [1]}'


def test_openai_text_can_fall_back_to_output_content():
    class _Content:
        type = "output_text"
        text = '{"WSJ": [1]}'

    class _Item:
        content = [_Content()]

    class _Response:
        output = [_Item()]

    assert _openai_text(_Response()) == '{"WSJ": [1]}'


def test_build_provider_rejects_unknown_provider():
    with pytest.raises(ProviderError):
        build_provider("local")


def test_anthropic_provider_missing_key_fails_clearly(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider().complete("prompt", "claude-test")


def test_openai_provider_missing_key_fails_clearly(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
        OpenAIProvider().complete("prompt", "gpt-test")


def test_gemini_provider_missing_key_fails_clearly(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(ProviderError, match="GEMINI_API_KEY"):
        GeminiProvider().complete("prompt", "gemini-test")
