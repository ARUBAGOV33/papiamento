---
id: RULE_PRE_EN_001
title: Use den or na, not Spanish en, for location
status: draft
source: RUL2026
page: ""
severity: error
reviewed_by: ""
---

## Rule

Spanish en used for a location is not Aruban Papiamento. Write den for a place that is closed or limited, and na for a place in general; which one depends on the meaning. en is kept only in fixed expressions.

## Source

Maintainer ruling in `_meta/invariants.md` (Grammar table), as decided on 2026-10-17: locative en becomes den or na, depending on the meaning. No book in the registry says that en is wrong. The choice between den and na follows Preposicion y Interheccion:

- §1.3.4 Den, I. Relacion di espacio (PRE2016 p. 6): "Den e relacion aki den ta denota un entidad den un luga cu dos of tres dimension. E luga aki ta un espacio cera of limita:"
- §1.3.7 Na, I. Relacion di espacio (PRE2016 p. 15): "E preposicion na den su relacion di espacio, por lo general, ta indica un luga den espacio, sea sin dimension of cu un of mas dimension:"

The fixed expressions under Exceptions come from the AB 2018 word list, which lists en only as "en (expr.)" (word list Pagina 25).

## Correct

- den cas (`_meta/invariants.md`)
- Mi amigonan ta keiro den auto. (PRE2016 p. 6)
- Francisco ta biba na Venezuela. (PRE2016 p. 15)

## Incorrect

- en cas → den cas (`_meta/invariants.md`; a house is a closed place)

## Exceptions

- Fixed expressions with en in the AB 2018 word list, Pagina 25: en bes di, en bista di, en cambio, en espera di, en todo caso.
- The Departamento di Enseñansa books also use en in fixed phrases, for example en pugna cu (PRE2016 §1.2 Forma, III. Expresion preposicional, p. 2) and de bes en cuando (MOR2010 §5.3 Forma, p. 31).

## Notes

- Barbarismo row bar-0007 (en → den; na) points to this rule. It cites AB 2018 word list p. 20, where the right form den is printed, like the other ruling barbarismos (bar-0001 famia p. 27, bar-0002 tin p. 67); "en (expr.)" is on word list Pagina 25, the same page err-0013 gives for en todo caso.
- Before 2026-10-17 the ruling said en always becomes den. The maintainer changed it to den or na after PRE2016 pp. 6 and 15 were checked. See RULE_PRE_NA_SPACE_001.
- Because the right word depends on the meaning, RULE_PRE_EN_001 only flags en and names both options; it has no automatic fix.
- The checker should flag en only before a place, never inside the fixed expressions above. en todo caso is also covered by err-0013.
- The rule pack had no citation for this rule.
