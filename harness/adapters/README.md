# adapters

One file per tool. Each file builds the tool's request and turns its response into search hits. Setups and prices live in `tools/<tool>.yaml`.

Web search tools take the question as written:

- `brave.py` — Brave web search and Brave LLM context.
- `context.py` — Context Developer search with highlights.
- `exa.py` — Exa search with highlights.
- `firecrawl.py` — Firecrawl search.
- `linkup.py` — Linkup search results.
- `nimble.py` — Nimble search.
- `parallel.py` — Parallel search.
- `perplexity.py` — Perplexity search.
- `serp.py` — Google results through a RapidAPI search service.
- `string.py` — String web access search, using Google results.
- `tavily.py` — Tavily search.
- `tinyfish.py` — TinyFish search.
- `you.py` — You.com search with highlights.

News indexes look up a company's events:

- `autobound.py` — Autobound news signals for a company domain.
- `datahyena.py` — Datahyena company timeline.
- `predictleads.py` — PredictLeads news events. A model first picks which event types to ask for.
- `seltz.py` — Seltz news search.

Each file ends with `setup(name, ...)`. Its arguments are the `settings` from the tool's yaml file.
