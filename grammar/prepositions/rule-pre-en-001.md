---
id: RULE_PRE_EN_001
title: Use den, not Spanish en, for location
status: draft
source: RUL2026
page: ""
severity: error
reviewed_by: ""
---

## Rule

Spanish en used for a location is not Aruban Papiamento; write den instead. en is kept only in fixed expressions.

## Source

Maintainer ruling in `_meta/invariants.md` (Grammar table): "Location en becomes den." No book in the registry states this rule. The fixed expressions under Exceptions come from the AB 2018 word list, which lists en only as "en (expr.)" (word list Pagina 25).

## Correct

- den cas (`_meta/invariants.md`)

## Incorrect

- en cas → den cas (`_meta/invariants.md`)

## Exceptions

- Fixed expressions with en in the AB 2018 word list, Pagina 25: en bes di, en bista di, en cambio, en espera di, en todo caso.
- The Departamento di Enseñansa books also use en in fixed phrases, for example en pugna cu (PRE2016 §1.2 Forma, III. Expresion preposicional, p. 2) and de bes en cuando (MOR2010 §5.3 Forma, p. 31).

## Notes

- Barbarismo row bar-0007 (en → den) points to this rule. It cites AB 2018 word list p. 20, but the entry "en (expr.)" is on word list Pagina 25, the same page err-0013 gives for en todo caso. The row's page needs correcting.
- Not every locative en maps to den. PRE2016 §1.3.4 (p. 6) describes den for an entity in a place with two or three dimensions that is closed or limited, while na marks a place in general (§1.3.7, p. 15: "Francisco ta biba na Venezuela."). The ruling is followed here; a reviewer may want the checker to suggest den or na rather than always den. See RULE_PRE_NA_SPACE_001.
- The checker should flag en only before a place, never inside the fixed expressions above. en todo caso is also covered by err-0013.
- The rule pack had no citation for this rule.
