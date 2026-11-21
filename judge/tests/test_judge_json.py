import json
from pathlib import Path

import pytest

from harness import orchestration
from judge import bedrock
from judge.bedrock import json_object

VERDICT = {"correct": True, "cells_hit": 2, "note": "matches"}


def test_braces_before_the_verdict_object_are_skipped():
    text = 'Gold cells {revenue, date} are both present.\n' + json.dumps(VERDICT)
    assert json_object(text, "correct") == VERDICT


def test_braces_after_the_verdict_object_are_ignored():
    text = json.dumps(VERDICT) + '\nFormat used: {"x": 1}'
    assert json_object(text, "correct") == VERDICT


def test_an_object_without_the_key_is_not_taken_as_the_verdict():
    text = '{"cells": ["revenue"]}\n{"bearing_ranks": [1, 4], "note": "ok"}'
    assert json_object(text, "bearing_ranks") == {"bearing_ranks": [1, 4], "note": "ok"}
    assert json_object(text, "correct") is None


def test_unreadable_reply_has_no_object():
    assert json_object("no json here", "correct") is None
    assert json_object("", "correct") is None


class FakeBedrock:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def converse(self, **_kwargs):
        self.calls += 1
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return {"output": {"message": {"content": [{"text": reply}]}},
                "usage": {"inputTokens": 10, "outputTokens": 5}}


def _patch_client(monkeypatch, fake):
    monkeypatch.setattr(bedrock.boto3, "client", lambda *a, **k: fake)
    monkeypatch.setattr(bedrock.time, "sleep", lambda _s: None)


def test_call_json_reads_a_reply_with_leading_braces(monkeypatch):
    fake = FakeBedrock(['Checked {revenue}.\n' + json.dumps(VERDICT)])
    _patch_client(monkeypatch, fake)
    parsed, tokens = bedrock.call_json("sys", {}, max_tokens=64, key="correct")
    assert parsed == VERDICT
    assert tokens == {"input_tokens": 10, "output_tokens": 5}
    assert fake.calls == 1


def test_call_json_retries_an_unreadable_reply_and_counts_all_tokens(monkeypatch):
    fake = FakeBedrock(["I cannot answer in JSON.", json.dumps(VERDICT)])
    _patch_client(monkeypatch, fake)
    parsed, tokens = bedrock.call_json("sys", {}, max_tokens=64, key="correct")
    assert parsed == VERDICT
    assert tokens == {"input_tokens": 20, "output_tokens": 10}
    assert fake.calls == 2


def test_call_json_retries_transport_errors(monkeypatch):
    fake = FakeBedrock([TimeoutError("read timeout"), json.dumps(VERDICT)])
    _patch_client(monkeypatch, fake)
    parsed, _ = bedrock.call_json("sys", {}, max_tokens=64, key="correct")
    assert parsed == VERDICT


def test_call_json_gives_up_after_four_unreadable_replies(monkeypatch):
    fake = FakeBedrock(["nope"] * 4)
    _patch_client(monkeypatch, fake)
    with pytest.raises(RuntimeError, match="no JSON object with 'correct'"):
        bedrock.call_json("sys", {}, max_tokens=64, key="correct")
    assert fake.calls == 4


def _write_cell(run_dir: Path, case_id: str) -> Path:
    audit = {"method": "POST", "url": "https://api.example.com", "request": {}, "ok": True,
             "latency_ms": 5, "started_at": "t0", "ended_at": "t1"}
    audit_path = Path("audits") / f"{case_id}.json"
    (run_dir / audit_path).parent.mkdir(parents=True, exist_ok=True)
    (run_dir / audit_path).write_text(json.dumps(audit))
    path = run_dir / "cells" / case_id / "exa_instant.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"case_id": case_id, "question": "q", "endpoint": "exa_instant",
                                "surface": "web-search", "hits": [], "audit_path": str(audit_path)}))
    return path


def test_one_failed_judge_call_keeps_the_other_evaluations(tmp_path, monkeypatch):
    for case_id in ("a", "b", "c"):
        _write_cell(tmp_path, case_id)
    snapshots = []
    monkeypatch.setattr(orchestration, "build_snapshot", lambda run_dir: snapshots.append(run_dir))

    def flaky(case, _result):
        if case.id == "b":
            raise RuntimeError("Bedrock judge failed")
        return {"accuracy": {"correct": True}}

    monkeypatch.setattr(orchestration, "evaluate_search_result", flaky)
    with pytest.raises(RuntimeError, match="1 of 3 cell"):
        orchestration.evaluate_run(tmp_path, workers=2)
    saved = {p.parent.name: json.loads(p.read_text()).get("evaluation")
             for p in (tmp_path / "cells").glob("*/*.json")}
    assert saved == {"a": {"accuracy": {"correct": True}}, "b": None, "c": {"accuracy": {"correct": True}}}
    assert snapshots == []  # no snapshot from a partial evaluation

    retried = []

    def ok(case, _result):
        retried.append(case.id)
        return {"accuracy": {"correct": False}}

    monkeypatch.setattr(orchestration, "evaluate_search_result", ok)
    orchestration.evaluate_run(tmp_path, workers=2)
    assert retried == ["b"]  # rerun only evaluates what is missing
    assert snapshots == [tmp_path]
