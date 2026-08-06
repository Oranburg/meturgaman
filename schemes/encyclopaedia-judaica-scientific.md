<!-- Generated from a two-channel reading of the source document: one
     programmatic extraction and one visual reading of the rendered pages,
     diffed cell by cell. See sources/manifest.md for the document, its URL,
     and its SHA-256. Edit this file to change the scheme; the code reads it. -->
---
name: encyclopaedia-judaica-scientific
citation: "Encyclopaedia Judaica, 2nd ed. (2007), vol. 1, p. 197, Transliteration Rules, Scientific column"
source: encyclopaedia-judaica.pdf
doubles: true
never_double: [sh]
hyphenate_prefixes: false
always_mark_alef: true
shva_na: "ə"
tsere_male: "e"
hireq_male: "i"
holam_male: "o"
shuruq: "û"
source_gaps: [hataf_qamats, qamats_qatan]
---

# Encyclopaedia Judaica, Scientific

The second column of the same page. Where the General column is a pronunciation
aid, this one is a comparative-Semitics notation: alef and ayin are written,
spirantized consonants are distinguished from their stops, and vowels carry
length and quality marks.

Read the caveat below before using it on running text. Several of its cells are
sets of alternatives rather than single values, and this file chooses the first
of each and says so.

## Consonants

| Letter | Name | Romanization |
|---|---|---|
| א | alef | ʾ |
| בּ | bet | b |
| ב | vet | v |
| גּ | gimel | g |
| ג | gimel spirant | ḡ |
| דּ | dalet | d |
| ד | dalet spirant | ḏ |
| ה | he | h |
| ו | vav | w |
| ז | zayin | z |
| ח | ḥet | ḥ |
| ט | tet | ṭ |
| י | yod | y |
| כּ | kaf | k |
| כ ך | khaf | kh |
| ל | lamed | l |
| מ ם | mem | m |
| נ ן | nun | n |
| ס | samekh | s |
| ע | ayin | ʿ |
| פּ | pe | p |
| פ ף | fe | f |
| צ ץ | tsadi | ṣ |
| ק | qof | q |
| ר | resh | r |
| שׁ | shin | š |
| שׂ | sin | ś |
| תּ | tav | t |
| ת | tav spirant | ṯ |
| ג׳ | gimel geresh | ğ |
| ז׳ | zayin geresh | ž |
| צ׳ | tsadi geresh | č |

## Vowels

| Sign | Name | Romanization |
|---|---|---|
| ◌ָ | qamats | å |
| ◌ַ | patah | a |
| ◌ֲ | hataf patah | a |
| ◌ֵ | tsere | e |
| ◌ֶ | segol | æ |
| ◌ֱ | hataf segol | œ |
| ◌ְ | sheva | ə |
| ◌ִ | hireq | i |
| ◌ֹ | holam | o |
| ◌ֻ | qubuts | u |

## The spirants, and how they were read

This column knows five spirants and no more: `ḇ` for bet, `ḡ` for gimel, `ḏ` for
dalet, `ḵ` for kaf, and `ṯ` for tav. **There is no pe spirant.** Five, not six.

Three of them stand alone in their row and are taken: `ḡ`, `ḏ` and `ṯ`. The other
two are printed as the second of a pair, `v, ḇ` and `kh, ḵ`, and this file takes
the first of each, so `ḇ` and `ḵ` appear nowhere in the table above.

That count matters here more than anywhere else in this repository. An earlier
version of this project put a six-member spirant set including a pe form into the
**SBL** scheme, where the SBL Handbook prints no spirants at all. The set was
invented. It is recorded here because the same characters are correct in this
scheme and were wrong in that one, and the difference is entirely a question of
which document is open.

The two channels disagreed about these cells, and the disagreement is itself the
finding:

- The **visual** channel at 900 dpi shows an unmistakable rule under the b, the
  d, the k and the t, and a rule **above** the g.
- The **programmatic** channel returns plain `b`, `d`, `k` and `t` with no
  combining mark at all, and returns `ḡ` U+1E21 for the gimel.

