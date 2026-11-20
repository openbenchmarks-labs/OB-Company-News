from __future__ import annotations

import os
from typing import Any

from harness.models import Case, Hit
from harness.tool_base import WebAdapter, hit


def _parse(payload: Any) -> list[Hit]:
    return [item for row in (payload or {}).get("results") or [] if (item := hit(row.get("url"), row.get("title"), row.get("snippet")))]


def _build(case: Case):
    return "POST", "https://request.usestring.ai/v1/search", {"Authorization": f"Bearer {os.environ['STRING_API_KEY']}", "Content-Type": "application/json"}, {"query": case.question, "engine": "google"}, None, 45


def setup(name: str) -> WebAdapter:
    return WebAdapter(name, "https://portal.usestring.ai/docs/api-reference/search", ("STRING_API_KEY",), _build, _parse)
