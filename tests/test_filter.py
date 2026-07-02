import pytest

from ann_app.filter import FilterError, _parse_response


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
