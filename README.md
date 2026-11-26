# OB-Company-News

Open, independent benchmark of APIs for company news: web search APIs and dedicated news indexes, measured on how accurately they surface recent, verified company news for AI agents, such as executive hires, acquisitions, product launches and funding. Every tool answers the same questions with one query, no query rewrite and no page fetch, graded by the same judge. Tools measured: Brave, Context, Exa, Firecrawl, Hydrafetch, Linkup, Nimble, Parallel, Perplexity, SERP, Tavily, TinyFish, You.com, Autobound, DataHyena, PredictLeads and Seltz.

**Live leaderboard:** [openbenchmarks.com/company-news](https://openbenchmarks.com/company-news) · **Public dataset:** [`openbenchmarks/OB-News-Websearch`](https://huggingface.co/datasets/openbenchmarks/OB-News-Websearch)

Published and maintained by **[OpenBenchmarks Labs](https://openbenchmarks.com)**.

## Methodology

General web search APIs and dedicated company-news indexes are evaluated on factual company-news questions (such as executive hires, acquisitions, product launches, and funding announcements).

- **Fixed protocol:** One query per question, no query rewriting, and no secondary page fetch.
- **Scoring:** `judge/extraction.py` extracts an answer from the returned snippets alone, and `judge/judging.py` grades the extracted answer against ground-truth facts (`cells`) and checks snippet provenance.
- **Headline metrics:** Extracted-answer accuracy, cost per 1,000 correct answers, latency, and token efficiency.

## Tools evaluated

17 tools configured in [`tools/`](tools/README.md):

- **Web search APIs:** `brave`, `context`, `exa`, `firecrawl`, `hydrafetch`, `linkup`, `nimble`, `parallel`, `perplexity`, `serp`, `tavily`, `tinyfish`, `you`
- **News indexes:** `autobound`, `datahyena`, `predictleads`, `seltz`

## Dataset

No question files are committed to this repository.

- **Public split:** Published on Hugging Face at [`openbenchmarks/OB-News-Websearch`](https://huggingface.co/datasets/openbenchmarks/OB-News-Websearch).
- **Held-out split:** The private evaluation set used for the published leaderboard stays private so tools cannot train on it. Pass your dataset file with `--dataset`.

See [`data/README.md`](data/README.md) for the complete JSON schema.

## Repository structure

- [`data/`](data/README.md): Question file schema and dataset instructions (no question files committed).
- [`harness/`](harness/README.md): Benchmark CLI (`list-providers`, `run`, `evaluate`, `build-snapshot`, `verify`), orchestration, and tool adapters.
- [`tools/`](tools/README.md): One `<tool>.yaml` config per search API or news index, with setups and pricing (17 tools).
- [`judge/`](judge/README.md): Answer extraction, ground-truth grading, and board aggregation.
- [`benchmark.yaml`](benchmark.yaml): Benchmark contract, scope, and refresh cadence.
- [`AGENTS.md`](AGENTS.md): Entry guide for coding agents.

## Quick start

Run the offline test suite (no API keys required):

```sh
uv venv && uv pip install -e ".[dev]"
.venv/bin/pytest
```

To run against live APIs, copy `.env.example` to `.env`, add your keys, and inspect the CLI:

```sh
cp .env.example .env
.venv/bin/python -m harness --help
```

## Adding or updating a tool

1. Add or edit `tools/<tool>.yaml` (and add `harness/adapters/<tool>.py` plus one line in `harness/registry.py` if adding a new tool).
2. Run `.venv/bin/pytest`.
3. Open a pull request.

## Links

- [Live leaderboard](https://openbenchmarks.com/company-news)
- [Best company news API](https://openbenchmarks.com/company-news/best-company-news-api)
- [Hugging Face dataset](https://huggingface.co/datasets/openbenchmarks/OB-News-Websearch)
- [`llms.txt`](https://openbenchmarks.com/llms.txt)

## Related benchmarks

- [OB-Code-Websearch](https://github.com/openbenchmarks-labs/OB-Code-Websearch): Web search APIs for coding agents ([leaderboard](https://openbenchmarks.com/web-search-for-coding-agents))
- [OB-Company-Search-Multi-Turn](https://github.com/openbenchmarks-labs/OB-Company-Search-Multi-Turn): Multi-hop company research agents ([leaderboard](https://openbenchmarks.com/multi-turn-company-search))
- [OB-Company-Funding](https://github.com/openbenchmarks-labs/OB-Company-Funding): Latest funding round accuracy and freshness ([leaderboard](https://openbenchmarks.com/company-funding))
- [All OpenBenchmarks leaderboards](https://openbenchmarks.com)

## License

MIT. See [LICENSE](LICENSE).
