from __future__ import annotations

import json
import os
import time
from typing import Any

import boto3
from botocore.config import Config


def model_id() -> str:
    return os.getenv("BEDROCK_JUDGE_MODEL", "us.anthropic.claude-opus-5")


def json_object(text: str, key: str) -> dict[str, Any] | None:
    """The first JSON object in a judge reply that carries `key`.

    A reply can mention other braces before or after that object. Taking the
    first `{` through the last `}` makes such a reply unreadable.
    """
    decoder = json.JSONDecoder()
    body = text or ""
    index = 0
    while True:
        start = body.find("{", index)
        if start < 0:
            return None
        try:
            payload, end = decoder.raw_decode(body, start)
        except json.JSONDecodeError:
            index = start + 1
            continue
        if isinstance(payload, dict) and key in payload:
            return payload
        index = end


def _reply_text(response: dict[str, Any]) -> str:
    return "\n".join(
        block.get("text", "")
        for block in response.get("output", {}).get("message", {}).get("content", [])
        if isinstance(block, dict)
    ).strip()


def call_json(
    system: str, payload: dict[str, Any], *, max_tokens: int, key: str,
) -> tuple[dict[str, Any], dict[str, int]]:
    """Ask the judge and return the first JSON object carrying `key`.

    A transport error or an unreadable reply is retried; tokens from every
    reply are counted.
    """
    client = boto3.client(
        "bedrock-runtime",
        region_name=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1",
        config=Config(max_pool_connections=50, retries={"max_attempts": 3, "mode": "adaptive"},
                      read_timeout=180, connect_timeout=10),
    )
    last: Exception | None = None
    tokens = {"input_tokens": 0, "output_tokens": 0}
    for attempt in range(4):
        try:
            kwargs: dict[str, Any] = {
                "modelId": model_id(),
                "system": [{"text": system}],
                "messages": [{"role": "user", "content": [{"text": json.dumps(payload, ensure_ascii=False)}]}],
                "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.0},
                "additionalModelRequestFields": {"thinking": {"type": "disabled"}},
            }
            try:
                response = client.converse(**kwargs)
            except Exception as exc:  # Some Bedrock profiles reject explicit thinking/temperature.
                if "thinking" not in str(exc).lower() and "temperature" not in str(exc).lower():
                    raise
                kwargs.pop("additionalModelRequestFields", None)
                kwargs["inferenceConfig"].pop("temperature", None)
                response = client.converse(**kwargs)
            usage = response.get("usage") or {}
            tokens["input_tokens"] += int(usage.get("inputTokens") or 0)
            tokens["output_tokens"] += int(usage.get("outputTokens") or 0)
            text = _reply_text(response)
            parsed = json_object(text, key)
            if parsed is not None:
                return parsed, tokens
            last = ValueError(f"judge reply has no JSON object with {key!r}: {text[:200]}")
        except Exception as exc:  # noqa: BLE001
            last = exc
        if attempt < 3:
            time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"Bedrock judge failed: {last}")
