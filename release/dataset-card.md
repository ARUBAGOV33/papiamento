---
license: cc-by-4.0
language:
- pap
- en
- nl
- es
multilinguality:
- multilingual
pretty_name: "Papiamento: open data for Aruban Papiamento"
size_categories:
- 10K<n<100K
source_datasets:
- original
annotations_creators:
- expert-generated
- machine-generated
language_creators:
- expert-generated
task_categories:
- translation
tags:
- papiamento
- aruba
- pap-AW
- orthography
- spelling
- grammar
- lexicon
- low-resource
configs:
- config_name: words
  data_files: words.jsonl
  default: true
- config_name: numbers
  data_files: numbers.jsonl
- config_name: calendar
  data_files: calendar.jsonl
- config_name: barbarismos
  data_files: barbarismos.jsonl
- config_name: variants
  data_files: variants.jsonl
- config_name: loanwords
  data_files: loanwords.jsonl
- config_name: grammar
  data_files: grammar.jsonl
- config_name: rules
  data_files: rules.jsonl
- config_name: errata
  data_files: errata.jsonl
- config_name: sources
  data_files: sources.jsonl
- config_name: known_facts
  data_files: known_facts.jsonl
---

# Papiamento: open data for Aruban Papiamento

Version {{VERSION}}. Built from the GitHub repository [ARUBAGOV33/papiamento](https://github.com/ARUBAGOV33/papiamento), where the data is kept, reviewed and corrected. Report mistakes there, not here.

An open, citable reference dataset for **Aruban Papiamento** (`pap-AW`): the language as it is written in Aruba, in the etymological spelling of the AB 2018 no. 68 law and its official word list.

Papiamento is written in two standards. Aruba uses an etymological spelling (`cas`, `educacion`); Curaçao and Bonaire use a phonological one (`kas`, `edukashon`). Both share the language code `pap`, and most Papiamento text online is in the Curaçao standard. In this dataset, every Papiamento column holds Aruban spelling only. Curaçao forms appear in one place, the `variants` table, mapped to the Aruban form.

## Read this first

- **Rows start as drafts.** A row becomes `reviewed` only when a member of the review board of Aruban teachers and linguists has checked it against the source page. The board is being recruited. Filter on `status == "reviewed"` when you need verified data. {{REVIEW_STATE}}
- **Most translations are machine drafts.** {{WORDS_TRANSLATED}} of the {{WORDS}} words have English, Dutch or Spanish translations. In {{WORDS_MACHINE}} of them a model drafted the translations and a second model checked them cell by cell, with no dictionaries or websites; these rows carry `machine` in `translated_by`. Leave them out if you need human translations only.
- **Every row cites a source and printed page.** The source PDFs are the source of truth. Where two sources disagree, or a source has a typo, the case is in the `errata` table with the maintainer's decision.
- **Keep Aruban and Curaçao data apart** in anything you build, and label it.

## Tables

Each table is a configuration with one `train` split.

| Configuration | Rows |
|---|---:|
{{COUNTS_TABLE}}

| Configuration | What it holds |
|---|---|
| `words` | Every headword of the AB 2018 word list: `lemma`, alternative forms (`alt`), the law's own labels (`tag`), part of speech, `en`/`nl`/`es` translations, and the printed page. `letter` is the letter folder in the repository. |
| `numbers` | Cardinals, ordinals, fractions, multiples, clock times and worked examples. `file` names the source file (`cardinals`, `ordinals`...). |
| `calendar` | Days of the week and months, lowercase as the law requires. |
| `barbarismos` | Forms to avoid (`wrong`) with the Aruban form to use (`right`), the language they come from and the reason. |
| `variants` | Curaçao spellings (`curacao`) mapped to Aruban spellings (`aruba`). Each Curaçao form is printed in a Curaçao-spelled source; each Aruban form is an AB 2018 headword. |
| `loanwords` | Loanwords from AB 2018 §12, their language of origin, the original spelling and the accepted Aruban form. |
| `grammar` | {{GRAMMAR}} spelling and grammar rules restated from the source books, with correct and incorrect examples quoted verbatim from the page. |
| `rules` | {{RULES}} machine-readable checker rules (regular expressions that work in both Python and JavaScript), each with tests taken from its grammar rule, plus the rule's severity, source and page. |
| `errata` | Where sources disagree or contain a typo, and what was decided. |
| `sources` | The source documents: title, authors, year, licence and the offset between printed and PDF pages. |
| `known_facts` | Maintainer rulings that the repository checks automatically on every change, for example that `hopi` means "a lot". |

Columns that can hold several values (`alt`, `en`, `nl`, `es`, `translated_by`, `reviewed_by`, `right`, `authors`) are lists. All other values are strings; an empty string means "not known yet".

Each row's `status` is one of:

| Status | Meaning |
|---|---|
| `draft` | Entered by a person or a machine; not yet checked by the review board. |
| `reviewed` | A review-board member checked it against the source page. `reviewed_by` names them. |
| `disputed` | Sources conflict or reviewers disagree. See `notes` and the `errata` table. |
| `deprecated` | Kept for history; no longer valid. |

## Other files

| File | Content |
|---|---|
| `rule_pack.json` | Everything a writing checker needs in one file: the machine rules, the barbarismos and the Curaçao-to-Aruba pairs. |
| `manifest.json` | Row counts per table and status, and the SHA-256 of every file. |
| `RELEASE_NOTES.md` | Rows per table and status for this version. |

## How to use it

```python
from datasets import load_dataset

words = load_dataset("{{HF_REPO}}", "words", split="train")
human_translated = words.filter(lambda r: r["en"] and "machine" not in r["translated_by"])
```

Without the `datasets` library, every file is plain JSON Lines: one JSON object per line.

## Sources

- **AB 2018 no. 68**: the law published in Aruba's official gazette in 2018, with its spelling rules and official word list. Public domain.
- Books by the **Departamento di Enseñansa** of Aruba: Ortografia (2009), Vocabulario (2009), Morfologia (2010), Sintaxis (2015), and Preposicion y Interheccion (2016). Republished with permission from the Departamento di Enseñansa, granted through the Minister of Education and Innovation.
- Other books, such as Stilistica di Papiamento (2008), are cited, not republished.
- Maintainer rulings (source id `RUL2026`) where no printed page settles a question.

The full list, with licences, is in the `sources` table. Nothing is copied from copyrighted dictionaries, websites or newspapers.

## How it was made

Parts of this dataset were made with the help of AI models (Claude, by Anthropic): rebuilding the word list from the AB 2018 PDF, drafting the translations, and restating the grammar rules and writing the machine rules. Each piece was checked by a separate run against the page images, or cell by cell for translations, and the maintainer decided every conflict between sources. Machine-made content stays `draft` until the review board checks it against the source page. AI models are not listed as authors.

## Licence

The data is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Text quoted from a source, such as the grammar examples, keeps that source's terms, recorded in the `sources` table.

Attribution: "Papiamento Open Data contributors, https://github.com/ARUBAGOV33/papiamento, CC BY 4.0".

## Citation

Each version is archived on Zenodo with its own DOI, listed in the repository's README and `CITATION.cff`; https://doi.org/10.5281/zenodo.23427108 always points to the latest version. Cite the DOI of the version you used. If you rely on a specific word or rule, also cite the source and page given in that row.

```bibtex
@dataset{papiamento_open_data,
  author  = {{Papiamento Open Data contributors}},
  title   = {Papiamento: open data for Aruban Papiamento},
  version = {{{VERSION}}},
  doi     = {10.5281/zenodo.23427108},
  url     = {https://github.com/ARUBAGOV33/papiamento}
}
```

## Acknowledgements

Supported by Vadria Innovation Labs. With thanks to the Departamento di Enseñansa and the Ministry of Education and Innovation of Aruba for permission to republish the Departamento di Enseñansa books, and to the authors and editors of the source books and the AB 2018 word list.

## Contributing

Teachers, linguists and other speakers can fix a translation, report a wrong word or propose a rule through simple forms on GitHub, with no code. See the repository's [contributing guide](https://github.com/ARUBAGOV33/papiamento/blob/main/CONTRIBUTING.md).
