# tools/contribute/

A clickable **prototype** of the contribution tool (board card P2-09): one website where Aruban teachers and linguists check machine translations, translate words and translate everyday sentences, without a GitHub account. The design, the decisions it needs and the recommendations are in [DESIGN.md](DESIGN.md).

The prototype runs from a local file. It sends nothing anywhere and keeps answers in the browser (`localStorage`) until you export them as JSON.

## Open it

Double-click `index.html`, or from the repository root:

```sh
open tools/contribute/index.html
```

Or serve the repository and open <http://localhost:8000/tools/contribute/>:

```sh
python3 -m http.server 8000
```

Then try this:

1. Go through the four onboarding steps. The email step is a mock: type any address and any six digits. Nothing is sent and the address is not stored.
2. Work through the three modes from Home. Each answer ends on a feedback sheet. On a laptop, word tasks use two columns.
3. Go to **Account → Switch person → + Add a person** and add a second teacher. That person can rate the first person's sentences and give the second answer on words.
4. Add a third person and switch on "review board". That person gets the **Review board** queue.
5. **Account → Prototype: connection** sets Normal, Slow or Failing, to show the loading and error states.
6. **Account → Export** downloads the JSON and previews the TSV rows a pull request would contain. **Delete everything in this browser** resets it.

## Files

| File | What |
|---|---|
| `index.html`, `style.css`, `app.js` | The prototype. No libraries, no network. Phone first, with a sidebar layout from 900 px. |
| `assets/hero.webp` | The welcome image: a text-free slice of the README banner (`.github/assets/banner.webp`, Higgsfield artwork) |
| `checker.js` | Live checks on Papiamento text: the repo's rules, barbarismos, Curaçao variants and the AB 2018 word list. Works in the browser and in Node. |
| `prompts.tsv` | 12 English and Spanish prompts written for the prototype (`origin = written-for-prototype`), CC0. Not part of the dataset. |
| `ui-strings.tsv` | Interface text: English, and a Papiamento machine draft (`pap_status = draft`) for a teacher to check |
| `build_sample.py` | Builds `data/*.js` and `crops/*.png` from the repo's own data and `sources/pdf/AB2018.pdf`. Checks the Papiamento interface text. |
| `data/` | Generated; do not edit by hand. Sample words and prompts, check data, interface strings. |
| `crops/` | Generated crops of the printed AB 2018 word-list pages: four columns, and one column for phones |
| `test_checker.mjs` | Tests the checker against every rule test, barbarismo and Curaçao pair in the repo |
| `proposal/` | Draft schemas for the new tables and a sketch of the tool's database (see DESIGN.md §5(d)) |

## Rebuild and test

`build_sample.py` needs PyMuPDF and Pillow. The validator itself needs neither.

```sh
python3 tools/contribute/build_sample.py
node tools/contribute/test_checker.mjs
```

The build fails if a word in the Papiamento interface text is not an AB 2018 headword or if a repo check fires on it. It checks spelling, not grammar: a teacher still has to read `ui-strings.tsv`.

## What it is not

- It is not deployed and has no server, sign-in or email.
- It is not part of the release: `tools/build_dist.py` does not read this folder.
- Its sample words come from `lexicon/words/` at the commit recorded in `data/sample.js`.
- Its answers are test data, not contributions.
