---
id: RULE_SYN_NEG_001
title: Two kinds of negation - the whole sentence or one sentence part
status: draft
source: SIN2015
page: "89"
severity: info
reviewed_by: ""
---

## Rule
Negation denies what the whole sentence, or what one part of the sentence, denotes. Sintaxis distinguishes two kinds: negation of the whole sentence and negation of a sentence part. The grammatical means used to negate are called negation elements, and a sentence with a negation element is a negative sentence.

## Source
Manual di Gramatica di Papiamento: Sintaxis (2015), §5.1 "Introduccion" and §5.2 "Clasificacion", p. 89.
"Ta distingui dos clase di negacion: negacion di henter e frase y negacion di un parti di frase"

## Correct
- E doño di e compania no a duna su trahadonan bonus. (negacion di henter e frase)
- E reina di Carnaval di e aña aki no ta biba na Aruba tampoco. (negacion di henter e frase)
- No ta e bestianan den cura di Shon Poli a come e resto di cuminda. (negacion di suheto)
- Awa no a cay ayera. (negacion di henter e frase)
- No ta na machi su cas el a bay. (negacion di complemento adverbial di luga)

## Notes
- Severity is info: a classification. It matters for a checker or a rewriter because the two kinds mean different things, but there is nothing to flag.
- Whole-sentence negation: RULE_SYN_NEG_002. Negation of a sentence part: RULE_SYN_NEG_003.
- The negation elements are listed in §5.3 (pp. 90–91): no, hamas, nunca, tampoco, ni, nada, ningun hende / niun hende and ningun caminda / niun caminda. See RULE_SYN_NEG_004 for using several of them together.
