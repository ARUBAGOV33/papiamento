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

- Front matter: `id`, `title`, `status`, `source`, `page`, `severity` (`error`, `warning`, `suggestion` or `info`), and `reviewed_by` once reviewed. The validator checks every file.
- Body: the rule in one or two sentences, correct examples, incorrect examples with the correction next to each, and exceptions.
- Keep each file under 200 lines; split long topics.

## Rules

- Every rule cites the source PDF and printed page. Check the PDF itself, not an OCR copy. A rule that rests only on a maintainer ruling cites `RUL2026` and names the ruling in Notes.
- Papiamento examples are copied verbatim from the cited page. Never write new example sentences.
- The Departamento di Enseñansa books are republished with permission, so their wording and examples may be quoted with a citation.
- When sources disagree, add a row to [`sources/errata.tsv`](../sources/errata.tsv) and mark the rule `disputed`.

## Word-level rules live in `lexicon/`

Rules that swap one word for another (Spanish day and month names, `hay` → `tin`, Curaçao `kome` → `come`…) are rows in [`lexicon/barbarismos/`](../lexicon/barbarismos/) and [`lexicon/variants/`](../lexicon/variants/), with the same `RULE_LEX_*` ids, not files here.

## Old rule-pack ids that are not files here

The rules in this folder were rebuilt from the source PDFs out of an older rule pack (the one the Skirbi checker uses). These ids from that pack have no file, either because they were merged into another rule or because no page supports them:

| Id | Why |
|---|---|
| `RULE_ORT_MAL_001` | Merged into RULE_ORT_044 and RULE_ORT_045 (same section, AB 2018 §11.9). |
| `RULE_ORT_BON_001` | Merged into RULE_ORT_046 (§11.9). |
| `RULE_ORT_REDUP_001` | Merged into RULE_ORT_047 and RULE_ORT_048 (§11.10). |
| `RULE_ORT_BORROW_001` | Merged into RULE_ORT_052, RULE_ORT_053 and RULE_ORT_054 (§12.2). |
| `RULE_ORT_001` | Merged into RULE_ORT_ACCENT_001 (same statement). |
| `RULE_MOR_GERUND_PORNDO` | Merged into RULE_MOR_GERUND_PODIENDO: por has no gerund (err-0010). |
| `RULE_MOR_GERUND_PREFARANDO` | Merged into RULE_MOR_GERUND_PREFIRIENDO: prefera has no gerund (err-0011). |
| `RULE_MOR_GERUND_PREFERANDO` | Merged into RULE_MOR_GERUND_PREFIRIENDO: prefera has no gerund (err-0011). |
| `RULE_MOR_NOUN_PLURAL_004` | Merged into RULE_MOR_NOUN_PLURAL_003: the same statement (Morfologia §2.3.4.1, p. 11). |
| `RULE_PRE_NA_REFERENCE_002` | Merged into RULE_PRE_NA_OPINION_001: the same section (Preposicion y Interheccion §1.3.7, p. 17). |
| `RULE_STY_ASYM_003` | Merged into RULE_STY_ASYM_002 (Stilistica §2 point 10, enumerations). |
| `RULE_STY_ASYM_004` | Merged into RULE_STY_ASYM_001 (Stilistica §2 point 10, keeping the same person). |
| `RULE_STY_CONC_001` | Merged into RULE_STI_CONC_001 (Stilistica §2 point 11). |
| `RULE_STY_CONC_002` | Not supported: Stilistica requires singular reference only for nouns such as club, gobierno and comision, which RULE_STI_CONC_001 covers. |
| `RULE_STY_GER_001` | Merged into RULE_STI_GER_001 (Stilistica §2 point 9). |
| `RULE_STY_GER_002` | Not stated: the mientras rewrite is one of two corrections of a single example, recorded in RULE_STI_GER_001. |
| `RULE_STY_GER_003` | Not stated in Stilistica. |
| `RULE_STY_PLEO_002` | Merged into RULE_STY_PLEO_001 (Stilistica §2 point 3). |
| `RULE_STY_PLEO_003` | Not stated: Stilistica never advises shortening a pleonasm. |
| `RULE_STY_REP_003` | Merged into RULE_STY_REP_001 (Stilistica §2 point 1). |
| `RULE_STY_REP_004` | Not stated: Stilistica gives no rule on chains of function words or a count of three. |
| `RULE_STY_SCORE_001` | A scoring design for the old checker, not a language rule; no source. |
| `RULE_STY_SEQ_001` | Merged into RULE_STI_ORDER_001 (Stilistica §2 point 6). |
| `RULE_STY_SEQ_002` | Not supported beyond the tur + no example, which RULE_STI_ORDER_001 covers. |
| `RULE_STY_TAUT_001` | Not supported: Stilistica presents tautology as a device for emphasis, not an error (see RULE_STY_TAUT_002). |
| `RULE_STY_TRANS_001` | Not stated: Stilistica gives no transparency score or length limit. |
| `RULE_STY_TRANS_002` | Not stated: Stilistica draws no rule about the distance between subject and verb. |
| `RULE_STY_TRANS_003` | Merged into RULE_STI_TRANSP_001 (split long sentences). |
| `RULE_STY_TRANS_004` | A scoring design for the old checker, not a language rule; no source. |
| `RULE_SYN_SUB_002` | Not supported: Sintaxis §4.3 (pp. 86-87) gives both forms, with and without pa or cu, as correct. |
