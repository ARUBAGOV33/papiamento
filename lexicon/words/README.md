# lexicon/words/

One folder per letter, `A` to `Z`. Each holds `words.tsv`: every headword of the AB 2018 no. 68 word list that starts with that letter. Words starting with `ñ` are in `N`, as in the AB list.

## Columns

| Column | What to put |
|---|---|
| `id` | Stable id (`pap-000412`). Assigned once; never change it. |
| `lemma` | The word exactly as the AB list prints it. |
| `alt` | Alternative forms the AB list gives in brackets. |
| `pos` | Part of speech (`s.`, `v.`, `adh.`, `adv.`, … see conventions). Empty if unknown. |
| `tag` | The AB list's own label in parentheses, copied exactly. |
| `en`, `nl`, `es` | Translations; several senses separated by `; `. |
| `status` | `draft` until a review-board member checks it. |
| `reviewed_by` | GitHub username of the reviewer. |
| `source`, `page` | Where the word is printed (`AB2018` + page). |
| `notes` | Anything a reviewer should know. |

## Help with one letter

Pick a letter, open its `words.tsv`, and work through the `draft` rows: check each translation, fix what's wrong, and leave a note when unsure. Each letter folder will get a generated progress page showing how many words have reviewed English, Dutch and Spanish translations.
