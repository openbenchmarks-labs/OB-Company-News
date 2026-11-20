"""Extruct AI Tables news arm. research_reasoning on a generic table, one row per question."""

from __future__ import annotations

import os
import time
from typing import Any

from harness.http_client import now, request_json
from harness.models import Case, HttpAudit, SearchResult
from harness.tool_base import ProviderAdapter, dedupe, hit

API = "https://api.extruct.ai/v1/tables"
ANSWER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "answer": {"type": "string", "description": "The single atomic fact the question asks for."},
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "url": {"type": "string"},
                    "title": {"type": "string"},
                    "snippet": {"type": "string"},
                },
            },
        },
    },
    "required": ["answer", "sources"],
}
PROMPT = (
    "Answer this company-news factual question. Use the company name and any "
    "domain in the question.\n\n"
    "Rules for `answer`:\n"
    "- Return ONLY the atomic fact (product/program/fund name, dollar amount, "
    "person, full address, acquirer legal name, headcount). No wrapping sentence "
    "unless the fact itself is a phrase.\n"
    "- Copy the published proper name. Do not paraphrase. Keep brand prefixes "
    "('Acme Pro Suite' not 'Pro Suite') and legal suffixes (Inc., L.L.C., "
    "Corporation, Holdings) when the source uses them.\n"
    "- Money: keep the exact figure and currency as written. Do not round "
    "($1,234,500 stays $1,234,500). If the source says approximately, keep "
    "that word and the exact number.\n"
    "- Locations: city + state/country; street addresses include street, unit, "
    "city, and state.\n"
    "- People: full published name, including credentials if present.\n"
    "- For 'what product/program/fund' questions, the answer IS the proper "
    "name from the headline or first paragraph. Do not describe the launch "
    "instead of naming it.\n"
    "- If you cannot verify a primary source, leave `answer` empty and "
    "`sources` empty. Never write 'Not found'. Do not guess.\n\n"
    "At most 10 sources.\n\nQuestion: {input}"
)


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {os.environ['EXTRUCT_API_TOKEN']}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _ensure_table() -> str:
    table_id = os.environ.get("EXTRUCT_NEWS_TABLE_ID", "").strip()
    if table_id:
        return table_id
    created = request_json(
        "POST",
        API,
        headers=_headers(),
        body={
            "name": "OpenBenchmarks company-news (Extruct Tables)",
            "kind": "generic",
            "column_configs": [
                {"kind": "input", "name": "Question", "key": "input"},
                {
                    "kind": "agent",
                    "name": "News fact",
                    "key": "news_fact",
                    "value": {
                        "agent_type": "research_reasoning",
                        "prompt": PROMPT,
                        "output_format": "json",
                        "output_schema": ANSWER_SCHEMA,
                    },
                },
            ],
        },
        timeout=60,
    )
    if not created.ok or not (created.response or {}).get("id"):
        raise RuntimeError(created.error or "create table failed")
    os.environ["EXTRUCT_NEWS_TABLE_ID"] = created.response["id"]
    return created.response["id"]


def _unwrap(value: Any) -> dict[str, Any]:
    if isinstance(value, dict) and isinstance(value.get("answer"), dict) and "answer" in value["answer"]:
        return value["answer"]
    if isinstance(value, dict) and ("answer" in value or "sources" in value):
        return value
    return {"answer": str(value or ""), "sources": []}


class ExtructTablesAdapter(ProviderAdapter):
    surface = "news-index"
    docs_url = "https://docs.extruct.ai/api-guides/ai-tables/ai-table-basics"
    required_env = ("EXTRUCT_API_TOKEN",)

    def search(self, case: Case) -> SearchResult:
        self.validate_credentials()
        started = time.perf_counter()
        started_at = now()
        table_id = _ensure_table()
        created = request_json(
            "POST",
            f"{API}/{table_id}/rows",
            headers=_headers(),
            body={"rows": [{"data": {"input": case.question}, "metadata": {"case_id": case.id}}], "run": True},
            timeout=60,
        )
        row = (created.response or [None])[0] if isinstance(created.response, list) else None
        if isinstance(created.response, dict):
            rows = created.response.get("rows") or created.response.get("data") or []
            row = rows[0] if rows else created.response
        row_id = (row or {}).get("id")
        fields: dict[str, Any] = {}
        status = "error"
        if created.ok and row_id:
            deadline = time.time() + 900
            while time.time() < deadline:
                data = request_json("GET", f"{API}/{table_id}/rows/{row_id}", headers=_headers(), timeout=60)
                payload = data.response or {}
                cell = ((payload.get("data") or {}).get("news_fact") or {})
                status = cell.get("status") or payload.get("status") or ""
                if status in {"done", "failed"}:
                    fields = _unwrap(cell.get("value"))
                    break
                time.sleep(10)
        hits = []
        for item in (fields.get("sources") or [])[:10]:
            found = hit(item.get("url"), item.get("title"), item.get("snippet")) if isinstance(item, dict) else None
            if found:
                hits.append(found)
        return SearchResult(
            endpoint=self.name,
            surface=self.surface,
            hits=dedupe(hits),
            audit=HttpAudit(
                method="POST",
                url=f"{API}/{table_id}/run",
                request={"table_id": table_id, "row_id": row_id, "case_id": case.id},
                response={"fields": fields, "create": created.response},
                ok=created.ok and status == "done",
                status_code=created.status_code,
                error="" if status == "done" else (created.error or status or "timeout"),
                attempts=list(created.attempts),
                latency_ms=round((time.perf_counter() - started) * 1000),
                started_at=started_at,
                ended_at=now(),
            ),
        )


def setup(name: str) -> ExtructTablesAdapter:
    return ExtructTablesAdapter(name)