Both are right. The underlines are drawn vector rules rather than encoded
characters, which is why extraction cannot see them, and the gimel differs
because a precomposed g with macron exists in Unicode while a g with line below
does not, so the typesetter used the character for one row and drew the rule for
the other four.

This file encodes what the page means: the standard line-below forms `ḇ` U+1E07,
`ḏ` U+1E0F, `ḵ` U+1E35 and `ṯ` U+1E6F, and for gimel the macron-above `ḡ` U+1E21
that the document itself contains.

The visual channel also showed a rule under the lamed. That one is discarded:
lamed is not a begadkefat letter, it has no spirant, the programmatic channel
reads it as plain `l`, and no Semitic notation marks it. It is a stray rule.

## What the source prints, and what is chosen from it

Every row below prints several values. The first is taken, and taking the first
is a choice rather than a reading, so each is listed.

| Sign | Source prints | Chosen | Why |
|---|---|---|---|
| ב | `v, ḇ` | `v` | First listed. `ḇ` is available for anyone marking spirantization explicitly. |
| ט | `ṭ, t` | `ṭ` | First listed, and the one that keeps tet distinct from tav. |
| כ ך | `kh, ḵ` | `kh` | First listed. |
| פ ף | `p, f, ph` | **`f`** | **Not the first listed.** Taking `p` would make `פ` identical to `פּ`, collapsing two rows the source keeps apart. `f` is the value that preserves the distinction the row exists to make. |
| צ ץ | `ṣ, ẓ` | `ṣ` | First listed. |
| ק | `q, k` | `q` | First listed, and the one that keeps qof distinct from kaf. |
| שׂ | `ś, s` | `ś` | First listed, and the one that keeps sin distinct from samekh. |
| ◌ָ | `å, o, o̊ (short)` and `â, ā (long)` | `å` | First of the short set. See the caveat below. |
| ◌ֵ | `e, ẹ, ē` | `e` | First listed. |
| ◌ֶ | `æ, ä, ẹ` | `æ` | First listed. |
| ◌ֱ | `œ, ě, ᵉ` | `œ` | First listed. |
| ◌ְ | `ə, ě, e` | `ə` | First listed. Only sheva na is transliterated. |
| ◌ֻ | `u, ŭ` | `u` | First listed. |
| shuruq | `û, ū` | `û` | First listed. |
| ◌ֲ | `a, ᵃ` | `a` | First listed; the second is a raised a. |
| ◌ֹ | `o, o, o` | `o` | Three o-forms whose diacritics the extraction cannot separate; the first is bare. |

## Two values this file states that the column does not print

`tsere_male` is `e`. The Scientific column's tsere-yod row is **blank**; only the
General column fills it, with "ei; biblical e". The value here is therefore the
plain tsere value carried through to the sequence rather than a reading of the
row, which is the honest description of it.

`ə` is U+0259 LATIN SMALL LETTER SCHWA. The document's text stream holds U+04D9
CYRILLIC SMALL LETTER SCHWA, which is the same glyph and is almost certainly a
font substitution rather than a claim about Cyrillic. The Latin codepoint is what
this file uses, and the difference is recorded here rather than left to be
discovered.

## A caveat about using this on running text

The qamats row does not print a value. It prints a set conditioned on vowel
length: `å, o, o̊` for the short vowel and `â, ā` for the long one. Deciding which
applies needs a syllable analysis this tool performs only partially, so `å` is the
mainline and `romanize/rules.py` raises a flag whenever it meets a qamats it
cannot classify.

The honest summary is that this column was designed for a scholar setting one
word at a time with a grammar open, not for a machine setting a paragraph. It is
here because it is a published standard and because reading it is often the point,
and its output should be checked rather than trusted.

## What the source does not print

No hataf qamats row and no qamats qatan row, in either column. Fourteen vowel
rows were counted in both channels and neither is among them. Declared in
`source_gaps`; the engine flags rather than substitutes.

## Rules

- **Dagesh ḥazak doubles, except in `ש`.** Note 2.
- **An apostrophe separates vowels that are not a diphthong.** Note 1.
- **A double dagger marks a reconstructed form.** The last row of the table, whose
  Scientific value reads "reconstructed forms of words."
