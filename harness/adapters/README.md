# adapters

One file per tool. Each file builds the tool's request and turns its response into search hits. Setups and prices live in `tools/<tool>.yaml`.

Web search tools take the question as written:

- `brave.py` — Brave web search and Brave LLM context.
- `context.py` — Context Developer search, with highlights (`context`) or without (`context_nohl`).
- `exa.py` — Exa search with highlights.
- `firecrawl.py` — Firecrawl search, and Firecrawl Agent with the Apollo toolkit (`firecrawl_agent_apollo`): starts a job, polls it, and returns the answer as one hit.
- `keenable.py` — Keenable search.
- `linkup.py` — Linkup search results.
- `nimble.py` — Nimble search.
- `parallel.py` — Parallel search. The extract model writes one objective and 2-3 keyword queries per question, shared across modes.
- `perplexity.py` — Perplexity search.
- `serp.py` — Google results through a RapidAPI search service.
- `specstream.py`: SpecStream web search, with one best passage per result (`specstream`), up to four passages per result (`specstream_passages`), or the fast tier (`specstream_fast`).
- `tavily.py` — Tavily search.
- `tinyfish.py` — TinyFish search.
- `seltz.py` — Seltz search, web scope: full content (`seltz_web`) or the highest-scoring passages (`seltz_web_snippets`).
- `you.py` — You.com search with highlights.

The baseline needs no tool:

- `model_only.py` — Makes no call; the extract model answers from its own knowledge.

Each file ends with `setup(name, ...)`. Its arguments are the `settings` from the tool's yaml file.
