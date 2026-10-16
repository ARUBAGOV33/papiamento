---
id: RULE_MOR_NOUN_PLURAL_002
title: Plural meaning without nan
status: draft
source: MOR2010
page: "10"
severity: warning
reviewed_by: ""
---

## Rule

The suffix nan is not used, even when the meaning is plural, in three cases: the noun has a general sense; the noun denotes an indeterminate quantity; or the noun is combined with a definite or indefinite numeral.

## Source

Manual di Gramatica di Papiamento: Morfologia (2010), §2.3.1 "Sustantivo cu nificacion plural sin e sufiho nan", p. 10: "No ta uza e sufiho nan ora tin un interpretacion plural den caso cu:".

## Correct

- General sense: Porco ta gusta come sushi.
- General sense: Sustantivo ta forma un categoria gramatical.
- General sense: No ta berdad cu colebra semper ta agresivo.
- Indeterminate quantity: Pa forma un ehercito mester solda.
- Indeterminate quantity: Tempo mi tabata mucha mi welo tabata cria galiña, carne y cabrito.
- Indeterminate quantity: Na Aruba tabatin Indjan e tempo aya.
- With a numeral: Bo no ta contento ainda cu bo ta gana tres mil florin?
- With a numeral: Ayera nochi nos a mira hopi auto riba caretera.
- With a numeral: Tin diferente asunto pa discuti ainda riba agenda.

## Notes

- Severity is warning because the first two cases depend on meaning, which a checker cannot judge reliably. The numeral case is enforced as an error by the invariant "No -nan after a bare numeral" (_meta/invariants.md) and by RULE_GRA_PLURAL_001. See also RULE_STY_PLUR_001 (Stilistica, another batch).
- Read with §2.3.2 (p. 11), the numeral case applies to a numeral without an article, possessive or demonstrative. With a definite article and demonstrative the noun takes nan: "E tres edificionan aya ta di Gobierno." (RULE_MOR_NOUN_PLURAL_001), as the invariant also says.
- The page prints no incorrect forms.
