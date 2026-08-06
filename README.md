# Meturgaman

A study companion for Jewish texts. Ask it what the tradition says about a
subject and it finds the sources, fetches them with their editions and
licences, and teaches from what it fetched: how the argument is built, who
disagrees, and what turns on the disagreement. Underneath the teaching sits a
careful instrument: retrieval that names its edition every time, romanization
under eight published standards, comparison of editions, recorded
cantillation, and the Jewish calendar.

A *meturgaman* is the person who stood beside the reader and rendered the text
for the congregation. This does that job, in both senses: it renders the
letters, and it renders the meaning, without ever supplying a text from
memory.

## What an answer looks like

Asked "is there Jewish wisdom about limited liability?", the agent built on
this tool answered from fetched sources: the default of expansive liability,
the *apotiki* formula of Shulchan Arukh Choshen Mishpat 117:1 quoted from the
Lemberg 1898 printing, the Nehardean *iska* from Bava Metzia 104b:14, the
debtor protections of Deuteronomy 24 and Mishneh Torah Creditor and Debtor
1:7, and the modern dispute over whether halakhah recognizes the corporate
veil, reported as a dispute. An independent checker then fetched every one of
those citations and confirmed all six.

That is the standard the project holds itself to, and it is measured rather
than claimed: six real questions were put to the agent, every answer was
saved verbatim, and every citation-bearing claim was handed to a separate
verification agent told to fetch it and try to refute it. The transcripts,
the hostile verification reports, and an honest account of what still goes
wrong (counts and reference anchors remain the weak spot) are in
[notes/agent-evaluation.md](notes/agent-evaluation.md).

## Getting started

```
git clone https://github.com/Oranburg/meturgaman.git
cd meturgaman
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m tools.fetch_sources    # the source documents, verified by hash
.venv/bin/python -m pytest -m "not network"
```

Python 3.11 or later. The core has no dependencies at all: both services are
keyless JSON over HTTPS, and `urllib` does that.

```
meturgaman topics charity                     # find a subject's slug
meturgaman sources tzedakah --text            # what the tradition says about it
meturgaman text "Berakhot 2a"                 # a passage, in every edition
meturgaman chain "Mishnah Bava Metzia 5:11"   # what the tradition built on it
meturgaman romanize "כָּל־הָאָרֶץ"              # kol-ha-’arets
meturgaman audio "Genesis 1:1"                # chanted, by a person
```

## Walking the tradition

A halakhic question runs Torah, Mishnah, Gemara, the Rishonim, the codes,
then responsa. Sefaria's link graph knows the actual path for any passage,
and three commands walk it:

```
$ meturgaman chain "Mishnah Bava Metzia 5:11"
Mishnah Bava Metzia 5:11: what the tradition built on this passage

Tanakh  (5)
    Exodus       Exodus 22:24
    Leviticus    Leviticus 25:36  and 2 more
    Deuteronomy  Deuteronomy 23:20
Tosefta  (2)
Talmud  (3)
    Bava Metzia  Bava Metzia 75a:11-75b:4
Commentary  (43)
Quoting Commentary  (6)
Halakhah  (1)
```

The work lists are trimmed here; the command prints every work and its refs.

`meturgaman links` gives the same graph filtered and flat (`--category
Commentary`, `--refs-only` for piping), and `meturgaman related` summarizes
everything Sefaria attaches to a passage, topics included. Reading the chain
down from a Gemara shows where its law lands in the Shulchan Arukh; reading
up from a code shows where its ruling began. Every ref in the output can be
fetched with `meturgaman text`.

`meturgaman sugya` maps a Talmud reference to the passage boundary it belongs
to, which regularly crosses the printed page. `meturgaman word` fetches
dictionary entries, with Jastrow's citations back into the corpus.

## The one idea this is built around

Every romanization table lives in `schemes/`, as markdown, one file per
standard. No table is written in Python anywhere in this repository.

That is not a stylistic preference. A table written in code is a table nobody
proofreads: it gets edited to make a test pass, it drifts from the standard it
claims to implement, and the drift is invisible because checking it means
reading code. This project shipped a set of spirant characters that appear
nowhere in the SBL Handbook, and they survived a rewrite because a second file
had quietly copied them. They were caught by someone opening the PDF.

So the tables are documents. Each one carries its citation, its grid, and a
section recording every place it departs from what its source prints and why.
A test re-extracts each source and checks every character against it. When
the output looks wrong, you read one page.

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

What exists is Yiddish. YIVO's treatment of the *loshn-koydesh* layer, the
words of Hebrew and Aramaic origin, is Ashkenazi Hebrew pronunciation: `תּ` is
`t` and bare `ת` is `s`, which is what gives Shabbos rather than Shabbat. That
is real, published, and in `schemes/yivo.md`.

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
one mark doing two jobs: a dagesh is lene or forte, a sheva is vocal or
silent, a qamats is long or short, a vav is a consonant or half a vowel.

