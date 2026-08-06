# Meturgaman

Fetch Hebrew, Aramaic and Yiddish primary sources, romanize them under any of
eight published standards, and hear them read aloud.

A *meturgaman* is the person who stood beside the reader and rendered the text
for the congregation. This does that job: it retrieves the source, says which
edition it came from, and renders it into Latin letters under a standard that is
named rather than assumed.

```
pip install -e .

meturgaman text "Berakhot 2a"                 # a passage, in every edition
meturgaman topics charity                     # find a subject
meturgaman sources tzedakah --text            # what the tradition says about it
meturgaman romanize "כָּל־הָאָרֶץ"              # kol-ha-’arets
meturgaman audio "Genesis 1:1"                # chanted, by a person
```

## The one idea this is built around

Every romanization table lives in `schemes/`, as markdown, one file per standard.
No table is written in Python anywhere in this repository.

That is not a stylistic preference. A table written in code is a table nobody
proofreads: it gets edited to make a test pass, it drifts from the standard it
claims to implement, and the drift is invisible because checking it means reading
code. This project shipped a set of spirant characters that appear nowhere in the
SBL Handbook, and they survived a rewrite because a second file had quietly
copied them. They were caught by someone opening the PDF.

So the tables are documents. Each one carries its citation, its grid, and a
section recording every place it departs from what its source prints and why. A
test re-extracts each source and checks every character against it. When the
output looks wrong, you read one page.

## The eight schemes

| Scheme | Source | Use it when |
|---|---|---|
| `sbl-general` | SBL Handbook 2nd ed. §5.1.2 | general scholarly writing. **The default.** |
| `sbl-academic` | SBL Handbook 2nd ed. §5.1.1 | the romanization must be reversible |
| `ala-lc` | ALA-LC, Library of Congress | the result must match a catalogue record |
| `bgn-pcgn` | BGN/PCGN 2018 Agreement | Israeli place names, or anything official |
| `encyclopaedia-judaica-general` | EJ 2nd ed. vol. 1 p. 197 | matching how a Jewish Studies reader expects a word to look |
| `encyclopaedia-judaica-scientific` | EJ 2nd ed. vol. 1 p. 197 | comparative Semitics. Check its output |
| `yivo` | YIVO Institute | Yiddish, and the closest published thing to Ashkenazi Hebrew |
| `ala-lc-yiddish` | ALA-LC, Yiddish column | Yiddish for a catalogue record |

```
meturgaman schemes                # all eight with their sources
meturgaman schemes --name yivo    # one in full, table and reasoning
```

### About Ashkenazi

There is no published romanization table for Ashkenazi Hebrew. Not one that
could not be found: one that does not exist. ArtScroll and Feldheim have house
practices and publish no tables, and the Library of Congress's *Hebraica
Cataloging* manual mentions Ashkenaz only as the surname of a lexicographer.

What exists is Yiddish. YIVO's treatment of the *loshn-koydesh* layer, the words
of Hebrew and Aramaic origin, is Ashkenazi Hebrew pronunciation: `תּ` is `t` and
bare `ת` is `s`, which is what gives Shabbos rather than Shabbat. That is real,
published, and in `schemes/yivo.md`.

What the tool will not do is rewrite your Ashkenazi spelling into Sephardi. It
refuses and shows its evidence:

```
$ meturgaman romanize "Shabbos and halachah and Sukkos and mitzvos"
refused: This text is written in Ashkenazi register (ashkenazi 14, sephardi 0),
and sbl-general would rewrite it as Sephardi. That is a change of the author's
usage rather than a correction.
```

## Flags, and why they matter more than the output

Hebrew orthography is genuinely ambiguous in four places, and each of them has
one mark doing two jobs: a dagesh is lene or forte, a sheva is vocal or silent, a
qamats is long or short, a vav is a consonant or half a vowel.

The engine decides these in a pass of their own, in the open. **Where the rules
cannot settle a question, it raises a flag rather than picking a default and
staying quiet.** Output goes to stdout, flags to stderr.

```
$ meturgaman romanize "חָכְמָה"
ḥokhmah
  [qamats-qatan-assumed] (חָכְמָה) qamats before a silent sheva read as short (o).
  A meteg on the qamats would make it long (a); this edition has none here.
```

