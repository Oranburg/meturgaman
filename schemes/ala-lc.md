<!-- Generated from a two-channel reading of the source document: one
     programmatic extraction and one visual reading of the rendered pages,
     diffed cell by cell. See sources/manifest.md for the document, its URL,
     and its SHA-256. Edit this file to change the scheme; the code reads it. -->
---
name: ala-lc
citation: "ALA-LC Romanization Table: Hebrew and Yiddish, Library of Congress"
source: ala-lc.pdf
doubles: false
never_double: []
hyphenate_prefixes: true
always_mark_alef: false
shva_na: e
tsere_male: e
hireq_male: i
holam_male: o
shuruq: u
patah_male: ai
---

# ALA-LC

The cataloguing standard: what North American library catalogues use, and where
IJMES sends Hebrew authors. Use it when the result has to match a catalogue
record. Its preamble says it "approximates the modern Israeli, primarily
Sephardic, pronunciation."

## Consonants

| Letter | Name | Romanization |
|---|---|---|
| א | alef | ʼ |
| בּ | bet | b |
| ב | vet | v |
| ג | gimel | g |
| ד | dalet | d |
| ה | he | h |
| ו | vav | ṿ |
| װ | double vav | ṿ |
| ז | zayin | z |
| ח | ḥet | ḥ |
| ט | tet | ṭ |
| י | yod | y |
| כּ ךּ | kaf | k |
| כ ך | khaf | kh |
| ל | lamed | l |
| מ ם | mem | m |
| נ ן | nun | n |
| ס | samekh | s |
| ע | ayin | ʻ |
| פּ ףּ | pe | p |
| פ ף | fe | f |
| צ ץ | tsadi | ts |
| ק | qof | ḳ |
| ר | resh | r |
| שׁ | shin | sh |
| שׂ | sin | ś |
| ת תּ | tav | t |

ו and י are romanized **only when consonantal**; as matres they are carried by
the vowel. The source prints that condition itself, on the ו, װ and י rows.
The alef row instead prints an option, `ʼ (alif) or disregarded`, with no
positional condition attached; this scheme writes it.

The final forms ךּ and ףּ are the source's own, printed in parentheses on the
kaf and pe rows the way it prints every other final form. תּ has a row of its
own beside ת, both reading `t` in the Hebrew column, and װ has one too,
reading `ṿ (only if a consonant)` exactly as the ו row does.

## Vowels

| Sign | Name | Romanization |
|---|---|---|
| ◌ַ | patach | a |
| ◌ָ | qamats | a |
| ◌ׇ | qamats qatan | o |
| ◌ֶ | segol | e |
| ◌ֵ | tsere | e |
| ◌ִ | hiriq | i |
| ◌ֹ | holam | o |
| ◌ֻ | qubuts | u |
| ◌ְ | sheva | e |
| ◌ֲ | hataf patah | a |
| ◌ֱ | hataf segol | e |
| ◌ֳ | hataf qamats | o |

Vowel-plus-yod: segol yod `e`, **patah yod `ai`**, tsere yod `e`, hiriq yod `i`.
Vav with holam `o`, vav with dagesh `u`.

## What the source prints, and what is chosen from it

Two rows of the vowel table print an alternative rather than a value. A cell
reading "a or o" cannot be applied by a machine, so each is split across the two
Unicode signs the alternative is actually about, and the split is recorded here
rather than left to be inferred.

| Sign | Source prints | Chosen | Why |
|---|---|---|---|
| ◌ָ qamats | `a or o` | `a` for U+05B8, `o` for U+05C7 | The alternative is the gadol and qatan distinction, and Unicode gives those separate codepoints. Almost no text in the wild uses U+05C7, so `romanize.rules` decides the question by position and flags when it cannot. |
| ◌ְ sheva | `e or disregarded` | `e` when vocal, nothing when silent | Same distinction, and again positional. `shva_na: e` in the front matter carries the vocal value. |

Neither is a departure from the source. Both are the source's own alternative,
resolved by the criterion the source has in mind.

## Rules

- **Nothing doubles.** The Hebraica Cataloging Manual does not distinguish dagesh
  ḥazaḳ from dagesh ḳal, so gemination is not marked at all.
- **The single prime.** "A single prime ( ʹ ) is placed between two letters
  representing two distinct consonantal sounds when the combination might
  otherwise be read as a digraph": `hisʹhid` for הסהיד.
- **Supplying vowels is expected.** "In romanizing Hebrew, it is often necessary
  to consult dictionaries and other sources … primarily for the purpose of
  supplying vowels." The named authority is Even-Shoshan, *ha-Milon he-ḥadash*
  (Jerusalem: Ḳiryat-sefer, 1966-1970), with *Hebraica Cataloging* (Maher, 1987)
  for the detailed rules.
- **Diacritics are dot-below throughout**: ḥ, ṭ, ḳ, ṿ. Sin takes an **acute**, ś.

Alef is `ʼ` U+02BC MODIFIER LETTER APOSTROPHE and ayin is `ʻ` U+02BB MODIFIER
LETTER TURNED COMMA, read from the file. The visual channel confirmed the marks
are comma-shaped and mirrored rather than half rings, but noted it cannot
separate U+02BC from U+2019 by eye in this face.
