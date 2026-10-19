# tools/contribute/

The **contribution tool** (board card P2-09): one website where Aruban teachers and linguists check machine translations, translate words and translate everyday sentences, without a GitHub account. The design, the maintainer's decisions and the setup checklist are in [DESIGN.md](DESIGN.md).

The same files run in two ways:

- **Live**, at <https://arubagov33.github.io/papiamento/>.
  - Teachers sign in with a 6-digit code sent by email.
  - Their answers go to the tool's database in Supabase ([`supabase/`](supabase/)).
  - Each week a sync job turns the review board's decisions into one pull request ([`tools/apply_contributions.py`](../apply_contributions.py)).
- **Demo**, the prototype: open `index.html` from this folder.
  - Nothing is sent anywhere.
  - Answers stay in the browser (`localStorage`) until you export them as JSON.

`config.js` decides which. The committed file says `demo`, and the deploy writes a live one.

## The live site

The workflow **Contribution site** (`.github/workflows/contribute-site.yml`) builds and publishes the site with GitHub Pages. It runs on every push to `main` that changes this folder or the data the tool shows (words, prompts, rules, barbarismos, variants), and can also be run by hand.

It runs `build_site.py --live --vendor`, which writes the whole site into `_site/`:

| What | From |
|---|---|
| `config.js` | The repository variables `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY`. Both are public by design: the database's access rules decide what they can reach. The build refuses a secret key (`sb_secret_…`, or a legacy key whose role is not `anon`). |
| `index.html` | The site's own HTML, with a Content-Security-Policy: scripts only from the site itself, connections only to the Supabase project. |
| `vendor/supabase-js-2.117.2.js` | The browser build of supabase-js, one pinned version. It is downloaded from the npm registry at deploy time and checked against its published sha512 checksum before it is used. |
| `data/sample.js` | Every machine-drafted word still in `draft` (2,918 now; "uncertain" ones first, then by frequency) and every untranslated word that occurs in the repo's texts (1,539 now), ordered by [`tools/word_frequency.py`](../word_frequency.py). Also every prompt in `corpus/parallel/` and `eval/parallel/`. |
| `crops/<id>.png` | The entry's own column of the printed AB 2018 word-list page, with the entry highlighted. A few entries can't be found on their page; those link to the PDF instead. |
| `data/checks.js`, `data/strings.js` | The live checks and the interface text, as in the demo. The Papiamento-text check runs here too, and the build fails if it finds a problem. |
| `pdf/AB2018.pdf` | For "Open the whole page". |

What the live tool does differently from the demo:

- **Sign-in.** A 6-digit code by email, valid for an hour. "Send a new code" is offered after a minute. A first sign-in goes on to the profile and licence steps, which create the profile in the database.
- **Blind answers.** A contributor sees only their own answers. The queues come from `queue_state()`, which returns ids and counts, never other people's answers.
- **The review board.** It appears for board members, and for maintainers while the board has fewer than two members. The database decides this, not the browser. Board members see everyone's answers, without emails.
- **States.**
  - A loading screen while the tool connects.
  - An error screen with **Try again** if it can't connect (offline, or the database is unreachable).
  - The demo's saving, saved, error, offline and empty states.
  - "Someone else was first" when another person gave the second answer, or the board decided, while you were answering.
  - "Please sign in again" when a sign-in has expired.
- **Account page.**
  - Show or hide your name in the credits.
  - Download your own contributions as JSON.
  - Sign out.
  - The demo's switch-person, connection-simulator, import and "delete everything" tools are not shown.

Setting up the database once, and adding board members, is described in [`supabase/README.md`](supabase/README.md).

## Open the demo

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
| `index.html`, `style.css`, `app.js` | The tool. No framework. Phone first, with a sidebar layout from 900 px. `app.js` has both backends: demo (`localStorage`) and live (supabase-js). |
| `config.js` | Which backend to use. The committed file is the demo; the deploy replaces it. |
| `theme.js` | Applies the saved appearance (Light, the default, Dark or Match device) before the first paint |
| `build_site.py` | Builds the live (or a full demo) site into one folder for GitHub Pages. Tested in `tests/test_build_site.py`. |
| `supabase/` | The database: migration, access rules, their tests, the sign-in email and the setup guide |
| `assets/hero.webp` | The welcome image: a text-free slice of the README banner (`.github/assets/banner.webp`, Higgsfield artwork) |
| `checker.js` | Live checks on Papiamento text: the repo's rules, barbarismos, Curaçao variants and the AB 2018 word list. Works in the browser and in Node. |
| `prompts.tsv` | 12 English and Spanish prompts written for the demo (`origin = written-for-prototype`), CC0. Not part of the dataset; the live site uses `corpus/parallel/` and `eval/parallel/`. |
| `ui-strings.tsv` | Interface text: English, and a Papiamento machine draft (`pap_status = draft`) for a teacher to check |
| `build_sample.py` | Builds the demo's `data/*.js` and `crops/*.png` from the repo's own data and `sources/pdf/AB2018.pdf`. Checks the Papiamento interface text. |
| `data/` | Generated; do not edit by hand. The demo's sample words and prompts, check data, interface strings. |
| `crops/` | Generated crops of the printed AB 2018 word-list pages for the demo: four columns, and one column for phones |
| `test_checker.mjs` | Tests the checker against every rule test, barbarismo and Curaçao pair in the repo |

## Rebuild and test

`build_sample.py` and `build_site.py` need PyMuPDF and Pillow. The validator itself needs neither.

```sh
python3 tools/contribute/build_sample.py
node tools/contribute/test_checker.mjs
python3 -m unittest tests.test_build_site
```

To build the full site locally as a demo (all words, no database), in a folder that is not committed:

```sh
python3 tools/contribute/build_site.py --out _site
```

The build fails if a word in the Papiamento interface text is not an AB 2018 headword or if a repo check fires on it. It checks spelling, not grammar: a teacher still has to read `ui-strings.tsv`.

## What it is not

- It is not part of the release: `tools/build_dist.py` does not read this folder.
- Nothing becomes `reviewed` in the tool itself. A board member's decision becomes a row in the weekly sync pull request, and it reaches the data only when that pull request, approved on GitHub by the board member named in `reviewed_by`, is merged.
- The demo's answers are test data, not contributions.
