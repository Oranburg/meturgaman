# Words whose qamats is short as a matter of the lexicon

Hebrew writes a long qamats and a short one with the same mark. `romanize/rules.py`
settles almost every case from the shape of the word: an explicit U+05C7, a meteg,
a following hataf qamats, a maqaf after a monosyllable, or a following silent
sheva. Those five between them cover the overwhelming majority of occurrences.

This file holds what is left: words where two different readings share one
spelling and only the lexicon separates them.

## The list

| Word | Reading | Why the shape cannot settle it |
|---|---|---|
| כָּל | kol | A monosyllable closed by an unvoweled consonant, the same shape as `שָׁם` sham and `רָם` ram, both long. |
| כָּל־ | kol- | Before a maqaf the rule already gets this right. Listed so both spellings behave alike whether or not the edition prints the maqaf. |
| חָכְמָה | ḥokhmah | Qamats before a sheva, the same shape as `הָיְתָה` haytah and `לָיְלָה` laylah, both long. |
| אָזְנַיִם | oznayim | Same shape. |
| חָפְשִׁי | ḥofshi | Same shape. |
| קָדְשׁוֹ | qodsho | Same shape. |
| קָדְשִׁי | qodshi | Same shape. |
| עָנְיִי | onyi | Same shape. |
| תָּכְנִית | tokhnit | Same shape. |
| אָנִיָּה | oniyah | Same shape. |
| נָעֳמִי | Noomi | Hataf qamats follows, so the rule reaches this one; listed for completeness. |

## Why a list rather than a rule

An earlier version of this engine tried to decide this shape by rule: a qamats
before a consonant carrying a sheva was read short unless the edition printed a
meteg on it. Tested against 1,934 words of running text it fired fifteen times
and was wrong fifteen times, giving *hoytah* for `הָיְתָה`, *loylah* for
`לָיְלָה`, and *levovkha* for `לְבָבְךָ`.

The reasoning was wrong at its root. Masoretic editions print meteg on some long
qamats and not others, so its absence is evidence of nothing. Worse, the sheva
pass reads the qamats decision and silences the sheva accordingly, so a single
bad call corrupted the vowel and the syllable together.

So the engine now reads this shape as **long**, which is the commoner reading by
a wide margin, and raises `qamats-may-be-short` so a reader knows the shape is
one to check. The words that genuinely take a short qamats are the ones above,
and they are a list because that is what they are in the language: qamats qatan
follows the noun pattern, not the spelling, and no amount of looking at the
letters recovers the pattern.

## How to keep this file honest

A test caps this file. That is deliberate. An earlier version of this project
accumulated a glossary of whole-word transliterations that grew every time the
engine got something wrong, and hid the fact that the engine was getting things
wrong. This file is the opposite of that in three specific ways, and an addition
that breaks any of them belongs in the engine instead:

1. **It answers one question.** Is this qamats long or short. It does not supply
   a romanization, so it cannot paper over a fault anywhere else in the pipeline.
2. **Every entry names why the rule cannot reach it.** An entry that could be
   handled by a rule is a missing rule, not a missing word.
3. **It is scheme-independent.** Vowel length is a fact about Hebrew, not about
   how a given standard writes it, so this file sits outside `schemes/`.

## Authority

The five orthographic rules follow the standard treatment in Gesenius,
*Hebrew Grammar*, ed. Kautzsch, tr. Cowley, 2nd English ed., §9 u to v and §26,
and the meteg convention at §16 g to i. The Library of Congress reaches the same
conclusion about the limits of orthography from the cataloguing side: its
*Hebraica Cataloging* manual sends cataloguers to Alcalay's dictionary
"primarily to distinguish schwa naʻ from schwa nah, a matter which has
significant impact on romanization."

The engine flags rather than guesses wherever those authorities say a dictionary
is needed. A flag is the honest output when the orthography genuinely does not
say.
