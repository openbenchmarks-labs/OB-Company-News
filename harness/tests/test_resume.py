import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, call

import pytest

from harness import orchestration
from harness.artifacts import read_json, write_json
from harness.cli import main
from harness.models import Case, SearchResult
from harness.verification import verify_run


@pytest.fixture
def benchmark(tmp_path, monkeypatch):
    dataset = tmp_path / "dataset.json"
    run_dir = tmp_path / "run"
    question = {
        "id": "funding-1",
        "question": "How much did Example Corp raise?",
        "expected_answer": "$25 million",
        "cells": [{"label": "amount", "value": "$25 million"}],
    }
    write_json(dataset, [question])
    tool = Mock()
    tool.name = "exa_instant"
    tool.search.return_value = SearchResult(
        endpoint=tool.name,
        surface="web-search",
        hits=[{"url": "https://example.com/news", "snippet": "$25 million"}],
        audit={
            "method": "GET",
            "url": "https://example.com/search",
            "request": {},
            "ok": True,
            "status_code": 200,
            "latency_ms": 1,
            "started_at": "start",
            "ended_at": "end",
        },
    )

    def grade(case, result):
        return {"accuracy": {"correct": case.expected_answer == result.hits[0].snippet}}

    judge = Mock(side_effect=grade)
    monkeypatch.setattr(orchestration, "load_dotenv", lambda *_: None)
    monkeypatch.setattr(orchestration, "selected_adapters", lambda _: [tool])
    monkeypatch.setattr(orchestration, "evaluate_search_result", judge)
    return dataset, run_dir, question, tool, judge


def _run(dataset, run_dir, *options):
    return main(["run", "--dataset", str(dataset), "--output", str(run_dir), *options])


def _files(run_dir):
    return {path.relative_to(run_dir): path.read_bytes() for path in run_dir.rglob("*") if path.is_file()}


def test_resume_rejects_edited_question_with_same_id(benchmark):
    dataset, run_dir, question, tool, judge = benchmark
    assert _run(dataset, run_dir) == 0
    original = _files(run_dir)
    edited = {
        **question,
        "question": "What was the confirmed raise for Example Corp?",
        "expected_answer": "$30 million",
        "cells": [{"label": "amount", "value": "$30 million"}],
    }
    write_json(dataset, [edited])

    with pytest.raises(ValueError, match=r"dataset SHA-256.*new --output"):
        _run(dataset, run_dir, "--resume")

    assert _files(run_dir) == original
    assert tool.mock_calls == [call.validate_credentials(), call.search(Case.from_record(question))]
    judge.assert_called_once()


def test_limited_ordinary_rerun_cannot_replace_plan_before_resume(benchmark):
    dataset, run_dir, first, tool, judge = benchmark
    second = {**first, "id": "funding-2"}
    write_json(dataset, [first, second])
    assert _run(dataset, run_dir) == 0
    original = _files(run_dir)
    corrected = {
        **second,
        "expected_answer": "$30 million",
        "cells": [{"label": "amount", "value": "$30 million"}],
    }
    write_json(dataset, [first, corrected])

    with pytest.raises(ValueError, match=r"dataset SHA-256.*new --output"):
        _run(dataset, run_dir, "--limit", "1")
    assert _files(run_dir) == original
    with pytest.raises(ValueError, match=r"dataset SHA-256.*new --output"):
        _run(dataset, run_dir, "--resume")
    assert _files(run_dir) == original
    tool.validate_credentials.assert_called_once()
    assert tool.search.call_count == judge.call_count == 2

    fresh = run_dir.with_name("fresh")
    fresh.mkdir()
    assert _run(dataset, fresh) == 0
    assert read_json(fresh / "cells/funding-2/exa_instant.json")["expected_answer"] == "$30 million"
    assert read_json(fresh / "run.json")["leaderboard"][0]["accuracy_pct"] == 50.0
    assert verify_run(fresh) == {"cases": 2, "endpoints": 1, "cells": 2, "files": 4}


@pytest.mark.parametrize("options", [(), ("--resume",)], ids=["rerun", "resume"])
@pytest.mark.parametrize(
    "metadata",
    [None, b"{", b"\xff", b"[]", b"{}", b'{"dataset_sha256": 7}'],
    ids=["missing-plan", "invalid-json", "invalid-encoding", "array", "missing-hash", "numeric-hash"],
)
def test_existing_run_rejects_invalid_plan(benchmark, options, metadata):
    dataset, run_dir, _, tool, judge = benchmark
    assert _run(dataset, run_dir) == 0
    plan_path = run_dir / "run-plan.json"
    if metadata is None:
        plan_path.unlink()
    else:
        plan_path.write_bytes(metadata)
    original = _files(run_dir)

    with pytest.raises(ValueError, match=r"run-plan\.json.*new --output"):
        _run(dataset, run_dir, *options)

    assert _files(run_dir) == original
    tool.validate_credentials.assert_called_once()
    tool.search.assert_called_once()
    judge.assert_called_once()


