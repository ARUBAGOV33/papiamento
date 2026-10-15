# _meta/

The rules about the data, rather than the data itself.

| File | What it is |
|---|---|
| [`conventions.md`](conventions.md) | File format, ids, status values, source and page rules, column meanings |
| [`invariants.md`](invariants.md) | Aruban rules that are not up for debate, each with its source |
| [`known-facts.tsv`](known-facts.tsv) | Maintainer and review-board rulings the validator enforces on every change |
| [`schema/`](schema/) | Table Schema for every TSV file, plus `registry.json` mapping files to schemas |
| [`allowlists/`](allowlists/) | Words exempt from a check (e.g. loanwords the AB list prints with accents) |

Changes here affect every file in the repo, so they need a code-owner approval. When a reviewer corrects a fact, add it to `known-facts.tsv` so the mistake can never come back.
