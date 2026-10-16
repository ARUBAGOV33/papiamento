# rules/

Machine-readable rules for the Aruban Papiamento writing auditor. Each rule links to the grammar file with the same id in [`grammar/`](../grammar/), which holds the rule's wording, source page and examples. This folder holds only what a program needs to find the problem.

Word-for-word swaps (barbarismos such as `hay` → `tin`, Curaçao spellings such as `kome` → `come`) are not repeated here: an auditor reads them straight from [`lexicon/barbarismos/`](../lexicon/barbarismos/) and [`lexicon/variants/`](../lexicon/variants/).

## Format: `rules.jsonl`

One JSON object per line:

| Field | Content |
|---|---|
| `rule_id` | Id of the grammar file (`RULE_ORT_...`). Only rules with severity `error`, `warning` or `suggestion`; `info` rules describe usage and have nothing to flag. |
| `pattern` | Regular expression that finds the problem. |
| `flags` | `""` or `"i"` (ignore case). |
| `replacement` | The fix, with `$1`, `$2` for groups; `null` when the rule only flags. |
| `message` | One plain sentence: what is wrong and what to write instead. |
| `tests` | `match`: examples the rule must flag. `no_match`: examples it must leave alone. `fix`: `{"text", "expect"}` pairs for the replacement. All copied verbatim from the grammar file. |
| `derived` | Optional tests made by a mechanical change of a printed example (capitalising, splitting a joined word…): `{"text", "from", "change", "expect"}`. `from` must be printed in the grammar file. |
| `notes` | What the rule deliberately does not catch. |

Severity, source and page are not repeated: they come from the grammar file.

## Patterns must work in JavaScript and Python

The Skirbi checker runs these rules in JavaScript; the validator runs them in Python. The two engines differ in small ways, so:

- Do not use `\b`, `\B`, `\w` or `\W`. In JavaScript they treat ñ and accented letters as non-letters, so `\ban\b` wrongly matches inside `mañan`. Write word boundaries as `(?<![A-Za-zÀ-ÿñÑ'])` before and `(?![A-Za-zÀ-ÿñÑ'])` after.
- No inline flags such as `(?i)`, no named groups, no `\A` or `\Z`. Lookbehind must have a fixed length.

## How the rules are tested

On every pull request:

- `python3 tools/validate.py` (gate G5) checks that every test sentence is printed in the grammar file, that each rule flags its `match` tests and leaves its `no_match` tests alone, that fixes produce the expected text, and that no rule flags a correct example in another grammar file.
- `node tools/test_rules.mjs` runs the same tests with JavaScript's RegExp.

Precision matters more than coverage. A rule that flags correct Aruban text annoys teachers and misleads AI models, so a rule is left out when a pattern cannot check it reliably.
