# data

No question files are committed to this folder.

## Public vs. held-out evaluation sets

- **Public split:** Published on Hugging Face at [`openbenchmarks/OB-Company-News`](https://huggingface.co/datasets/openbenchmarks/OB-Company-News).
- **Held-out split (private):** The evaluation set used for the published leaderboard stays private so tools cannot train on it. Pass your own dataset file with `python -m harness run --dataset <path>`.

## Files and schema

A JSON array, or a JSON object with the array under `cases`, `samples`, or `items`.

Required fields per question:

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique question identifier. |
| `question` | string | Exact question sent to web search tools. |

Ground-truth fields used by `judge/`:

| Field | Type | Description |
|---|---|---|
| `expected_answer` | string | Expected answer in plain text. |
| `cells` | array | Required facts that must all appear for an answer to count as correct. |
| `ground_truth_url` | string | Source URL containing the verified answer. |

Additional fields used by news indexes that query by company rather than free-text question:

| Field | Type | Description |
|---|---|---|
| `company_domain` | string | Target company domain. |
| `pattern` | string | Event category (for example, `hires` or `acquires`). |

Legacy field names (`ground_truth`, `recipe`, `gold.cells`, `gold.domain`, `gold.primary_url`) are also accepted.
