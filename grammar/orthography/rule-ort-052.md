---
id: RULE_ORT_052
title: Unchanged Dutch and English loans keep their original spelling
status: draft
source: AB2018
page: "42"
severity: error
reviewed_by: ""
---

## Rule

Words from Dutch and English whose pronunciation has (practically) not changed are written in their original form. Words adopted from French follow the current Dutch spelling rules, and words adopted from English follow the latest edition of the Merriam-Webster dictionary.

## Source

AB 2018 no. 68, annex Ortografia di Papiamento, §12.2 "Hulandes, Ingles y Frances", point 1, gazette page 42. "Palabra cu ta bin di Hulandes y Ingles y cu (practicamente) no a cambia den pronunciacion, ta skirbi segun e forma original."

## Correct

- bandeau, catch, crèche, kampeer
- belasting, computer, huurmento, schaats
- paté

## Exceptions

- a. These words and their derivations are written as printed: altar, apelsina, automat, bek, cadaver, calbas, caliber, canari, caramel, caracter, carcas, caret, chens, clarinet, coma (,), compas, cosmos, comer, comper, credit, dobel, dres, electricien, electrode, ful, horizontal, hospital, kapseis, mamut, material, maximal, minimal, neutral, normal, o.k., optimal, ortodox, oval, palet, papiyot, par, paralel, pashent, payet, pilar, pres, rom, slek, standard, trupial, vaginal, vertical, wak, w.c.
- b. "Ta skirbi nomber geografico sin strepi. Ehempel: Noord Korea."

## Notes

- Footnote 1: "practicamente" means a small change is possible, for example in the pronunciation of the word "appel". Footnote 2: the exception list is not necessarily complete.
- paté (the French example) and crèche are printed with accents; both are in `_meta/allowlists/accented-loans.txt`. See RULE_ORT_ACCENT_001.
- The page splits "electricien elec-trode" across a line; it is given above as two words, electricien and electrode, both headwords of the AB 2018 word list.
- Verb base forms, derivations and compounds of these words: RULE_ORT_054. Loans whose sound has changed: RULE_ORT_053.
- The old rule pack also had RULE_ORT_BORROW_001 for §12.2; it was merged into this rule, RULE_ORT_053 and RULE_ORT_054.
- The old rule pack had this as a warning; the law states it as a rule, so the severity here is error. A checker should flag only words it can match to the AB 2018 word list or `lexicon/loanwords/`.
- ORT2009 prints the same section on page 42.
