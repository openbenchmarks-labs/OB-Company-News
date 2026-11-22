# harness

Runs the benchmark and calls each tool. No grading code lives here.

- `cli.py` — Command-line runner (`list-providers`, `run`, `evaluate`, `build-snapshot`, `verify`).
- `__main__.py` — Lets you start the runner with `python -m harness`.
- `orchestration.py` — Sends every question to every setup, saves each result, then builds the run summary.
- `registry.py` — Reads `tools/<tool>.yaml`, builds each setup, and sets the default run order.
- `tool_base.py` — Shared base for tools: the common request flow, result cleanup, and the skip record for news indexes.
- `adapters/` — The request and response code for each tool, one file per tool.
- `http_client.py` — Sends HTTP requests with retries and keeps a record of each one with API keys hidden.
- `openai_client.py` — Asks an OpenAI model for a structured answer. Used by the judge and by PredictLeads to pick event types.
- `models.py` — The shapes of questions, search hits, request records, and judge verdicts.
- `artifacts.py` — Reads the question file and writes JSON files safely.
- `verification.py` — Checks a finished run: file hashes, result counts, and that no API key was saved.
- `tests/` — Tests for the runner, the request records, and the tool adapters.

## What a run writes

```text
<run-dir>/
├── run-plan.json
├── run.json
├── manifest.json
├── cells/<question-id>/<setup>.json
└── audit/<question-id>/<setup>.json
```

- `run-plan.json` — The question file and its hash, the setups, the number of questions, and the start time.
- `cells/` — One result per question and setup: the hits, the extracted answer, and the judge's verdicts.
- `audit/` — The full HTTP request and response behind each result.
- `run.json` — The run plan, every result, and the board.
- `manifest.json` — A hash of every file, so anyone can check nothing changed.

API keys and similar headers are replaced with `***REDACTED***` before anything is saved. Response bodies are kept so the scoring can be checked. Read each tool's terms and the output before you publish a run.

## Reusing a run directory

Every `run`, with or without `--resume`, checks the dataset's SHA-256 against
`run-plan.json` before updating a nonempty output directory or calling a tool or
judge. Use a fresh `--output` directory if the dataset bytes changed, including
formatting-only edits, or if the saved plan or hash is missing or invalid.

You can move a byte-identical dataset to another path, increase `--limit`, or
add setups and still reuse completed cells with `--resume`. Deferred
`evaluate` reads the saved search-only cells and can run without the dataset file.

Each output directory supports one writer at a time. Run `run`, `evaluate`,
and `build-snapshot` sequentially when they target the same directory. Use
separate output directories for concurrent runs.
