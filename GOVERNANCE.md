# Governance

How this project is run: who decides, how changes are approved, how disagreements are settled, and how releases are made.

## Roles

### Maintainers

Current maintainers: [@ARUBAGOV33](https://github.com/ARUBAGOV33) and [@victorgomesrt-rgb](https://github.com/victorgomesrt-rgb).

Maintainers:

- manage the repository, its settings and its automation;
- review and merge pull requests;
- keep `sources/sources.tsv`, the source PDFs and the permission records in order;
- make releases;
- enforce the [Code of Conduct](CODE_OF_CONDUCT.md).

### Review board

The review board checks language content. It is being recruited and will have at least two members: Aruban teachers or linguists.

Board members:

- check rows against the source page and set them to `reviewed`, adding their GitHub username to `reviewed_by`;
- approve changes to language content;
- decide errata and disputes;
- keep `_meta/invariants.md` and `_meta/known-facts.tsv` up to date.

**Until the board has at least two members, the maintainers do its work.**

### Contributors

Anyone who opens an issue, fills in a form, reviews a pull request or sends a change. Contributors can do everything except set a row to `reviewed`. See [CONTRIBUTING.md](CONTRIBUTING.md).

Contributors do not need a GitHub account: the contribution tool (`tools/contribute/`) lets teachers and linguists check and add translations and write sentences, and a maintainer brings their work in by pull request. Everyone the data credits is listed in [`_meta/contributors.tsv`](_meta/contributors.tsv), by name or by handle, with no contact details. Review-board members and maintainers need a GitHub account, because they approve pull requests there.

## Source precedence

1. **The source PDFs decide.** These are the AB 2018 no. 68 law and its word list, the Departamento di Enseñansa books (Ortografia 2009, Vocabulario 2009, Morfologia 2010, Sintaxis 2015, Preposicion y Interheccion 2016) and the other sources in `sources/sources.tsv`. Every row cites a source and the printed page.
2. **Working copies never decide.** OCR text, scraped data and older data files are working copies. When one disagrees with the PDF, the PDF wins and the working copy is corrected.
3. **Conflicts and typos go to errata.** When two PDFs disagree, or a PDF contains a typo, nobody picks a winner silently. The case goes into `sources/errata.tsv` and the review board decides.
4. **Rulings are recorded.** Decisions by the board (or, for now, the maintainers) are written down in `_meta/invariants.md`, and in `_meta/known-facts.tsv` when the validator can check them, with who decided and when. A ruling can be reopened by a pull request that cites a source page.

### Errata process

1. Anyone adds a row to `sources/errata.tsv`: the source, the printed page, the section, what the source prints (verbatim), what it should say, and why. Status `draft`.
2. Data rows affected by the case are set to `disputed`, with the errata id in `notes`.
3. The board decides in the pull request and records its decision there (see [Disputes](#disputes)).
4. The errata row is set to `reviewed`, with the deciding members in `reviewed_by`. The affected data rows are corrected. If the decision can be checked automatically, it is added to `_meta/known-facts.tsv`.

Example: AB 2018 §11.8, p. 38, gives the example "23 > bintiseis". But bintiseis is 26; 23 is bintitres. This is recorded as an erratum, and a known fact makes sure the dataset says bintitres for 23.

### Sources and permissions

- A PDF may be added to `sources/pdf/` only if its licence tier in `sources/sources.tsv` is `public-domain`, `permission` or `open-licence`. Permission records are kept in `sources/permissions/`.
- Sources with the tier `restricted` can be cited by page, but their files and text are not added to the repository.
- Adding or changing a source needs a maintainer's approval.

## How a change is approved

Every pull request must pass the gauntlet (`python3 tools/validate.py`, run by GitHub Actions).

| Change | Approval needed now | Once the board has 2 or more members |
|---|---|---|
| Language content: `lexicon/`, `grammar/`, `rules/`, `eval/`, `_meta/known-facts.tsv`, `_meta/invariants.md`, and errata decisions in `sources/errata.tsv` | 1 approving review from a code owner | 2 approving reviews from board members |
| Everything else: code, tests, workflows, documentation, other files in `sources/` and `_meta/` | 1 approving review from a code owner | 1 approving review from a code owner |

Also:

- Nobody approves their own pull request.
- A row may be set to `reviewed` only by a review-board member, who adds their GitHub username to `reviewed_by`. The person named in `reviewed_by` must be the author of the pull request or one of its approvers.
- A board member can review many rows in one pull request, but must have checked each row against its source page.
- Code owners are listed in [`.github/CODEOWNERS`](.github/CODEOWNERS). Branch protection on `main` requires a code-owner review. The maintainers check the other conditions before merging.

## Disputes

When reviewers disagree about language content, or sources conflict:

1. The affected rows are set to `disputed`, with an explanation in `notes`.
2. If sources are involved, a row is added to `sources/errata.tsv` and its id is put in `notes`.
3. The discussion happens in the pull request (or in an issue linked from it). Arguments cite sources and pages.
4. The board decides. A board member records the decision in the pull request: what was decided, by whom, and on which source pages. The rows are then updated.
5. If the board cannot agree, the rows stay `disputed` and both positions are kept in `notes`. Disputed rows are not part of the `reviewed` data.

Disputes about code, tooling or process are decided by the maintainers. Conduct problems follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Joining and leaving the review board

**Who can join.** Aruban teachers of Papiamento, linguists, and others with recognised expertise in Aruban Papiamento and its official spelling, who are willing to check rows against source pages.

**How to join.**

1. Anyone can nominate someone, including themselves, by opening an issue titled "Review board nomination: @username" with a short description of the person's background.
2. The maintainers and current board members discuss it in the issue. The nominee joins if no maintainer or board member objects within 14 days.
3. A pull request adds them to [Current members](#current-members) and to `.github/CODEOWNERS`, and they get write access to the repository.

**How to leave.**

- Members can step down at any time by opening an issue or a pull request.
- Members who have not taken part for 12 months are asked if they want to stay. Without a reply within 30 days, they step down.
- Maintainers can remove a member who breaks the Code of Conduct.

Rows that a former member reviewed stay `reviewed`, with their name in `reviewed_by`.

## Machine-made content

- Content made by software is always `draft`. This covers OCR, scraping, scripts, and AI models, including AI translation.
- Nothing becomes `reviewed` automatically. A person on the board must check each row against its source page.
- Machine-made content must not reproduce copyrighted sources such as dictionaries, websites, Glosbe or newspapers.
- A pull request with machine-made content says which tool or model made it and from what input.
- Machine-drafted translations carry `translated_by = machine`. A person who corrects one replaces it with their username; a review-board member who only confirms it leaves it as `machine` and fills `reviewed_by`.
- AI agents working in this repository follow `CLAUDE.md` or `AGENTS.md` and the same rules as everyone else.
- Known facts in `_meta/known-facts.tsv` guard against known machine mistakes. For example, a machine source gave "Hopi" (the people) for `hopi`, which means "a lot", and "basketball team" for `cinco`, which means "five".

## Variant policy

- Canonical columns hold **Aruban Papiamento** (`pap-AW`) only.
- **Curaçao forms** (`pap-CW`) appear only in `lexicon/variants/curacao-aruba.tsv`, mapped to the Aruban form.
- Papiamentu, as written in Curaçao and Bonaire, is a different standard. It is correct in its own place. This repository documents the Aruban standard.
- The validator warns about Curaçao spelling patterns in Aruban columns, except for words that are in the AB 2018 list.

## Releases

Releases use [semantic versioning](https://semver.org/) tags: `vMAJOR.MINOR.PATCH`.

| Part | When it changes |
|---|---|
| MAJOR | A change that can break users: a column renamed or removed, a file moved, a format changed. |
| MINOR | New tables, new columns, many new rows (for example a letter imported), new rules. |
| PATCH | Corrections, new translations, and rows reviewed. |

Before version 1.0.0, the structure may still change in a MINOR release. Ids never change in any release.

Release steps (details in [RELEASING.md](RELEASING.md)):

1. A maintainer opens a release pull request. It moves the "Unreleased" entries in `CHANGELOG.md` under the new version, and sets `version` and `date-released` in `CITATION.cff`.
2. The gauntlet passes and the pull request is approved and merged.
3. The maintainer tags `main` with `vX.Y.Z` and publishes a GitHub release. The release notes give the number of rows per status.
4. The release workflow builds JSONL files from the TSV files (into `dist/`, which is never committed), attaches them to the release and publishes them to Hugging Face under the same version number.
5. Zenodo archives the GitHub release and gives it a DOI. The DOI is added to `README.md` and `CITATION.cff`.

A published version is never changed. Corrections go into the next version.

## Partners

Organisations can support the project with time, tools or funding. A partner is credited in the README and in the Zenodo record of each release. Partners get:

- no exclusive or early access: everyone gets the same data at the same time, under the same licences;
- no say in language rulings, errata or reviews, which stay with the maintainers and the review board;
- no control over the repository.

A partner may build products on the data like anyone else, following the licences. Products must not be presented as the official source or as reviewed by the board unless the rows they use are `reviewed`.

Current partners: **Vadria Innovation Labs** (supporting the project).

## Changing this document

Open a pull request. Changes need approval from a maintainer and, once the board has at least two members, from a board member.

## Current members

**Maintainers:** [@ARUBAGOV33](https://github.com/ARUBAGOV33), [@victorgomesrt-rgb](https://github.com/victorgomesrt-rgb)

**Review board:** being recruited.
