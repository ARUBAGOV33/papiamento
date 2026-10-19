# release/

Files used to build a release. Nothing here is data; the data lives in `lexicon/`, `grammar/`, `rules/`, `corpus/`, `eval/` and `sources/`.

| File | What it is |
|---|---|
| `dataset-card.md` | Template of the Hugging Face dataset card. `tools/build_dist.py` fills in the `{{PLACEHOLDERS}}` (version, counts, repository id) and writes the result to `dist/README.md`. |

How a release is made is in [RELEASING.md](../RELEASING.md). To change what the dataset card says, edit `dataset-card.md` here and run `python3 tools/build_dist.py --check`: the build fails if a placeholder is left unfilled.
