<!-- Generated from a two-channel reading of the source document: one
     programmatic extraction and one visual reading of the rendered pages,
     diffed cell by cell. See sources/manifest.md for the document, its URL,
     and its SHA-256. Edit this file to change the scheme; the code reads it. -->
---
name: encyclopaedia-judaica-general
citation: "Encyclopaedia Judaica, 2nd ed. (2007), vol. 1, p. 197, Transliteration Rules, General column"
source: encyclopaedia-judaica.pdf
doubles: true
never_double: [sh]
hyphenate_prefixes: false
always_mark_alef: false
shva_na: e
tsere_male: ei
hireq_male: i
holam_male: o
shuruq: u
source_gaps: [hataf_qamats, qamats_qatan]
---

# Encyclopaedia Judaica, General

The house style of the standard English-language Jewish reference work, and the
one most likely to match how a Jewish Studies reader already expects to see a
Hebrew word spelled. It is a pronunciation aid rather than a reversible notation:
alef and ayin go unwritten, vowel length goes unmarked, and `ei` is used where
most other schemes print `e`.

The page prints two columns, General and Scientific, and this file is the first
of them. `encyclopaedia-judaica-scientific.md` is the second.

## Consonants

| Letter | Name | Romanization |
|---|---|---|
| א | alef | |
| בּ | bet | b |
| ב | vet | v |
| ג גּ | gimel | g |
| ד דּ | dalet | d |
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
| ע | ayin | |
| פּ | pe | p |
| פ ף | fe | f |
| צ ץ | tsadi | ẓ |
| ק | qof | k |
| ר | resh | r |
| שׁ | shin | sh |
| שׂ | sin | s |
| ת תּ | tav | t |
| ג׳ | gimel geresh | dzh |
| ז׳ | zayin geresh | zh |
| צ׳ | tsadi geresh | ch |

Two rows are deliberately empty. Note 1 reads, in full: "The letters א and ע are
not transliterated. An apostrophe (’) between vowels indicates that they do not
form a diphthong and are to be pronounced separately."

`ו` is `v` "when not a vowel", and `י` is `y` "when vowel and at end of words, i".
Both conditions are decided by `romanize/rules.py`, which flags rather than
guesses when the position is genuinely ambiguous.

## Vowels

| Sign | Name | Romanization |
|---|---|---|
| ◌ָ | qamats | a |
| ◌ַ | patah | a |
| ◌ֲ | hataf patah | a |
| ◌ֵ | tsere | e |
| ◌ֶ | segol | e |
| ◌ֱ | hataf segol | e |
| ◌ְ | sheva | e |
| ◌ִ | hireq | i |
| ◌ֹ | holam | o |
| ◌ֻ | qubuts | u |

Tsere yod is `ei`, and this is the source SBL general borrows that value from.
Biblical `e` is the alternative the source names for the same sign.

## What the source prints, and what is chosen from it

The vowel grid prints each General value once, vertically centred across the rows
it covers, and leaves the covered rows blank. Reading a blank as "no value" would
lose two thirds of the vowels, so the spans are read as spans.

| Rows covered | Value printed | Read as |
|---|---|---|
| qamats, patah, hataf patah | `a`, printed at the patah row | all three are `a` |
| tsere, segol, hataf segol | `e`, printed at the segol row | all three are `e` |
| hireq, hireq yod | `i` | both are `i` |
| holam, holam vav | `o` | both are `o` |
| qubuts, shuruq | `u` | both are `u` |

Confirmed in both channels. The visual read at 1200 dpi of the sign column alone
counted fourteen vowel rows and identified each point; the programmatic read
returned the same fourteen in the same order, with the General column blank on
exactly the rows the visual read shows blank.

The sheva row sits outside those spans, and its `e` is chosen rather than
printed. Its General cell contains only "only *sheva na* is transliterated",
which says when the sign is written and never says what it is written as, and
the `e` above it belongs to the segol span. The Scientific column beside it
prints `ə, ě, e` for the same sign, so `e` is the one value the page itself
offers that the General column's plain alphabet can carry, and it is what
`shva_na` in the front matter and the sheva row of the vowel table record.

The consonant grid leans on blanks the same way, three times. ג, ד and ת each
print two rows, the dotted form and the spirant; the General column prints its
value on the dotted row and leaves the spirant row blank, while the Scientific
column fills both, `g` against `ḡ` and so on. Read by the letter of
`schemes/README.md`, an empty cell means the letter is not written, which is
what the alef and ayin cells mean; here the blank is read as a span instead,
the printed value covering both forms, and that reading is what the merged
ג גּ, ד דּ and ת תּ rows of the consonant table above carry.

## What the source does not print

**There is no hataf qamats row, and no qamats qatan row.** Fourteen vowel rows
were counted in both channels and neither point is among them. The engine
therefore refuses rather than borrowing `o` from a neighbouring scheme, which is
what `source_gaps` in the front matter declares.

`ק` and `כּ` are both `k`, so this scheme cannot be reversed at that letter. That
is a property of the source, not a defect in the reading.

## Rules

- **Dagesh ḥazak doubles, except in `ש`.** Note 2, in full: "Dagesh ḥazak (forte)
  is indicated by doubling of the letter, except for the letter ש."
- **An apostrophe separates vowels that are not a diphthong.** Note 1.
- **Names follow other authorities.** Note 3: biblical names and biblical place
  names follow the Jewish Publication Society translation; post-biblical Hebrew
  names are transliterated; contemporary names are "transliterated or rendered as
  used by the person"; and "names and some words with an accepted English form
  are usually not transliterated."
