# grammar/

Aruban Papiamento grammar and spelling rules in plain language, one small Markdown file per rule. These files explain the rules to people. The machine-readable versions the checker runs are in [`rules/`](../rules/).

## Topic folders

| Folder | Main source |
|---|---|
| `orthography/` | AB 2018 no. 68; Ortografia 2009 |
| `morphology/` | Morfologia 2010 |
| `syntax/` | Sintaxis 2015 |
| `prepositions/` | Preposicion y Interheccion 2016 |
| `style/` | Stilistica 2008 |

## File format

Start from [`_templates/rule.md`](../_templates/rule.md). File name: the rule id in lowercase kebab-case, e.g. `rule-ort-accent-001.md`.

- Front matter: `id`, `title`, `status`, `source`, `page`, `severity`, and `reviewed_by` once reviewed.
- Body: the rule in one or two sentences, correct examples, incorrect examples with the correction next to each, and exceptions.
- Keep each file under 200 lines; split long topics.

## Rules

- Every rule cites the source PDF and printed page. Check the PDF itself, not an OCR copy.
- The Departamento di Enseñansa books are republished with permission, so their wording and examples may be quoted with a citation.
- When sources disagree, add a row to [`sources/errata.tsv`](../sources/errata.tsv) and mark the rule `disputed`.