def test_ordinary_rerun_rejects_formatting_only_edit(benchmark):
    dataset, run_dir, question, tool, judge = benchmark
    assert _run(dataset, run_dir) == 0
    original = _files(run_dir)
    dataset.write_text(json.dumps([question], separators=(",", ":")))
    assert read_json(dataset) == [question]

    with pytest.raises(ValueError, match=r"dataset SHA-256.*new --output"):
        _run(dataset, run_dir)

    assert _files(run_dir) == original
    tool.validate_credentials.assert_called_once()
    tool.search.assert_called_once()
    judge.assert_called_once()


def test_run_hashes_and_parses_one_dataset_read(benchmark, monkeypatch):
    dataset, run_dir, question, tool, judge = benchmark
    original_hash = hashlib.sha256(dataset.read_bytes()).hexdigest()
    replacement = {**question, "expected_answer": "$30 million"}
    open_path = Path.open
    reads = 0

    @contextmanager
    def replace_after_read(path, *args, **kwargs):
        nonlocal reads
        with open_path(path, *args, **kwargs) as stream:
            yield stream
        if path == dataset:
            reads += 1
            if reads == 1:
                write_json(dataset, [replacement])

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", replace_after_read)
        assert _run(dataset, run_dir) == 0

    assert read_json(dataset) == [replacement]
    assert read_json(run_dir / "run-plan.json")["dataset_sha256"] == original_hash
    judge.assert_called_once_with(Case.from_record(question), tool.search.return_value)
    assert reads == 1


def test_resume_allows_relocated_dataset_more_questions_and_added_setup(benchmark, monkeypatch):
    dataset, run_dir, first, tool, judge = benchmark
    second = {**first, "id": "funding-2"}
    write_json(dataset, [first, second])
    assert _run(dataset, run_dir, "--limit", "1") == 0
    original = _files(run_dir)
    relocated = dataset.rename(dataset.with_name("relocated.json"))
    extra = Mock()
    extra.name = "exa_fast"
    extra.search.return_value = tool.search.return_value.model_copy(update={"endpoint": extra.name})
    tools = {tool.name: tool, extra.name: extra}
    monkeypatch.setattr(orchestration, "selected_adapters", lambda names: [tools[name] for name in names])

    endpoints = f"{tool.name},{extra.name}"
    assert _run(relocated, run_dir, "--limit", "2", "--resume", "--endpoints", endpoints) == 0

    plan = read_json(run_dir / "run-plan.json")
    assert plan["dataset"] == str(relocated.resolve())
    assert plan["endpoints"] == [tool.name, extra.name]
    assert plan["dataset_sha256"] == json.loads(original[Path("run-plan.json")])["dataset_sha256"]
    for path, content in original.items():
        if path.parts[0] in {"cells", "audit"}:
            assert (run_dir / path).read_bytes() == content
    expected_searches = [call(Case.from_record(row)) for row in (first, second)]
    assert tool.search.call_args_list == extra.search.call_args_list == expected_searches
    assert judge.call_count == 4
    assert verify_run(run_dir) == {"cases": 2, "endpoints": 2, "cells": 4, "files": 8}


def test_search_only_resume_and_deferred_evaluation(benchmark):
    dataset, run_dir, question, tool, judge = benchmark
    assert _run(dataset, run_dir, "--search-only") == 0
    cell_path = run_dir / "cells/funding-1/exa_instant.json"
    original_cell = cell_path.read_bytes()
    assert _run(dataset, run_dir, "--search-only", "--resume") == 0
    assert cell_path.read_bytes() == original_cell
    assert read_json(cell_path)["evaluation"] is None
    original = _files(run_dir)
    write_json(dataset, [{**question, "expected_answer": "$30 million"}])

    with pytest.raises(ValueError, match=r"dataset SHA-256.*new --output"):
        _run(dataset, run_dir, "--search-only", "--resume")

    assert _files(run_dir) == original
    assert tool.validate_credentials.call_count == 2
    judge.assert_not_called()
    dataset.unlink()
    assert main(["evaluate", "--run-dir", str(run_dir), "--workers", "1"]) == 0
    tool.search.assert_called_once_with(Case.from_record(question))
    judge.assert_called_once_with(Case.from_record(question), tool.search.return_value)
    assert read_json(cell_path)["evaluation"] == {"accuracy": {"correct": True}}
    assert verify_run(run_dir) == {"cases": 1, "endpoints": 1, "cells": 1, "files": 2}