That flag is doing real work. `חָכְמָה` is *ḥokhmah* and `שָֽׁמְרָה` is *shamrah*,
and the two are written alike apart from a meteg. With the meteg present the tool
reads it and says nothing. Without it, the tool tells you what it assumed.

The Library of Congress reaches the same conclusion from the cataloguing side:
its manual sends cataloguers to a dictionary "primarily to distinguish schwa naʻ
from schwa nah, a matter which has significant impact on romanization." Code that
answers from orthography alone should say when it is unsure.

## What the tradition says about a subject

Sefaria has a curated topic ontology, which beats full-text search for anything
anyone has thought about before.

```
$ meturgaman topics lending
lending    Lending

$ meturgaman sources lending
Exodus 22:24
Deuteronomy 15:3
Bava Metzia 75a:3-75b:12
Ramban on Exodus 22:24:1
Sefer HaChinukh 67:1
Mishneh Torah, Creditor and Debtor 2:7
```

Add `--text` to fetch each passage, in Hebrew and English, with its edition.

## Every source carries its edition and its licence

```
$ meturgaman text "Genesis 1:1" --version all
Genesis 1:1
8 editions, 5 independent witnesses
providers: he.wikisource.org, tanach.us, jps.org, sefaria.org, chabad.org
```

Five witnesses from eight editions, because three of them came from the same
digitization. An edition's provider is derived from its own stated source rather
than from the fact that Sefaria served it, so two rows that came from one place
do not count as two.

## Hearing it

Two paths, and the tool says which one you are getting.

**Recorded cantillation.** Sefaria carries PocketTorah's recordings: a person
chanting, with the trope, CC-BY-SA, timestamped to the verse. Torah only.

**Synthetic speech.** macOS ships the `Carmit` voice. Offline, free, reads
anything including Aramaic, and needs pointed text to be worth listening to.

```
meturgaman audio "Genesis 1:1"           # the recording
meturgaman audio "Berakhot 2a" --synth   # nobody has recorded the Talmud
```

## What it reads

**Sefaria**, for texts, editions, topics, search, dictionaries, commentaries,
sugya boundaries and the daily calendar. No key, no registration.

**Hebcal**, for the calendar, Torah readings, halachic times and yahrzeits.
Its `--register` option takes any of twenty-two locales, seven of them Ashkenazi.

**Dicta**, optionally and locally, for adding vowel points. Their models are on
HuggingFace under a permissive licence and run on your own machine. They publish
no API contract, so this project does not call one.

Both APIs' contracts are committed under `docs/api/`, so the code is written
against a recorded spec rather than against anyone's memory of one.

## Installing

```
git clone https://github.com/Oranburg/meturgaman.git
cd meturgaman
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m tools.fetch_sources    # the source documents, verified by hash
.venv/bin/python -m pytest -m "not network"
```

Python 3.11 or later. The core has no dependencies at all: both services are
keyless JSON over HTTPS, and `urllib` does that.

Optional extras: `pip install -e ".[dicta]"` for local vocalization.

## The agent

`skills/meturgaman/SKILL.md` works on claude.ai and anywhere else Agent Skills
run. `agents/meturgaman.md` is the same thing as a Claude Code subagent. Both
know the schemes, read the engine's flags rather than trusting silent output, and
refuse to supply a Hebrew text from memory.

## Sources and licences

The code and documentation here are MIT. The rest is not ours to license:

- **The texts** carry their own licences per edition. The tool reports each one
  rather than assuming.
- **Hebcal** is CC-BY-4.0 and the tool prints its attribution.
- **PocketTorah** is CC-BY-SA and the tool prints its attribution.
- **The romanization standards** in `sources/` are not committed. Two of the six
  are copyrighted commercial publications, so `sources/` is gitignored and only
  provenance lives in the repository. `sources/manifest.md` records every URL and
  SHA-256, and `python -m tools.fetch_sources` retrieves and verifies them.

What *is* committed is the extracted table data in `schemes/`, because a table of
correspondences between two writing systems is a set of facts.

## Not yet

An MCP server of its own, the tanach.us reader, translation beyond retrieval of
published translations, and a web interface. Sefaria runs hosted MCP servers at
`https://mcp.sefaria.org/sse` and `https://developers.sefaria.org/mcp` if that is
what you want today; they need a paid account, which is why this tool does not
depend on them.
