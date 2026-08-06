<!-- Generated from a two-channel reading of the source document: one
     programmatic parse of the page HTML and one independent extraction through
     a different renderer, diffed cell by cell. All forty-two rows agreed.
     See sources/manifest.md for the document, its URL, and its SHA-256.
     Edit this file to change the scheme; the code reads it. -->
---
name: yivo
citation: "YIVO Institute for Jewish Research, Yiddish Alef-beys, yivo.org/Yiddish-Alphabet"
source: yivo-alphabet.html
script: yiddish
doubles: false
never_double: []
hyphenate_prefixes: false
always_mark_alef: false
shva_na: ""
---

# YIVO

The standard romanization for Yiddish, from the institute that standardized the
orthography. This is what Yiddish scholarship uses, what libraries increasingly
use, and what a reader of *In geveb* or a YIVO catalogue is looking at.

It is a phonetic system for Yiddish and it does not preserve Hebrew etymology.
`ח` and `כ` are both `kh`; `ק` and `כּ` are both `k`; `ס`, `שׂ` and `ת` are all `s`.
A word cannot be spelled back into Hebrew letters from its YIVO romanization, and
that is by design rather than by oversight.

## Why this is the Ashkenazi table

Yiddish pronunciation of words from the Hebrew and Aramaic component, the
*loshn-koydesh* layer, is Ashkenazi Hebrew pronunciation. That is what makes this
the closest published thing to the table that does not exist.

The tav is the clearest case. `תּ` with its dagesh is `t` and bare `ת` is `s`, which
is what gives Shabbos rather than Shabbat, Akeidas rather than Akeidat, and
Bereishis rather than Bereishit. `אָ` komets alef is `o`, which is the other half
of Shabbos. Between them those two rows produce most of what an Ashkenazi
spelling looks like.

What this scheme cannot do is take pointed Hebrew and read it aloud in Ashkenazi
register, because it romanizes Yiddish spelling rather than Hebrew pointing. For
files already written in Ashkenazi forms, the tool's job is to leave them alone,
and `romanize/register.py` is what refuses to normalize them.

## Consonants

| Letter | Name | Romanization |
|---|---|---|
| א | shtumer alef | |
| ב | beys | b |
| בֿ | veys | v |
| ג | giml | g |
| ד | daled | d |
| ה | hey | h |
| ו | vov | u |
| וּ | melupm vov | u |
| ז | zayen | z |
| ח | khes | kh |
| ט | tes | t |
| י | yud | y |
| כּ | kof | k |
| כ ך | khof | kh |
| ל | lamed | l |
| מ ם | mem | m |
| נ ן | nun | n |
| ס | samekh | s |
| ע | ayen | e |
| פּ | pey | p |
| פֿ | fey | f |
| ף | langer fey | f |
| צ ץ | tsadek | ts |
| ק | kuf | k |
| ר | reysh | r |
| ש | shin | sh |
| שׂ | sin | s |
| תּ | tof | t |
| ת | sof | s |

**`ש` is written bare.** YIVO spells shin with no dot and marks only sin, `שׂ`,
which is the reverse of the Hebrew convention where both carry a dot. A scheme
file records what its source prints, so there is no shin-dot row here.

## Vowel letters

| Sign | Name | Romanization |
|---|---|---|
| אַ | pasekh alef | a |
| אָ | komets alef | o |
| יִ | khirik yud | i |

## Letter combinations

| Sign | Name | Romanization |
|---|---|---|
| וו | tsvey vovn | v |
| װ | tsvey vovn ligature | v |
| זש | zayen shin | zh |
| דזש | daled zayen shin | dzh |
| טש | tes shin | tsh |
| וי | vov yud | oy |
| ױ | vov yud ligature | oy |
| יי | tsvey yudn | ey |
| ײ | tsvey yudn ligature | ey |
| ײַ | pasekh tsvey yudn | ay |
| ייַ | pasekh tsvey yudn spelled out | ay |

## How the source's one table became three here

YIVO prints two tables, an alphabet of thirty-five rows and seven letter
combinations. This file holds three, and the regrouping is mechanical rather than
interpretive.

`אַ` pasekh alef and `אָ` komets alef are letters carrying a vowel point, and both
sit on the same letter. A consonant table keyed by letter would have `א` meaning
three different things at once, so those two rows moved to their own table where
the key is the whole sequence. Nothing else moved, and no value changed.

The ligature spellings `װ`, `ױ` and `ײ` are added alongside the two-letter
spellings the source prints. They are the same sequences encoded as single
codepoints, real text uses both, and a file gives no clue which its author chose.
This is an addition to the source's coverage rather than a change to its values.

## What this scheme does not carry

Every letter in Yiddish also works as a vowel or a consonant depending on where it
sits, and YIVO's own table shows this by giving `י` yud two values, `y` and `i`.
Only `y` is in the consonant table. `יִ` khirik yud, which is the spelling used
when the vowel reading has to be made explicit, is in the vowel-letter table. A
bare `י` is decided by position: it is the consonant when it opens a syllable and
the vowel `i` otherwise.

The source gives no vowel points beyond pasekh and komets, because Yiddish does
not use them. A Hebrew word quoted inside a Yiddish text keeps its Yiddish
pronunciation under this scheme, per the rule that etymology is ignored.

## Rules

- **Nothing doubles.** YIVO marks no gemination.
- **`א` alone is silent.** The source gives its romanization as N/A. It carries
  a vowel or separates one from another, and is written only through the
  sequences above.
- **Etymology is ignored.** A word of Hebrew origin is romanized as Yiddish
  speakers say it: `שבת` is `shabes`, not `shabat`.
