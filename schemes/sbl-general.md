<!-- Generated from a two-channel reading of the source document: one
     programmatic extraction and one visual reading of the rendered pages,
     diffed cell by cell. See sources/manifest.md for the document, its URL,
     and its SHA-256. Edit this file to change the scheme; the code reads it. -->
---
name: sbl-general
citation: "SBL Handbook of Style, 2nd ed., §5.1.2 (general-purpose style)"
source: sbl-handbook.pdf
default: true
doubles: true
never_double: [ts, sh]
article_doubles: false
hyphenate_prefixes: true
always_mark_alef: false
shva_na: e
tsere_male: ei
hireq_male: i
holam_male: o
shuruq: u
qamats_he: ah
suffix_3ms: ayw
---

# SBL general-purpose

The default. Phonetic rather than reversible: no vowel length is marked at all,
and the digraphs `kh`, `ts`, `sh` are used. This is the style SBL intends for a
reader who will pronounce the Hebrew rather than reconstruct it.

## Consonants

| Letter | Name | Romanization |
|---|---|---|
| א | alef | ’ |
| בּ | bet | b |
| ב | vet | v |
| ג | gimel | g |
| ד | dalet | d |
| ה | he | h |
| ו | vav | v |
| ז | zayin | z |
| ח | ḥet | ḥ |
| ט | tet | t |
| י | yod | y |
| כּ | kaf | k |
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
| ת | tav | t |

## Vowels

| Sign | Name | Romanization |
|---|---|---|
| ◌ַ | patach | a |
| ◌ָ | qamats | a |
| ◌ׇ | qamats qatan | o |
| ◌ֶ | segol | e |
| ◌ֵ | tsere | e |
| ◌ִ | hireq | i |
| ◌ֹ | holam | o |
| ◌ֻ | qibbuts | u |
| ◌ֲ | hataf patach | a |
| ◌ֱ | hataf segol | e |
| ◌ֳ | hataf qamats | o |
| ◌ְ | vocal shewa | e |

## What the source prints, and what is chosen from it

SBL states several values as alternatives. Where it does, the choice made here is
recorded so it is a decision rather than an accident.

| Letter | Source prints | Chosen | Why |
|---|---|---|---|
| א | `’ or omit` | `’` | Written, not omitted. |
| ע | `‘ or omit` | `‘` | Written, not omitted. |
| ו | `v or w` | `v` | The style is a pronunciation aid, and modern Hebrew says v. `w` stays the academic style's letter, so the two SBL styles remain tellable apart at this row. |
| ח | `kh or h` | **`ḥ`** | **Deviation.** Both source options collapse ח into כ. `ḥ` is what SBL academic, ALA-LC, and both Encyclopaedia Judaica columns use. |
| ב ג ד כ פ ת | `b, v` · `g, gh` · `d, dh` · `k, kh` · `p, ph or f` · `t, th` | b/v, k/kh, p/f only | Note 3: in modern Hebrew the dagesh lene "generally affects the pronunciation of only bet, kaf, and pe." |
| tsere yod | `e` | **`ei`** | **Deviation**, following Encyclopaedia Judaica. |
| ◌ָ qamats | two rows, `a` at qamets and `o` at qamets khatuf, both signs encoded U+05B8 | `a` for U+05B8, `o` for U+05C7 | The source separates the rows by name rather than by codepoint; its own table encodes both signs as U+05B8. Unicode gives the qatan sign U+05C7, so this file keys the `o` row there, the way ALA-LC and BGN/PCGN split the same alternative, and `romanize.rules` decides by position for the U+05B8 that almost all real text uses. |
| שׂ | `s` | `s` | |

Two further deviations, both departures from the source rather than choices
within it: prefixes are hyphenated, where note 2 prints the unhyphenated
`Birkat Hatorah` with only the first letter capitalized, following ALA-LC
practice instead; and the definite article is written `ha-` with the name
keeping its capital.

## A hazard worth knowing

Aleph and ayin here are `’` U+2019 and `‘` U+2018, ordinary typographic quote
marks, because that is what the source prints. They are not the half rings
`ʾ` U+02BE and `ʿ` U+02BF that SBL's **academic** style uses. Verified twice: a
programmatic read of the codepoints, and a visual read at 4800 dpi that
described the academic marks as even-width arcs with squared terminals and the
general-purpose marks as comma-shaped with ball terminals.

The consequence is that a letter in this scheme is also a punctuation mark. It
collides with apostrophes in search, sorts unpredictably, and any smart-quote
processor in a publishing pipeline may rewrite it silently. If that becomes a
problem, changing the two rows above to the half rings is a one-line edit and
becomes a fifth documented deviation.

## Rules

- **Dagesh forte doubles.** Note 4 names exactly two exceptions, צ (`ts`) and שׁ (`sh`).
- **The definite article does not double the following consonant.** Note 2.
- **Maqqef becomes a hyphen.** §5.1.1.4 note 9.
- **Aramaic uses this same system.** §5.2, in full: "The systems described above
  for Hebrew are to be followed, even though tsere and holem are frequently not
  markers of long vowels in Aramaic."
