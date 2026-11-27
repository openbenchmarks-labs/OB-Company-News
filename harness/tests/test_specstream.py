from unittest.mock import patch

import pytest

from harness.models import Case
from harness.registry import DEFAULT_ENDPOINTS, all_adapters, pricing

QUESTION = "Who became CEO of Example Corp in 2026?"

# The reply shape of POST /v1/web-search: everything sits under "data".
REPLY = {
    "data": {
        "request_id": "r1",
        "took_ms": 2400,
        "price_usd": 0.005,
        "sources": [
            {
                "url": "https://example.com/news",
                "title": "Example Corp names CEO",
                "site": "example.com",
                "snippet": "Short engine snippet",
                "highlights": ["Example Corp named Jane Doe chief executive", "effective March 3, 2026."],
                "published": "2026-03-01",
            },
            {"url": "https://example.org/brief", "title": "Brief", "snippet": "Page not read in time", "highlights": []},
            {"url": "", "title": "No address", "snippet": "dropped"},
            "not a source",
        ],
    }
}


@pytest.mark.parametrize(
    "name,flags,price",
    [
        ("specstream", {"compact": True}, 0.005),
        ("specstream_passages", {"passages": True}, 0.005),
        ("specstream_fast", {"speed": "fast"}, 0.001),
    ],
)
def test_specstream_request(name, flags, price):
    adapter = all_adapters()[name]
    with patch.dict("os.environ", {"SPECSTREAM_API_KEY": "test-key"}):
        method, url, headers, body, params, timeout = adapter.build(Case(id="c1", question=QUESTION))
    assert (method, url, body, params, timeout) == (
        "POST", "https://api.specstream.ai/v1/web-search", {"q": QUESTION, "num": 10, **flags}, None, 45,
    )
    assert headers["Authorization"] == "Bearer test-key"
    assert name in DEFAULT_ENDPOINTS
    assert pricing()[name] == {"list_usd": price, "basis": "list"}


def test_specstream_parse_reads_data_sources():
    hits = all_adapters()["specstream_passages"].parse(REPLY)
    assert [h.url for h in hits] == ["https://example.com/news", "https://example.org/brief"]
    assert hits[0].snippet == "Example Corp named Jane Doe chief executive effective March 3, 2026."
    assert hits[0].metadata == {"published": "2026-03-01"}
    assert hits[1].snippet == "Page not read in time"


def test_specstream_parse_compact_snippet():
    reply = {"data": {"sources": [{"url": "https://example.com/a", "title": "A", "snippet": "Best matching lines"}]}}
    hits = all_adapters()["specstream"].parse(reply)
    assert [(h.url, h.title, h.snippet) for h in hits] == [("https://example.com/a", "A", "Best matching lines")]


@pytest.mark.parametrize("payload", [None, {}, {"data": None}, {"data": {"sources": None}},
                                     {"error": {"code": "unauthorized", "message": "no key"}}])
def test_specstream_parse_empty(payload):
    assert all_adapters()["specstream"].parse(payload) == []
