# rules/

Machine-readable rules for the Aruban Papiamento writing auditor, each with its own tests. Every rule here has a plain-language explanation in [`grammar/`](../grammar/) with the same id.

**Status:** empty. The rules are imported in phase 1 (board card P1-11).

## Planned format

`rules.jsonl`, one rule per line:

| Field | Content |
|---|---|
| `rule_id` | Same id as in `grammar/`, e.g. `RULE_ORT_ACCENT_001` |
| `pattern` | JavaScript-compatible regular expression |
| `replacement` | Suggested fix, or `null` to flag only |
| `severity` | `error`, `warning` or `suggestion` |
| `examples` | Correct and incorrect sentences; the incorrect ones must trigger the rule, the correct ones must not |
| `source`, `page`, `status` | As everywhere else |

The validator will run every rule against its own examples (gate G5), so a rule that stops catching its examples fails the build.
