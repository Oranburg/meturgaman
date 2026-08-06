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
| כָּל | kol | A monosyllable closed by an unvoweled consonant, which is the same shape as `שָׁם` sham and `רָם` ram, both of which are long. Only the word itself decides. |
| כָּל־ | kol- | Before a maqaf the rule already gets this right. Listed so that both spellings behave alike whether or not the edition prints the maqaf. |

## Why it is this short, and how to keep it that way

Two entries is not an oversight. Every other qamats qatan in common use is
followed by a consonant carrying a silent sheva, which the rule detects:
`חָכְמָה` ḥokhmah, `אָזְנַיִם` ozhnayim, `חָפְשִׁי` ḥofshi, `קָדְשׁוֹ` qodsho. And
`צָהֳרַיִם` tsohorayim is caught by the hataf qamats after it. None of them belong
here.

A test asserts this file stays under a dozen entries. That is deliberate. An
earlier version of this project accumulated a glossary of whole-word
transliterations, which grew every time the engine got something wrong and hid
the fact that the engine was getting things wrong. This file is the opposite of
that in three specific ways, and an addition that breaks any of them belongs in
the engine instead:

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