The engine decides these in a pass of their own, in the open. **Where the
rules cannot settle a question, it raises a flag rather than picking a default
and staying quiet.** Output goes to stdout, flags to stderr, and under
`--json` the flags travel inside the document so a pipeline cannot lose them.

```
$ meturgaman romanize "קָנְיָא"
qaneya
  [qamats-may-be-short] (קָנְיָא) read long (a), which is the commoner reading
  of this shape. A few words take a short qamats (o) here and are listed in
  rules/qamats-qatan.md; check the word if it matters
  [sheva-after-qamats] (קָנְיָא) read as vocal, which is the commoner reading
  after a long qamats. Some words take a silent sheva here and the spelling
  does not say which; check if it matters
```

The Library of Congress reaches the same conclusion from the cataloguing
side: its manual sends cataloguers to a dictionary "primarily to distinguish
schwa naʻ from schwa nah, a matter which has significant impact on
romanization." Code that answers from orthography alone should say when it is
unsure.

## Every source carries its edition and its licence

```
$ meturgaman text "Genesis 1:1" --version all
Genesis 1:1
8 editions, 5 independent witnesses
providers: he.wikisource.org, tanach.us, jps.org, sefaria.org, chabad.org
```

Five witnesses from eight editions, because three of them came from the same
digitization. An edition's provider is derived from its own stated source
rather than from the fact that Sefaria served it, so two rows that came from
one place do not count as two. `meturgaman compare` then reports where
editions actually differ, on the consonantal skeleton, with vocalization
recorded as apparatus rather than as disagreement.

## For scripts and other agents

Every command that talks to a service takes `--json` and `--no-cache`, limits
are bounded, refusals exit non-zero with a reason on stderr, and
`meturgaman clear-cache` empties the response cache. The engine romanizes
about 60,000 words per second and the CLI starts in about 50 milliseconds, so
driving it one call at a time from an agent costs nothing worth engineering
around.

```
meturgaman text "Genesis 1:1" --json | jq '.editions[0].segments[0].text'
meturgaman links "Bava Metzia 75b:2" --refs-only | while read ref; do ...
```

## Hearing it, and the calendar

**Recorded cantillation.** Sefaria carries PocketTorah's recordings: a person
chanting, with the trope, CC-BY-SA, timestamped to the verse. Torah only.
**Synthetic speech** through the macOS `Carmit` voice covers the rest, and
the tool always says which one you are getting.

```
meturgaman audio "Genesis 1:1"           # the recording
meturgaman audio "Berakhot 2a" --synth   # nobody has recorded the Talmud
meturgaman day --date 2026-08-08 --register a
meturgaman calendars                     # daf yomi and the learning cycles
meturgaman leyning --triennial
meturgaman yahrzeit 2020-03-15
meturgaman zmanim --zip 20902 --elevation 150
```

`--register a` keeps holiday names in Ashkenazi register; Hebcal publishes
twenty-two locales and six of them are Ashkenazi.

## What it reads

**Sefaria**, for texts, editions, links, topics, search, dictionaries,
commentaries, sugya boundaries and the learning calendar. No key, no
registration.

**Hebcal**, for the calendar, Torah readings, halachic times and yahrzeits.

**Dicta**, optionally and locally, for adding vowel points. Their models are
on HuggingFace under a permissive licence and run on your own machine. They
publish no API contract, so this project does not call one.

Both APIs' contracts are committed under `docs/api/`, so the code is written
against a recorded spec rather than against anyone's memory of one.

## The agent

`agents/meturgaman.md` is the Claude Code subagent; `skills/meturgaman/SKILL.md`
is the same capability as an Agent Skill for claude.ai and anywhere else
skills run. Both are written around teaching from fetched sources, and both
carry four disciplines that came out of the evaluation: no census without an
enumeration, no dressing a reading in the tool's authority, references copied
exactly as fetched, and search snippets treated as leads rather than sources.
The evidence for what the agent can and cannot do is in
[notes/agent-evaluation.md](notes/agent-evaluation.md).

## Sources and licences

The code and documentation here are MIT. The rest is not ours to license:

- **The texts** carry their own licences per edition. The tool reports each
  one rather than assuming.
- **Hebcal** is CC-BY-4.0 and the tool prints its attribution.
- **PocketTorah** is CC-BY-SA and the tool prints its attribution.
- **The romanization standards** in `sources/` are not committed. Two of the
  six are copyrighted commercial publications, so `sources/` is gitignored and
  only provenance lives in the repository. `sources/manifest.md` records every
  URL and SHA-256, and `python -m tools.fetch_sources` retrieves and verifies
  them.

What *is* committed is the extracted table data in `schemes/`, because a
table of correspondences between two writing systems is a set of facts.

## Not yet

An MCP server of its own, the tanach.us reader, translation beyond retrieval
of published translations, and a web interface. Sefaria runs hosted MCP
servers at `https://mcp.sefaria.org/sse` and
`https://developers.sefaria.org/mcp` if that is what you want today; they
need a paid account, which is why this tool does not depend on them.
