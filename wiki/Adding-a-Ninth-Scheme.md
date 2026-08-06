The schemes are documents, and the integrity claim of the whole project is
that every table value was read off a published page. Adding a standard means
extending that claim, so the recipe is mostly about provenance.

## 1. Record the source before touching the table

Add an entry to `sources/manifest.md`: the document's title, URL, byte count,
and SHA-256. Run `python -m tools.fetch_sources` and confirm the document
fetches and verifies. If the document is copyrighted, that is fine; the file
stays out of git and only the provenance is committed.

## 2. Read the table through two channels

Extract the text programmatically (`pdftotext`, NFC-normalized) and read the
rendered pages visually. Diff the two, cell by cell. The channels disagree
more often than you would expect: this project has met a PDF whose Hebrew
extracts as Latin garbage, spirant underlines drawn as vector rules rather
than characters, vowel glyphs that all extract as the same mark, and a
combining grave that lands after the wrong character in extraction. Where
the channels disagree, say which one you trusted and why, in the file.

## 3. Write the scheme file

One markdown file in `schemes/`, following `schemes/README.md` for the
format. It needs the provenance comment at the top (how the table was
extracted, pointing at `sources/manifest.md`), YAML frontmatter with the
citation and the rule settings, the consonant and vowel grids, and a section
recording every place the file departs from what its source prints and why.
An empty cell means "not written"; if you read a blank as a span or choose
one of two printed alternatives, disclose the choice.

The one absolute rule: **never add a row the source does not print, however
convenient it would be for one word's output.** This project once carried an
invented row that existed to make a single word come out right, and the file
asserted two lines later that nothing had been changed. If an output looks
wrong under a correct table, the fix belongs in `meturgaman/romanize/rules.py`
or in `rules/*.md`, never in a fabricated table value.

## 4. Let the tests hold you to it

```
.venv/bin/python -m pytest -q tests/test_schemes.py tests/test_source_fidelity.py
```

`test_schemes.py` checks structure: every letter defined, no Hebrew leaking
through the engine, exactly one default, a provenance comment pointing at the
manifest. `test_source_fidelity.py` re-extracts the source document and
checks table values against it; if your file needs an exception (a value the
two channels genuinely disagree on), the exception list requires a stated
reason, and the reason must be true.

## 5. Try it on real text

Fetch whole chapters and romanize them under the new scheme; the stress that
finds bugs is real fetched text, never hand-typed examples. Watch the flags:
`source-gap` firing on common characters means the table is missing rows the
source actually prints.
