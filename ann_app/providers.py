from __future__ import annotations

import os
from typing import Protocol

MAX_OUTPUT_TOKENS = 1024


class ProviderError(RuntimeError):
    pass


class ModelProvider(Protocol):
    name: str

    def complete(self, prompt: str, model: str) -> str:
        pass


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, client: object | None = None, api_key: str | None = None) -> None:
        self._client = client
        self._api_key = api_key

    def complete(self, prompt: str, model: str) -> str:
        client = self._client or self._build_client()
        response = client.messages.create(
            model=model,
            max_tokens=MAX_OUTPUT_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return _anthropic_text(response)

    def _build_client(self) -> object:
        api_key = self._api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not set for ANN_MODEL_PROVIDER=anthropic")

        try:
            import anthropic
        except ImportError as exc:
            raise ProviderError("anthropic package is not installed") from exc

        self._client = anthropic.Anthropic(api_key=api_key)
        return self._client


class OpenAIProvider:
    name = "openai"

    def __init__(self, client: object | None = None, api_key: str | None = None) -> None:
        self._client = client
        self._api_key = api_key

    def complete(self, prompt: str, model: str) -> str:
        client = self._client or self._build_client()
        response = client.responses.create(
            model=model,
            input=prompt,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        return _openai_text(response)

    def _build_client(self) -> object:
        api_key = self._api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ProviderError("OPENAI_API_KEY is not set for ANN_MODEL_PROVIDER=openai")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderError("openai package is not installed") from exc

        self._client = OpenAI(api_key=api_key)
        return self._client


class GeminiProvider:
    name = "gemini"

    def __init__(self, client: object | None = None, api_key: str | None = None) -> None:
        self._client = client
        self._api_key = api_key

    def complete(self, prompt: str, model: str) -> str:
        client = self._client or self._build_client()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            # gemini-2.5-flash is a thinking model: reasoning tokens count against
            # max_output_tokens, so leaving thinking on can consume the whole budget
            # and return empty text. Index-only selection needs no reasoning.
            config={
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "thinking_config": {"thinking_budget": 0},
            },
        )
        return _gemini_text(response)

    def _build_client(self) -> object:
        api_key = (
            self._api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if not api_key:
            raise ProviderError("GEMINI_API_KEY is not set for ANN_MODEL_PROVIDER=gemini")

        try:
            from google import genai
        except ImportError as exc:
            raise ProviderError("google-genai package is not installed") from exc

        self._client = genai.Client(api_key=api_key)
        return self._client


def build_provider(name: str, client: object | None = None) -> ModelProvider:
    normalized = name.strip().lower()
    if normalized == "anthropic":
        return AnthropicProvider(client=client)
    if normalized == "openai":
        return OpenAIProvider(client=client)
    if normalized == "gemini":
        return GeminiProvider(client=client)
    raise ProviderError(f"unsupported model provider {name!r}")


def _anthropic_text(response: object) -> str:
    blocks = getattr(response, "content", [])
    return "".join(
        getattr(block, "text", "")
        for block in blocks
        if getattr(block, "type", None) == "text"
    )


def _openai_text(response: object) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return output_text

    chunks: list[str] = []
    for item in getattr(response, "output", []):
        for content in getattr(item, "content", []):
            if getattr(content, "type", None) == "output_text":
                chunks.append(getattr(content, "text", ""))

    return "".join(chunks)


def _gemini_text(response: object) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text

    chunks: list[str] = []
    for candidate in getattr(response, "candidates", []):
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []):
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str):
                chunks.append(part_text)

    return "".join(chunks)
