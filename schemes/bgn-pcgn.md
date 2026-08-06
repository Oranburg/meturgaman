<!-- Generated from a two-channel reading of the source document: one
     programmatic extraction and one visual reading of the rendered pages,
     diffed cell by cell. See sources/manifest.md for the document, its URL,
     and its SHA-256. Edit this file to change the scheme; the code reads it. -->
---
name: bgn-pcgn
citation: "BGN/PCGN 2018 Agreement, Romanization of Hebrew, codifying the Academy of the Hebrew Language 2006 and 2011 systems"
source: bgn-pcgn.pdf
doubles: true
never_double: [sh, ts]
hyphenate_prefixes: false
join_and_capitalize_prefixes: true
always_mark_alef: false
shva_na: e
tsere_male: e
hireq_male: i
holam_male: o
shuruq: u
---

# BGN/PCGN

Adopted jointly by the BGN and the PCGN in 2018, and based on the Academy of
the Hebrew Language's 2006 and 2011 transliteration systems, which is all the
source says about its own standing. It is also the source of the determination
rules the other schemes rely on. Every row of its consonant tables prints an
explicit Unicode value, which removes all ambiguity about which character is
meant there; the fifteen-row vowel table prints no Unicode column, so its signs
rest on the visual channel described below.

## Consonants

| Letter | Name | Romanization |
|---|---|---|
| א | alef | ’ |
| בּ | bet | b |
| ב | vet | v |
| ג גּ | gimel | g |
| ד דּ | dalet | d |
| ה | he | h |
| ו | vav | v |
| ז | zayin | z |
| ח | ḥet | ẖ |
| ט | tet | t |
| י | yod | y |
| כּ ךּ | kaf | k |
| כ ך | khaf | kh |
| ל | lamed | l |
| מ ם | mem | m |
| נ ן | nun | n |
| ס | samekh | s |
| ע | ayin | ‘ |
| פּ | pe | p |
| פ ף | fe | f |
| צ ץ | tsadi | ts |
| ק | qof | q |
| ר | resh | r |
| שׁ | shin | sh |
| שׂ | sin | s |
| ת תּ | tav | t |
| ג׳ | gimel geresh | ǧ |
| ז׳ | zayin geresh | ž |
| צ׳ | tsadi geresh | č |

The three geresh rows are the source's rows 27 to 29, printed on page 3 as a
small second consonant table with its own Unicode column: 05D2+05F3/01E7,
05D6+05F3/017E, 05E6+05F3/010D. The source's remark on them: they are used on
Israeli maps to render Arabic and other non-Hebrew names, and names in which
they occur should be romanized in accordance with its notes 7 and 8.

**ח is `ẖ` U+1E96, h with a LINE below**, not the dot-below `ḥ` that SBL and
ALA-LC use. The printed Unicode column says 1E96 and the glyph matches. The same
document uses dot-below `ḥ` in note 8a, but only for Arabic ح written in Hebrew
script, which is a different job.

ה is not romanized in word-final position unless it carries mappiq.

## Vowels

| Sign | Name | Romanization |
|---|---|---|
| ◌ַ | patah | a |
| ◌ָ | qamats | a |
| ◌ׇ | qamats qatan | o |
| ◌ֶ | segol | e |
| ◌ֵ | tsere | e |
| ◌ִ | hiriq | i |
| ◌ֹ | holam | o |
| ◌ֻ | qubuts | u |
| ◌ְ | shva | e |
| ◌ֲ | hataf patah | a |
| ◌ֱ | hataf segol | e |
| ◌ֳ | hataf qamats | o |

The vowel glyphs in this PDF are unreadable by extraction, every one decoding as
patah because of a broken font encoding; these rows come from the visual channel.
The romanization column extracts cleanly and agrees with it, with one caution:
the text layer carries `aa` on the patah rows and `uu` on the qubuts rows, and
the rendered page prints neither. Rows 1 and 2 share a single printed `a` and
rows 14 and 15 share a single printed `u`; the doubled strings sit clipped
outside the visible cells, text-layer artifacts rather than values.

## What the source prints, and what is chosen from it

| Sign | Source prints | Chosen | Why |
|---|---|---|---|
| ◌ָ qamats | `a, o`, remarked "Usually a; very rarely o." | `a` for U+05B8, `o` for U+05C7 | The alternative is the gadol and qatan distinction, which Unicode gives separate codepoints. "Very rarely o" is the source's own statement that `a` is the mainline. |
| ◌ְ shva | `e, or not romanized`, see note 3 | `e` when vocal, nothing when silent | Positional, and note 3 is about exactly that position. |

## Rules

- **Note 2, the dagesh.** The strong dagesh doubles the letter, and **sh and ts
  are not doubled**. It is distinguishable from the weak dagesh because "the
  former is always preceded by a vowel character": `עַכּוֹ → ‘Akko` but `כַּרְכֹּם → Karkom`.
  The weak dagesh is not marked for ג, ד, or ת, whose phonetic distinction "has
  now been lost."
- **Note 3, the shva.** First consonant is always shva na‘, romanized `e` where
  sounded. Last consonant is always shva naẖ, not romanized. Medial requires
  reducing to the elementary form: singular, unprefixed, unsuffixed for nouns.
  If the elementary form keeps the shva it is naẖ. When in doubt, write `e`.
- **Note 4, prefixes are joined and capitalized**, not hyphenated:
  `HaAgudda LeQiddum HaH̱innuk BeYafo`, `Bet WITSO LeTippul BeEm UVeYeled`. Where
  the following letter bears a dagesh the Roman letter is capitalized but **not**
  doubled: `HaYogev`.
- **Note 5, furtive patach is written before** the ח, ע, or mappiq-ה it sits
  under: `רוֹקֵחַ → Roqeaẖ`.
- **Note 6b, pronounceable acronyms are written as words**: `רמב״ם → Rambam`,
  `גבעת כ״ח → Giv‘at Koaẖ`.

Alef is `’` U+2019 and ayin is `‘` U+2018, printed in the table's own Unicode
column and confirmed visually as mirrored comma-shaped marks.
