# sources/permissions/

Written permissions to republish sources. A source with `licence_tier` = `permission` in [`../sources.tsv`](../sources.tsv) must point here in its `permission_ref`.

## What goes here

- One file per permission: the signed letter or e-mail, saved as PDF, named `<rights-holder>-<YYYY-MM-DD>.pdf` (lowercase, kebab-case, ASCII), for example `departamento-di-ensenansa-2026-10-15.pdf`.
- Only what the permission itself says: who gave it, on whose behalf, the date, and which works it covers. Remove private contact details (home addresses, phone numbers) before filing.
- When a permission is filed, update `permission_ref` in `sources.tsv` and the "Permission reference" row on each card it covers.

## Current status

| Rights holder | Works | Status |
|---|---|---|
| Departamento di Enseñansa (DE), Aruba | MOR2010, SIN2015, PRE2016, ORT2009, VOC2009 | Permission granted verbally through the Minister of Education and Innovation on 2026-10-15. Written confirmation pending; it will be filed here. |

Notes:

- ORT2009 and VOC2009 do not print a publisher. The written confirmation should name them explicitly.
- STI2008 (Stilistica di Papiamento) is `restricted` and not in the repo: it prints no publisher. If the written confirmation covers it, change its tier and add its PDF.
