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

## Progress

<!-- PROGRESS:START -->
| Letter | Words | English | Dutch | Spanish | Reviewed |
|---|---:|---:|---:|---:|---:|
| [A](A/) | 1276 | 0% | 0% | 0% | 0% |
| [B](B/) | 924 | 0% | 0% | 0% | 0% |
| [C](C/) | 1922 | 0% | 0% | 0% | 0% |
| [D](D/) | 1136 | 0% | 0% | 0% | 0% |
| [E](E/) | 722 | 0% | 0% | 0% | 0% |
| [F](F/) | 624 | 0% | 0% | 0% | 0% |
| [G](G/) | 537 | 0% | 0% | 0% | 0% |
| [H](H/) | 560 | 0% | 0% | 0% | 0% |
| [I](I/) | 820 | 0% | 0% | 0% | 0% |
| [J](J/) | 61 | 0% | 0% | 0% | 0% |
| [K](K/) | 248 | 0% | 0% | 0% | 0% |
| [L](L/) | 456 | 0% | 0% | 0% | 0% |
| [M](M/) | 947 | 0% | 0% | 0% | 0% |
| [N](N/) | 293 | 0% | 0% | 0% | 0% |
| [O](O/) | 308 | 0% | 0% | 0% | 0% |
| [P](P/) | 1481 | 0% | 0% | 0% | 0% |
| [Q](Q/) | 11 | 0% | 0% | 0% | 0% |
| [R](R/) | 931 | 0% | 0% | 0% | 0% |
| [S](S/) | 1548 | 0% | 0% | 0% | 0% |
| [T](T/) | 765 | 0% | 0% | 0% | 0% |
| [U](U/) | 74 | 0% | 0% | 0% | 0% |
| [V](V/) | 282 | 0% | 0% | 0% | 0% |
| [W](W/) | 139 | 0% | 0% | 0% | 0% |
| [X](X/) | 4 | 0% | 0% | 0% | 0% |
| [Y](Y/) | 74 | 0% | 0% | 0% | 0% |
| [Z](Z/) | 75 | 0% | 0% | 0% | 0% |
| **All** | **16218** | **0%** | **0%** | **0%** | **0%** |
<!-- PROGRESS:END -->
