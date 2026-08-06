<!-- Generated from a two-channel reading of the source document: one
     programmatic extraction and one visual reading of the rendered pages,
     diffed cell by cell. See sources/manifest.md for the document, its URL,
     and its SHA-256. Edit this file to change the scheme; the code reads it. -->
---
name: ala-lc-yiddish
citation: "ALA-LC Romanization Table: Hebrew and Yiddish, Library of Congress (Yiddish column)"
source: ala-lc.pdf
script: yiddish
doubles: false
never_double: []
hyphenate_prefixes: false
always_mark_alef: false
shva_na: ""
---

# ALA-LC Yiddish

The same Library of Congress document that gives the ALA-LC Hebrew table also
gives a Yiddish one, in a second column of the same two grids. This file is that
column.

Its preamble: "For Yiddish, the table follows the standardized, principally
Lithuanian, pronunciation. In romanizing Yiddish, the etymology of the word is
ignored." That last sentence is the whole character of the scheme. A word of
Hebrew origin inside a Yiddish sentence is romanized as Yiddish speakers say it,
not as it would be romanized in a Hebrew text, which is why `ת` comes out as an
s sound here and a t sound in `ala-lc.md`.

## What this scheme is, and what it is not

It romanizes **Yiddish text**. It is the right choice for a Yiddish title, a
Yiddish quotation, or a catalogue record.

It is **not** a table for reading pointed Hebrew in Ashkenazi pronunciation.
Two of its values are facts about Yiddish spelling rather than about Ashkenazi
speech: bare `ב` is romanized `b` because Yiddish writes the v sound as `בֿ`, and
that has nothing to do with how an Ashkenazi reader pronounces a Hebrew word.

No published standard gives a romanization table for Ashkenazi Hebrew. That is
not an oversight in this repository; the tables were searched for and are not
there. ArtScroll and Feldheim have house practices and publish no tables, and the
Hebraica Cataloging Manual mentions Ashkenaz only as the surname of a
lexicographer of abbreviations. What exists is this scheme and `yivo.md`, both of
which romanize Yiddish, and whose treatment of words of Hebrew and Aramaic origin
is the closest published thing to Ashkenazi Hebrew.

For files already written in Ashkenazi forms, the tool's job is to leave them
alone. `romanize/register.py` detects the register and refuses to normalize it.

## Consonants

| Letter | Name | Romanization |
|---|---|---|
| א | shtumer alef | ʼ |
| ב בּ | beys | b |
| ג | giml | g |
| ד | daled | d |
| ה | hey | h |
| ו | vov | ṿ |
| װ | tsvey vovn | ṿ |
| ז | zayen | z |
| ח | khes | ḥ |
| ט | tes | ṭ |
| י | yud | y |
| כּ ךּ | kof | k |
| כ ך | khof | kh |
| ל | lamed | l |
| מ ם | mem | m |
| נ ן | nun | n |
| ס | samekh | s |
| ע | ayin | ʻ |
| פּ ףּ | pey | p |
| פ ף | fey | f |
| צ ץ | tsadek | ts |
| ק | kuf | ḳ |
| ר | reysh | r |
| שׁ | shin | sh |
| שׂ | sin | ś |
| תּ | tof | t |
| ת | sof | s̀ |

`ו` and `י` are romanized as consonants only. As vowels they belong to the table
below, and the engine tries that table first for a Yiddish scheme.

`א` and `ע` are printed here because the source prints them in its consonant
grid, which is shared between the two languages. In Yiddish both are vowel
carriers, so in practice the vowel-letters table takes them.

## Vowel letters

Yiddish writes most of its vowels as letters, sometimes with a point on top,
rather than as points under consonants. These are whole sequences, matched
longest first.

| Sign | Name | Romanization |
|---|---|---|
| אַ | pasekh alef | a |
| אָ | komets alef | o |
| ו, או | vov | u |
| וי, אוי, ױ, אױ | vov yud | oy |
| י, אי | yud | i |
| ע | ayin | e |
| ײַ, אײַ, ייַ, אייַ | pasekh tsvey yudn | ay |
| ײ, אײ, יי, איי | tsvey yudn | ey |

Each diphthong is listed in both encodings because real text uses both. `ױ` is
U+05F1 HEBREW LIGATURE YIDDISH VAV YOD and `ײ` is U+05F2 HEBREW LIGATURE YIDDISH
DOUBLE YOD; the same sounds are also written as two separate letters, and a
reader cannot tell which a file used.

## What the source prints, and what is chosen from it

| Sign | Source prints | Chosen | Why |
|---|---|---|---|
| א | `a or o` | `a` for אַ, `o` for אָ | The alternative is the pasekh and komets distinction, and the point is on the page. A bare `א` with no point is the shtumer alef and is silent. |
| ײ | `ay (if pronounced ai as in aisle), or ey (if pronounced ei as in weigh)` | `ay` for אײַ, `ey` for אײ | The two rows are printed with and without a pasekh under the double yod. Confirmed at 600 dpi: the ay row carries the stroke, the ey row does not. |
| ת | `t (in Yiddish, ṡ)` | `s̀` | See below. This one nearly went in wrong. |

## The one that nearly went in wrong

`ת` in Yiddish is **`s` followed by U+0300 COMBINING GRAVE ACCENT**, giving `s̀`.

The machine channel returned `t (in Yiddish, s)` with a combining character
stranded after the closing parenthesis, which reads exactly like an extraction
artifact worth discarding. The visual channel at 600 dpi showed an unmistakable
mark above the s but could not name it: a dot above and a grave above are hard to
tell apart in a sans face at that size. Reading the codepoint out of the text
stream settled it at U+0300.

Discarding it would have produced plain `s`, which is wrong in a way that matters
to this scheme specifically. ALA-LC needs three distinguishable s sounds to stay
reversible, and it has exactly three: `ס` samekh is plain `s`, `שׂ` sin takes an
acute `ś`, and `ת` in Yiddish takes a grave `s̀`. Collapsing the third into the
first would destroy the property the whole table is built for.

## Rules

- **Nothing doubles.** Carried over from the Hebrew column of the same document.
- **Etymology is ignored.** A word of Hebrew origin is romanized by its Yiddish
  pronunciation, so `שבת` is `shabes` rather than `shabat`.
- **The single prime.** "A single prime ( ʹ ) is placed between two letters
  representing two distinct consonantal sounds when the combination might
  otherwise be read as a digraph."

## A gap in the source

The source prints no row for `בֿ` beys with rafe, the ordinary Yiddish spelling of
the v sound, nor for `כֿ` or `פֿ`. Under this table a `בֿ` therefore romanizes as
`b`, which is wrong for any modern Yiddish text.

That is what the document prints, and this file does not invent the missing rows.
`yivo.md` covers them, and is the better choice for running Yiddish prose.
