# sources/

Every document this dataset is built from. The source PDFs are the source of truth: every data row cites a source id from [`sources.tsv`](sources.tsv) and a printed page. OCR text, scraped data and older JSON files are working copies only; when they disagree with the PDF, the PDF wins.

## What lives here

| Path | What |
|---|---|
| `sources.tsv` | The registry: one row per source. Schema: [`_meta/schema/sources.schema.json`](../_meta/schema/sources.schema.json) |
| `cards/<ID>.md` | One card per source: full citation, licence and why, page offset, what we use it for, known issues |
| `pdf/<ID>.pdf` | The PDF itself, only for sources we may redistribute |
| `pdf/SHA256SUMS` | SHA-256 of every PDF in `pdf/` (`shasum -a 256` format, sorted by file name) |
| `errata.tsv` | Typos and conflicts found in the sources. Schema: [`_meta/schema/errata.schema.json`](../_meta/schema/errata.schema.json) |
| `permissions/` | Written permissions from rights holders, and their status |

## Licence tiers

| Tier | Meaning | PDF in this repo? |
|---|---|---|
| `public-domain` | No copyright: laws (Auteursverordening art. 11) and government publications without a rights notice | Yes, if it is a language reference |
| `permission` | The rights holder allowed us to republish it; `permission_ref` says who, when and where the record is filed | Yes |
| `open-licence` | Published under an open licence (e.g. CC BY-SA); reuse follows that licence | Allowed, but we cite rather than copy |
| `restricted` | Anything else: newspapers, theses, literature, web pages | No. Cite it only |

The validator (`tools/validate.py`) refuses any PDF in `pdf/` that is not referenced by exactly one row with a shareable tier (`public-domain`, `permission` or `open-licence`), and any `permission` row without a `permission_ref`.

## Page numbers

Rows cite the page **as printed**. `page_offset` is PDF page minus printed page, so PDF page = printed page + `page_offset`. Each card says on which pages the offset was measured. It is empty when the pages are unnumbered or the offset is not constant.

## How to add a source

1. Pick an id: 2–5 capital letters and the 4-digit year, optionally a lowercase letter (`MOR2010`, `AB2018`, `BDA2024b`). Ids are never reused.
2. Write the card: copy [`_templates/source-card.md`](../_templates/source-card.md) to `cards/<ID>.md`. Take every fact from the PDF itself (title page, colophon); leave a field empty rather than guess.
3. Add the row to `sources.tsv`, keeping the rows sorted by id.
4. Only if the tier is shareable and it is a language reference: copy the PDF to `pdf/<ID>.pdf` without changing its bytes, fill the `pdf` column, measure `page_offset` on two or three numbered pages, and regenerate `pdf/SHA256SUMS` (`cd sources/pdf && shasum -a 256 *.pdf | sort -k2 > SHA256SUMS`).
5. For a `permission` source, file the written permission in `permissions/`.
6. Run `python3 tools/validate.py`.

## Errata

When a source has an obvious typo, or two sources disagree, do not pick a winner silently: add a row to `errata.tsv` (copy [`_templates/errata-row.tsv`](../_templates/errata-row.tsv)) and mention it on the card. The review board sets `status` to `reviewed`.
