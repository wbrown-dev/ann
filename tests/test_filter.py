import pytest

from ann_app.fetch import Candidate
from ann_app.filter import FilterError, _parse_response, select_headlines


class _TextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _Message:
    def __init__(self, text):
        self.content = [_TextBlock(text)]


class StubClient:
    def __init__(self, response_text):
        self._response_text = response_text
        self.calls = 0

    class _Messages:
        def __init__(self, outer):
            self._outer = outer

        def create(self, **kwargs):
            self._outer.calls += 1
            return _Message(self._outer._response_text)

    @property
    def messages(self):
        return self._Messages(self)


def _wsj(n):
    return [Candidate(outlet="WSJ", title=f"WSJ {i}", link=f"https://wsj.com/{i}") for i in range(n)]


def test_select_headlines_index_only_and_ranked():
    candidates = _wsj(4)
    client = StubClient('{"WSJ": [2, 0]}')

    result = select_headlines(candidates, client=client)

    assert [c.title for c in result["WSJ"]] == ["WSJ 2", "WSJ 0"]
    assert all(c in candidates for c in result["WSJ"])
    assert client.calls == 1


def test_select_headlines_truncates_to_headlines_per_outlet():
    candidates = _wsj(10)
    client = StubClient('{"WSJ": [0, 1, 2, 3, 4, 5, 6]}')

    result = select_headlines(candidates, client=client)

    assert len(result["WSJ"]) == 5
    assert [c.title for c in result["WSJ"]] == ["WSJ 0", "WSJ 1", "WSJ 2", "WSJ 3", "WSJ 4"]


def test_select_headlines_rejects_out_of_range_and_non_int():
    candidates = _wsj(3)
    client = StubClient('{"WSJ": [0, 9, "x", 2]}')

    result = select_headlines(candidates, client=client)

    assert [c.title for c in result["WSJ"]] == ["WSJ 0", "WSJ 2"]


def test_select_headlines_empty_candidates_returns_empty_without_client():
    assert select_headlines([]) == {}


def test_parse_response_plain_json():
    text = '{"WSJ": [0, 1], "NYT": [2]}'
    assert _parse_response(text) == {"WSJ": [0, 1], "NYT": [2]}


def test_parse_response_fenced_json():
    text = '```json\n{"WSJ": [0, 1]}\n```'
    assert _parse_response(text) == {"WSJ": [0, 1]}


def test_parse_response_fenced_json_with_prose():
    text = 'Here are my picks:\n```json\n{"WSJ": [0, 1]}\n```\nThanks!'
    assert _parse_response(text) == {"WSJ": [0, 1]}


def test_parse_response_bare_object_in_prose():
    text = 'Sure - {"WSJ": [3], "NYT": [0, 2]} is my answer.'
    assert _parse_response(text) == {"WSJ": [3], "NYT": [0, 2]}


def test_parse_response_invalid_raises():
    with pytest.raises(FilterError):
        _parse_response("not json")
