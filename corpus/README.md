# corpus/

Aruban Papiamento text that we are allowed to redistribute, for research and model training.

**Status:** empty. The first additions will be proofread digital editions of the Departamento di Enseñansa books (board card P1-17).

## Parallel sentences (`parallel/`)

`parallel/prompts.tsv` holds short everyday English and Spanish sentences; `parallel/pairs.tsv` holds their translations into Aruban Papiamento, written by teachers, several per prompt. Both are tables with schemas (`_meta/schema/parallel-*.schema.json`), not text files, so they are not listed in `manifest.tsv`. They are CC0 1.0 (LICENSE-DATA). 15% of the prompts and all their translations are held out in [`eval/parallel/`](../eval/parallel/). See `_meta/conventions.md`, Parallel sentences.

**Status:** set up, empty. The first prompts and the contribution tool (`tools/contribute/`) come next.

## Rules

- Only text with a shareable licence: public domain, explicit permission, or an open licence. Record which in `manifest.tsv`.
- Every file has a row in `manifest.tsv`: file, source id, pages covered, licence tier, variant, status, notes.
- Aruban spelling only. Curaçao text may be added only in a separate, clearly labelled `pap-CW/` folder.
- No newspaper articles, theses or private books unless the rights holder agrees in writing.
- Text extracted by OCR is `draft` until someone proofreads it against the PDF.
