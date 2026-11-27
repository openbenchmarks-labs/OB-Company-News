from __future__ import annotations

import os
from typing import Any

from harness.models import Case, Hit
from harness.tool_base import WebAdapter, hit

# Each mode is one request to the same endpoint; only the body flag changes.
MODES = {
    "compact": {"compact": True},
    "passages": {"passages": True},
    "fast": {"speed": "fast"},
}


def _text(row: dict[str, Any]) -> str:
    # passages=true puts each page's best passages in `highlights`; a page not read in time keeps `snippet`.
    highlights = [part for part in row.get("highlights") or [] if isinstance(part, str) and part.strip()]
    return " ".join(highlights) or row.get("snippet") or ""


def _parse(payload: Any) -> list[Hit]:
    # A successful reply is {"data": {...}}; the search results are data.sources, in rank order.
    data = payload.get("data") if isinstance(payload, dict) else None
    rows = data.get("sources") if isinstance(data, dict) else None
    return [item for row in (rows if isinstance(rows, list) else []) if isinstance(row, dict)
            if (item := hit(row.get("url"), row.get("title"), _text(row), published=row.get("published")))]


def setup(name: str, *, mode: str) -> WebAdapter:
    flags = MODES[mode]

    def build(case: Case):
        return (
            "POST", "https://api.specstream.ai/v1/web-search",
            {"Authorization": f"Bearer {os.environ['SPECSTREAM_API_KEY']}", "Content-Type": "application/json"},
            {"q": case.question, "num": 10, **flags},
            None, 45,
        )
    return WebAdapter(name, "https://specstream.ai/docs/search-api", ("SPECSTREAM_API_KEY",), build, _parse)
