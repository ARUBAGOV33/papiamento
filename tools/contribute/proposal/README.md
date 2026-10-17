# tools/contribute/proposal/

Drafts for the maintainer to accept, change or reject (DESIGN.md §5(d)). Nothing here is read by the validator or the release build, and `_meta/schema/` is unchanged.

| File | For |
|---|---|
| `parallel-prompts.schema.json` | `corpus/parallel/prompts.tsv` and `eval/parallel/prompts.tsv`: English and Spanish prompts |
| `parallel-pairs.schema.json` | `corpus/parallel/pairs.tsv` and `eval/parallel/pairs.tsv`: Aruban Papiamento translations, several per prompt |
| `contributors.schema.json` | `_meta/contributors.tsv`: everyone credited, by handle. No email addresses. |
| `supabase-schema.sql` | The tool's own working database, with the access rules that keep answers independent. Not run anywhere. |

If accepted, a separate pull request would:

1. move the schemas into `_meta/schema/` and add them to `registry.json`;
2. change `_meta/conventions.md` (contributed sentences have no source page) and LICENSE-DATA (CC0 for the parallel folders);
3. teach `tools/validate.py` to check contributor handles.
