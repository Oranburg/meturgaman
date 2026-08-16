<!-- Generated from a two-channel reading of the source document: one
     programmatic extraction and one visual reading of the rendered pages,
     diffed cell by cell. See sources/manifest.md for the document, its URL,
     and its SHA-256. Edit this file to change the scheme; the code reads it. -->
---
name: sbl-academic
citation: "SBL Handbook of Style, 2nd ed., §5.1.1 (academic style)"
source: sbl-handbook.pdf
doubles: true
never_double: []
hyphenate_prefixes: false
always_mark_alef: true
shva_na: "ǝ"
tsere_male: "ê"
hireq_male: "î"
holam_male: "ô"
shuruq: "û"
qamats_he: "â"
suffix_3ms: "āyw"
---

# SBL academic

Fully reversible: the Hebrew can be reconstructed from the Latin. Vowel length
is marked with macrons and circumflexes. Use it when the romanization is itself
the object of study rather than a pronunciation aid.

## Consonants

| Letter | Name | Romanization |
|---|---|---|
| א | alef | ʾ |
| ב | bet | b |
| ג | gimel | g |
| ד | dalet | d |
| ה | he | h |
| ו | vav | w |
| ז | zayin | z |
| ח | ḥet | ḥ |
| ט | tet | ṭ |
| י | yod | y |
| כ ך | kaf | k |
| ל | lamed | l |
| מ ם | mem | m |
| נ ן | nun | n |
| ס | samekh | s |
| ע | ayin | ʿ |
| פ ף | pe | p |
| צ ץ | tsadi | ṣ |
| ק | qof | q |
| ר | resh | r |
| שׂ | sin | ś |
| שׁ | shin | š |
| ת | tav | t |

**No spirant forms are printed.** §5.1.1.1 lists b, g, d, k, p, t bare, and note
4 says not to indicate begadkepat spirantization unless it matters to the
discussion, showing exceptions by underlining the consonant instead. The
machine channel confirmed the underline in the printed example is a drawn vector
stroke matching the `t` bounding box, not the character ṯ.

## Vowels

| Sign | Name | Romanization |
|---|---|---|
| ◌ַ | patach | a |
| ◌ָ | qamats | ā |
| ◌ׇ | qamats khatuf | o |
| ◌ֶ | segol | e |
| ◌ֵ | tsere | ē |
| ◌ִ | short hireq | i |
| ◌ֹ | holem | ō |
| ◌ֻ | short qibbuts | u |
| ◌ֲ | khatef patakh | ă |
| ◌ֱ | khatef segol | ĕ |
| ◌ֳ | khatef qamets | ŏ |
| ◌ְ | vocal shewa | ǝ |

Matres and long forms: final qamets he `â`, tsere yod `ê`, segol yod `ê`, long
hireq `ī`, hireq yod `î`, full holem `ô`, long qibbuts `ū`, shureq `û`, 3ms
suffix `āyw`.

Vocal shewa is **`ǝ` U+01DD LATIN SMALL LETTER TURNED E**, not U+0259 SCHWA. The
two are the same shape in an italic serif; the visual channel said so and
deferred, and the machine channel read the codepoint from the file.

## What the source prints, and what is chosen from it

| Sign | Source prints | Chosen | Why |
|---|---|---|---|
| ◌ָ qamats | two rows, `ā` at qamets and `o` at qamets khatuf, both signs encoded U+05B8 | `ā` for U+05B8, `o` for U+05C7 | The source separates the rows by name rather than by codepoint; its own table encodes both signs as U+05B8. Unicode gives the qatan sign U+05C7, so this file keys the `o` row there, the way ALA-LC and BGN/PCGN split the same alternative, and `romanize.rules` decides by position for the U+05B8 that almost all real text uses. |

## Rules

- **Note 2: always transliterate quiescent aleph.** `lōʾ`, `hûʾ`, `rōʾš`, Aramaic `malkāʾ`.
- **Note 5: dagesh forte doubles; a euphonic dagesh does not.** No ts/sh exception is stated here; that is the general-purpose style's note 4.
- **Note 6: a silent shewa is not transliterated**, including the second of two at a word's end.
- **Note 8: do not capitalize transliterated proper names**, except at the start of a sentence.
- **Note 9: maqqef becomes a hyphen.**
