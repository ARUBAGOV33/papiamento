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

## Grammar rules with no machine rule

These flaggable rules in `grammar/` have no pattern here, because a regular expression cannot check them reliably. An auditor needs a word list, sentence structure or meaning for them, or a human reviewer.

| Rule | Why there is no pattern |
|---|---|
| `RULE_MOR_IMP_002` | To flag a wrong imperative (bay/ta/tin used where ban/sea/tene belong), the checker would have to tell imperative mood from statements. |
| `RULE_MOR_NOUN_PLURAL_002` | Two of its three cases (general sense, indeterminate quantity) depend on meaning. |
| `RULE_MOR_NOUN_PLURAL_005` | Flagging -nan on an adjective when two or more adjectives follow the noun needs part-of-speech knowledge. |
| `RULE_MOR_NOUN_PLURAL_006` | Flagging -nan on a prenominal adjective ('e bunitanan cas') needs to know which word is an adjective and which a noun. |
| `RULE_ORT_004` | The file says a final u is often correct (sucu, leu, riu, friu), so a checker needs a word list. |
| `RULE_ORT_006` | Needs syllable division. |
| `RULE_ORT_008` | Severity is suggestion and depends on judgement: whether two main clauses or an enumeration should take a semicolon. |
| `RULE_ORT_011` | A lowercase phrase or enumeration after a colon can only be told from a full sentence (RULE_ORT_010) by syntax. |
| `RULE_ORT_012` | Whether a new topic starts after an ellipsis is a matter of meaning (the file says so). |
| `RULE_ORT_013` | Whether an ellipsis is inside a sentence (suspense) or starts a new topic (RULE_ORT_012) depends on meaning (the file says so). |
| `RULE_ORT_015` | Telling a quoted independent sentence from a quoted phrase needs syntax. |
| `RULE_ORT_016` | A regex would have to recognise the greeting at the start of a letter and the line structure. |
| `RULE_ORT_017` | Needs a list of personal names, pet names and nicknames. lexicon/names is empty, and the page gives no list. |
| `RULE_ORT_020` | Severity warning. |
| `RULE_ORT_024` | The same word is capitalised for a people (Indjan) and lowercase for a race or religion (rasgo indjan, hudiunan), so the choice depends on meaning (the file says so). |
| `RULE_ORT_025` | Severity warning. |
| `RULE_ORT_041` | Verb + verb compounds depend on meaning. |
| `RULE_ORT_042` | Joining depends on the compound having a single main stress, which a checker cannot hear. |
| `RULE_ORT_047` | One stress versus two decides joined versus split reduplication (pegapega vs pega pega), and a checker cannot hear stress. |
| `RULE_ORT_050` | The final-z list (point 2) is already covered by RULE_ORT_S_Z_001. |
| `RULE_ORT_053` | Needs matching against the AB 2018 word list or lexicon/loanwords (the file says so). |
| `RULE_ORT_054` | Verb roots and derivations of original-form loans need a lexicon. |
| `RULE_PRE_DI_REF_001` | Needs meaning. riba is correct for space and manner after the same nouns (riba nivel, riba tereno). |
| `RULE_STI_CONC_001` | nan after gobierno/comision/club can be an object pronoun referring to other people (gobierno a yuda nan, gobierno a duna nan placa), which a regex cannot tell from possessive nan. |
| `RULE_STI_GER_001` | Checking that the gerund and the main clause share a subject needs syntax. |
| `RULE_STI_ORDER_001` | It depends on what the writer meant. |
| `RULE_STI_TRANSP_001` | The page gives no length limit or score and prints no example that can be quoted. |
| `RULE_STY_ASYM_001` | Keeping the same person through a sentence needs reference resolution, and the page prints no incorrect example that can be quoted. |
| `RULE_STY_ASYM_002` | Whether the items in an enumeration are of the same kind depends on meaning, and the page itself allows the mismatch in recreational text. |
| `RULE_STY_REP_001` | This is advice against filler use of valid words (pues is in AB 2018). |
| `RULE_SYN_Q_003` | A regex cannot tell a direct question from a fronted indirect question (Con e pelicula a caba Edwin no a conta mi.), a concessive (Con cu mi a purba, ...) or an exclamation (Ki dushi ...). |
