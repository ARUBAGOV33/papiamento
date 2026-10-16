---
id: RULE_ORT_050
title: Words from Spanish follow Papiamento spelling, except listed words
status: draft
source: AB2018
page: "41"
severity: error
reviewed_by: ""
---

## Rule

Words that come from Spanish are written by the rules of the Papiamento orthography. The page lists exceptions that are written as printed, and their derivations and compounds keep that basic form. A second list of words is written with a final z, which is kept in the plural and in derivations with the suffix mente.

## Source

AB 2018 no. 68, annex Ortografia di Papiamento, §12.1 "Spaño", gazette page 41. "Palabra cu ta bin di Spaño ta skirbi segun e reglanan di “Ortografia di Papiamento”."

## Exceptions

- Point 1, words and expressions written as printed (derivations and compounds keep the basic form): acordeon, a la parrilla, anecdota, area, auxilia, aros con pollo, Azteca, bienhechor, boxeo, bucea, campeon, Caraqueño, cesarea, comiquita, contemporaneo, coreografia, Costariqueño, cumpleaño(s), delinea, eccema, eroneo, es decir, (e)spontaneo, guerrilla, guillotina, hallazgo, heterogeneo, homogeneo, ideologia, instantaneo, Jamaiquino, jinete, joya, liderazgo, llano, linea aereo, linea recta, linoleo, malhechor, marea, momentaneo, pellejo, petroleo, piratea, planea, Portoriqueño, quehaceres, quesillo, quinceañera, quinteto, refresqueria, sanea, Santa Oleo, simultaneo, sondea, tequila, toque de queda
- Point 2, words written with a final z (kept in the plural and before mente): actriz, antifaz, avestruz, caliz, capaz, cruz, cicatriz, disfraz, eficaz, escasez, estupidez, feliz, feroz, fluidez, incapaz, ineficaz, infeliz, inmadurez, invalidez, luz, madurez, matiz, matriz, paz, rapidez, ridiculez, timidez, tenaz, validez
- Point 3, nouns ending in eza or anza: see RULE_ORT_051.

## Notes

- Footnote 1 (page 41): the lists are not necessarily complete, "E palabranan no necesariamente ta un cantidad absoluto."
- The page sets the lists in narrow columns and breaks some words across lines (Ja-maiquino, ce-sarea, contem-poraneo, anti-faz, dis-fraz, inca-paz, inma-durez, ridi-culez, timi-dez). They are given above as whole words, which are headwords of the AB 2018 word list.
- The page gives no example of the general rule itself. Spanish words that have their own Papiamento word are listed as barbarismos in `lexicon/barbarismos/barbarismos.tsv`.
- The old rule pack had this as a warning; the law states it as a rule, so the severity here is error. A checker should flag only words it can match to the AB 2018 word list.
- The final-z list and point 3 are also covered by RULE_ORT_S_Z_001 from the old rule pack.
- ORT2009 prints the same section on page 41.
