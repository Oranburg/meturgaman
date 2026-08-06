# The scheme files

One markdown file per romanization standard. The code reads these; nothing here
is generated from anything else, and no romanization table exists in Python
anywhere in this repository.

## Why they are documents

A table written in code is a table nobody proofreads. It gets edited to make a
test pass, it drifts from the standard it claims to implement, and the drift is
invisible because checking it means reading code.

This project shipped a spirant set that appears nowhere in the SBL Handbook. It
came from a summary of the source rather than from the source, it looked
entirely plausible, and it survived a rewrite because a second file had quietly
copied it. It was caught by someone opening the PDF.

Keeping the tables as documents means checking one is reading a page. It also
means each can carry its citation, and can say in prose where it departs from
its source and why.

## The format

```markdown
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
---

# SBL general-purpose

Prose saying what this scheme is for.

## Consonants

| Letter | Name | Romanization |
|---|---|---|
| בּ | bet | b |
| ב | vet | v |
| כ ך | khaf | kh |

## Vowels

| Sign | Name | Romanization |
|---|---|---|
| ◌ַ | patach | a |

## What the source prints, and what is chosen from it

| Letter | Source prints | Chosen | Why |
|---|---|---|---|
| א | `’ or omit` | `’` | Written, not omitted. |

## Rules

- **Maqqef becomes a hyphen.** §5.1.1.4 note 9.
```

### The Letter column

Read literally, character by character. Nothing declares whether a form carries a
dagesh; the loader looks.

- `בּ` on one row and `ב` on another gives the scheme its dagesh and plain values.
- `כ ך` in one cell, space separated, covers a letter and its final form.
- `שׁ` and `שׂ` are read as shin and sin by their dots.
- `בֿ` with a rafe is a separate value, which is how Yiddish marks its spirants.
- `ג׳` with a geresh is a borrowed sound.
- An empty Romanization cell means the source says not to write this letter,
  which is what Encyclopaedia Judaica's General column does with alef and ayin.

A letter with no separate dagesh row falls back to its plain value, which is the
scheme saying the letter sounds the same either way. SBL academic prints no
spirant rows at all, so every begadkefat letter falls back; SBL general prints
three, so three do not.

### The Vowels table

Keyed by the bare combining mark. The `◌` U+25CC is a dotted circle the mark is
drawn on so it is visible, and the loader strips it.

### Vowel letters and letter combinations

Only for Yiddish, which carries most of its vowels in letters rather than in
points. Keys are whole sequences, matched longest first, and a Sign cell may list
several separated by commas.

## The front matter keys

Required: `name` (must match the filename), `citation`, `source`.

Everything else is optional and has a stated default. An unknown key is an error
rather than something ignored, because the usual way to break a scheme is to
misspell a rule and never learn it had no effect.

| Key | Default | What it does |
|---|---|---|
| `default` | `false` | the scheme used when none is named. Exactly one file sets it |
| `script` | `hebrew` | `hebrew` or `yiddish` |
| `doubles` | `true` | dagesh forte written by doubling |
| `never_double` | `[]` | digraphs that never double |
| `article_doubles` | `true` | whether the definite article's dagesh is written |
| `hyphenate_prefixes` | `false` | `ha-melekh` |
| `join_and_capitalize_prefixes` | `false` | `haMmelekh`, the BGN treatment |
| `always_mark_alef` | `false` | write alef even initially and when quiescent |
| `shva_na` | `e` | how a vocal sheva is written. Empty means not written |
| `tsere_male` | `e` | tsere plus yod |
| `hireq_male` | `i` | hireq plus yod |
| `holam_male` | `o` | holam plus vav |
| `shuruq` | `u` | vav with dagesh |
| `patah_male` | `""` | patah plus yod. Only ALA-LC prints one |
| `qamats_he` | `""` | word-final qamats plus he |
| `suffix_3ms` | `""` | word-final qamats, yod, vav |
| `maqaf` | `-` | what a maqaf becomes |
| `source_gaps` | `[]` | vowel points the source does not print at all |

`source_gaps` deserves a word. Encyclopaedia Judaica prints no hataf qamats row
and no qamats qatan row: fourteen vowel rows were counted in both channels and
neither is among them. Declaring the gap is what separates "the source does not
have this" from "the row was missed", and it makes the engine raise a flag rather
than borrow a value from a different standard.

## Adding a ninth scheme

1. **Get the source.** A published document, with a URL. Add it to
   `sources/manifest.md` with its SHA-256 and its rights status, and add the fetch
   to `tools/fetch_sources.py` if it needs one.

2. **Extract it twice, by different means.** Once programmatically, once by
   reading the rendered pages. Diff them cell by cell. This is not ceremony:

   - The Encyclopaedia Judaica PDF uses a custom font encoding, so its Hebrew
     letters extract as Latin characters. Alef comes out as `ý` and ayin as `ď`.
   - The same document draws its spirant underlines as vector rules rather than
     encoding them, so extraction reads `b` where the page shows `ḇ`.
   - ALA-LC's Yiddish tav is `s` plus U+0300, and the combining mark lands after
     the closing parenthesis in extraction, looking exactly like an artifact
     worth discarding. Discarding it would have collapsed three distinct s
     sounds into two.
   - `pdftotext` emits precomposed diacritics decomposed, so searching for `ḥ`
     U+1E25 finds nothing in a document plainly full of it unless both sides are
     normalized to NFC first.

   Where the channels disagree, neither wins automatically. The programmatic
   channel is authoritative about which codepoint a character is; the visual
   channel is authoritative about whether a mark is on the page at all.

3. **Write the file.** Record every choice in the "What the source prints"
   section. A cell reading `a or o` cannot be applied by a machine, so say which
   you took and why.

4. **Run the tests.**

   ```
   pytest tests/test_schemes.py tests/test_source_fidelity.py
   ```

   `test_every_value_appears_in_its_source` will fail on any character your
   source does not contain. If the character is genuinely there but not
   extractable, add it to `_NOT_EXTRACTABLE` in that file with the reason. That
   list is checked for staleness, so an excuse cannot outlive its evidence.

5. **Check the round trip.** `test_each_scheme_is_recognizable_from_its_own_output`
   romanizes a phrase under your scheme and works out which scheme it was. If it
   fails, your scheme is indistinguishable from another, which is worth knowing.

## What not to do

Do not add a value because it looks right, or because another scheme has it, or
because a summary of the standard said so. Open the document.
