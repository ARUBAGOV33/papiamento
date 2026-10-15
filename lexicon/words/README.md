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
| `translated_by` | `machine` for machine drafts, or the GitHub username of whoever wrote the translations. Replace `machine` with your username when you correct a draft. |
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
| [A](A/) | 1276 | 19% | 19% | 19% | 0% |
| [B](B/) | 924 | 19% | 19% | 19% | 0% |
| [C](C/) | 1922 | 21% | 21% | 21% | 0% |
| [D](D/) | 1136 | 16% | 16% | 16% | 0% |
| [E](E/) | 722 | 19% | 19% | 19% | 0% |
| [F](F/) | 624 | 16% | 16% | 16% | 0% |
| [G](G/) | 537 | 13% | 13% | 13% | 0% |
| [H](H/) | 560 | 15% | 15% | 15% | 0% |
| [I](I/) | 820 | 16% | 16% | 16% | 0% |
| [J](J/) | 61 | 18% | 18% | 18% | 0% |
| [K](K/) | 248 | 14% | 14% | 14% | 0% |
| [L](L/) | 456 | 19% | 19% | 19% | 0% |
| [M](M/) | 947 | 19% | 19% | 19% | 0% |
| [N](N/) | 293 | 23% | 23% | 23% | 0% |
| [O](O/) | 308 | 22% | 22% | 22% | 0% |
| [P](P/) | 1481 | 20% | 20% | 20% | 0% |
| [Q](Q/) | 11 | 9% | 9% | 9% | 0% |
| [R](R/) | 931 | 15% | 15% | 15% | 0% |
| [S](S/) | 1548 | 17% | 17% | 17% | 0% |
| [T](T/) | 765 | 20% | 20% | 20% | 0% |
| [U](U/) | 74 | 23% | 23% | 23% | 0% |
| [V](V/) | 282 | 12% | 12% | 12% | 0% |
| [W](W/) | 139 | 17% | 17% | 17% | 0% |
| [X](X/) | 4 | 0% | 0% | 0% | 0% |
| [Y](Y/) | 74 | 27% | 27% | 27% | 0% |
| [Z](Z/) | 75 | 8% | 8% | 8% | 0% |
| **All** | **16218** | **18%** | **18%** | **18%** | **0%** |
<!-- PROGRESS:END -->
