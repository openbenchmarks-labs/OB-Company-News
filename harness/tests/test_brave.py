from unittest.mock import patch

import pytest

from harness.models import Case
from harness.registry import DEFAULT_ENDPOINTS, all_adapters

CASE = Case(id="one", question="Unchanged question?")


def test_brave_web_request_and_parse():
    adapter = all_adapters()["brave"]
    with patch.dict("os.environ", {"BRAVE_SEARCH_API_KEY": "test-key"}):
        method, url, headers, body, params, timeout = adapter.build(CASE)
    assert (method, url, body, timeout) == ("GET", "https://api.search.brave.com/res/v1/web/search", None, 45)
    assert params == {"q": "Unchanged question?", "count": 10, "result_filter": "web"}
    assert headers["X-Subscription-Token"] == "test-key"

    hits = adapter.parse({"web": {"results": [
        {"url": "https://a.com", "title": "A", "description": "desc"},
        {"url": "https://b.com", "title": "B", "snippet": "fallback snippet"},
        {"url": "", "title": "dropped"},
    ]}})
    assert [h.url for h in hits] == ["https://a.com", "https://b.com"]
    assert hits[0].snippet == "desc"
    assert hits[1].snippet == "fallback snippet"


def test_brave_llm_request_and_parse():
    adapter = all_adapters()["brave_llm"]
    with patch.dict("os.environ", {"BRAVE_SEARCH_API_KEY": "test-key"}):
        method, url, headers, body, params, timeout = adapter.build(CASE)
    assert (method, url, params, timeout) == ("POST", "https://api.search.brave.com/res/v1/llm/context", None, 30)
    assert headers["X-Subscription-Token"] == "test-key"
    assert body["q"] == "Unchanged question?"
    assert body["enable_local"] is False

    hits = adapter.parse({"grounding": {"generic": [
        {"url": "https://a.com", "title": "A", "snippets": ["one", "two"]},
        {"url": "https://b.com", "title": "B", "snippets": "single"},
    ]}})
    assert hits[0].snippet.split() == ["one", "two"]  # every snippet piece is kept
    assert hits[1].snippet == "single"


def test_brave_handles_empty_payloads():
    assert all_adapters()["brave"].parse(None) == []
    assert all_adapters()["brave"].parse({}) == []
    assert all_adapters()["brave_llm"].parse({"grounding": {}}) == []


def test_brave_setups_run_by_default_as_web_search():
    adapters = all_adapters()
    for name in ("brave", "brave_llm"):
        assert name in DEFAULT_ENDPOINTS
        assert adapters[name].surface == "web-search"


@pytest.mark.parametrize("payload", [
    {"_raw": "<html>not json</html>"},                         # invalid JSON, as kept by the HTTP client
    {"query": {"original": "q"}},                              # "web" section missing
    {"web": None},                                             # null section
    {"web": {"results": None}},                                # null results
    {"data": {"items": [{"link": "https://a.com"}]}},          # provider changed its schema
])
def test_brave_web_returns_no_hits_for_missing_or_changed_fields(payload):
    assert all_adapters()["brave"].parse(payload) == []


def test_brave_web_keeps_rows_with_null_fields_and_drops_rows_without_url():
    hits = all_adapters()["brave"].parse({"web": {"results": [
        {"url": "https://a.com", "title": None, "description": None},
        {"url": None, "title": "no link"},
        {"title": "url key missing"},
    ]}})
    assert [(h.url, h.title, h.snippet) for h in hits] == [("https://a.com", "", "")]

