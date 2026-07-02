import requests

from ann_app.resolve import (
    _extract_params,
    _parse_batchexecute,
    resolve_google_news_url,
)

CANONICAL = "https://apnews.com/article/example-c3559d350a6467e64ac2845d25b5f393"
GNEWS = "https://news.google.com/rss/articles/CBMiExampleId?oc=5"

PAGE = (
    '<c-wiz data-n-a-id="AID123" data-n-a-sg="SIG456" data-n-a-ts="1700000000">'
    "</c-wiz>"
)
BATCH_BODY = (
    ")]}'\n\n"
    '[["wrb.fr","Fbv4je","[\\"garturlres\\",\\"' + CANONICAL + '\\",1]",null,null,null,"generic"]]'
)


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


class FakeSession:
    def __init__(self, page_text=PAGE, batch_text=BATCH_BODY, get_exc=None):
        self.page_text = page_text
        self.batch_text = batch_text
        self.get_exc = get_exc
        self.get_calls = 0
        self.post_calls = 0

    def get(self, url, timeout=None):
        self.get_calls += 1
        if self.get_exc is not None:
            raise self.get_exc
        return FakeResponse(self.page_text)

    def post(self, url, data=None, timeout=None):
        self.post_calls += 1
        return FakeResponse(self.batch_text)


class ExplodingSession:
    def get(self, *a, **k):
        raise AssertionError("network should not be touched")

    post = get


def test_parse_batchexecute_extracts_canonical_url():
    assert _parse_batchexecute(BATCH_BODY) == CANONICAL


def test_parse_batchexecute_returns_none_on_garbage():
    assert _parse_batchexecute("not json at all") is None


def test_extract_params_returns_none_when_attributes_missing():
    assert _extract_params("<div>no signature here</div>") is None


def test_extract_params_reads_id_timestamp_signature():
    assert _extract_params(PAGE) == ("AID123", 1700000000, "SIG456")


def test_non_google_link_passes_through_without_network():
    session = ExplodingSession()
    assert resolve_google_news_url(CANONICAL, session=session) == CANONICAL


def test_successful_resolution_returns_canonical():
    session = FakeSession()
    assert resolve_google_news_url(GNEWS, session=session) == CANONICAL
    assert session.get_calls == 1
    assert session.post_calls == 1


def test_missing_signature_falls_back_to_original_link():
    session = FakeSession(page_text="<html>no attrs</html>")
    assert resolve_google_news_url(GNEWS, session=session) == GNEWS
    assert session.post_calls == 0


def test_request_error_falls_back_to_original_link():
    session = FakeSession(get_exc=requests.ConnectionError("boom"))
    assert resolve_google_news_url(GNEWS, session=session) == GNEWS


def test_cache_resolves_each_link_once():
    session = FakeSession()
    cache: dict[str, str] = {}
    first = resolve_google_news_url(GNEWS, session=session, cache=cache)
    second = resolve_google_news_url(GNEWS, session=session, cache=cache)
    assert first == second == CANONICAL
    assert session.get_calls == 1
