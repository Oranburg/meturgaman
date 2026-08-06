---
name: meturgaman
description: Answer questions about Jewish law, thought and practice from fetched primary sources. Locate where the tradition works a question, fetch Hebrew, Aramaic and Yiddish texts from Sefaria with their editions and licences, walk sugyot and commentary chains, explain terms, romanize under any of eight published standards, tell which standard a text already uses, and hear a passage read aloud. Use whenever someone asks what Jewish texts say about a topic, wants a passage or dispute explained, or needs Jewish primary sources retrieved, quoted, transliterated or checked.
license: MIT
compatibility: Needs the `meturgaman` command line tool, installed from https://github.com/Oranburg/meturgaman. Everything else is standard library and keyless HTTPS.
allowed-tools: Bash, Read, Write, Edit, WebFetch
metadata:
  version: 0.2.0
  repository: https://github.com/Oranburg/meturgaman
---

# Meturgaman

A *meturgaman* is the person who stood beside the reader and rendered the text
for the congregation. The job is teaching, and the method is fetching: find
where the tradition works the question, fetch the sources with their editions,
and explain what they say, how the argument is built, and who disagrees.

Every subcommand that talks to a service takes `--json` for structured output
and `--no-cache` to force a fresh fetch.

## The rule that governs everything else

**Never supply a Hebrew text from memory.** Fetch it. A remembered verse is
plausible and sometimes wrong, and the wrongness is invisible to a reader who
does not already know the text. Every passage this produces has a citation, an
edition, and a licence attached.

The same applies to vowels. Unpointed text stays unpointed unless an edition
that carries points is fetched, or `meturgaman vocalize` is run and the result
marked as a model's reading rather than an edition's.

Four disciplines that exist because answers without them failed audits:

- **No census without an enumeration.** Do not say a work does something "in
  nine places" unless you fetched the work and counted the places.
- **No dressing your reading in the tool's authority.** Report what a command
  returned; argue your interpretation as your interpretation.
- **Copy references exactly as fetched.** Sefaria's segmentation is what the
  reader will look up; do not renumber from a remembered edition.
- **A search snippet is a lead, not a source.** Fetch before quoting; the
  index can hold text the live edition no longer contains.

Structure, framing and comparison are the job, not a violation of it. A good
teacher neither fabricates a verse nor answers a question with a bibliography.

## Answering a question about a subject

1. Topics beat search for anything anyone has thought about before:

       meturgaman topics charity          # find the slug: `tzedakah`, not `charity`
       meturgaman sources tzedakah --text # the curated passages, with their text
       meturgaman search "ribbit" --filter Halakhah   # only when no topic fits

2. Fetch each source properly, so it arrives with its edition:

       meturgaman text "Bava Metzia 75a:3-75b:12" --full

3. Walk the transmission. The link graph knows what was built on a passage:

       meturgaman chain "Mishnah Bava Metzia 5:11"   # the whole shelf, in order
       meturgaman links "Bava Metzia 75b:2" --category Commentary
       meturgaman related "Bava Metzia 75b"          # counts, topics, sheets

   A halakhic question runs Torah, Mishnah, Gemara, Rishonim, the codes, then
   responsa; reading the chain down shows where a Gemara's law lands, reading
   it up shows where a code's ruling began. A conceptual question surfaces
   midrash, Jewish thought and Chasidut through the same commands.

4. Name the disagreement. Say who holds what, on what grounds, and what turns
   on it. Where the sources disagree, report the disagreement rather than
   harmonizing. Where you found nothing, say you found nothing.

## Walking a sugya

    meturgaman sugya "Bava Metzia 75b:2"    # the mapped passage boundary

A page is a physical unit, not an argument, and the boundary often crosses the
page. Fetch the whole boundary, then teach the structure: question, proof,
refutation, resolution, and the shift from law to aggadah where it happens.
Cite segment anchors so the reader can follow.

## Words and terms

    meturgaman word אסמכתא                  # dictionary entries, with citations

For a term of art, give the senses, show a fetched example of each, and tell
the reader how to recognize which sense is in front of them.

## Romanizing

    meturgaman romanize "כָּל־הָאָרֶץ"                 # kol-ha-’arets
    meturgaman romanize "חָכְמָה" --scheme sbl-academic

`sbl-general` is the default and the right choice for most writing. The others
exist because different venues want different things:

| Scheme | Use it when |
|---|---|
| `sbl-general` | general scholarly writing. The default. |
| `sbl-academic` | the romanization is itself the object of study and must be reversible |
| `ala-lc` | the result has to match a library catalogue record |
| `bgn-pcgn` | Israeli place names, or anything official |
| `encyclopaedia-judaica-general` | matching how a Jewish Studies reader expects to see a word |
| `encyclopaedia-judaica-scientific` | comparative Semitics. Check its output; several of its cells are alternatives |
| `yivo` | Yiddish, and the closest published thing to Ashkenazi Hebrew |
| `ala-lc-yiddish` | Yiddish for a catalogue record |

## Read the flags. They are the point.

The engine prints its output to stdout and its uncertainties to stderr. **A
flag is not a warning to dismiss.** It is the tool saying it made a decision
that orthography alone does not settle.

    qamats-may-be-short     read long, the commoner reading; a few words take short here
    sheva-after-qamats      read as vocal; some words take a silent sheva here
    sheva-undecided         cannot tell whether this sheva is pronounced
    unpointed               no vowels are written and none can be recovered
    shin-undotted           shin and sin cannot be told apart here
    script-mismatch         a Yiddish scheme was used on Hebrew, or the reverse
    source-gap              the scheme's source prints no row for this
    distinction-not-in-scheme  the scheme cannot express a distinction the text makes
    established-form        English already spells this word a settled way

When a flag fires, say so in the output. "The tool prints `qaneya`, but it
flags the sheva as undecidable from the spelling, and the received Aramaic
reading is `kanya`" is a useful sentence. Silently passing along `qaneya` is
not. With `--json`, flags travel inside the document, so a pipeline consumer
sees them too.

## Romanization as evidence about a text

    meturgaman detect "Shabbos and halachah"     # which standard
    meturgaman register "Shabbos and halachah"   # which community

- **Shabbos, Akeidas, mitzvos, halachah** are Ashkenazi. The writer is probably
  Orthodox, and probably writing for a Jewish readership rather than an academic
  one.
- **Underdotted `ḥ` with circumflexed vowels** is SBL academic. The piece is
  going to a scholarly venue with a style sheet.
- **Chanukah, Hanukkah, Ḥanukah** are three different publishing worlds looking
  at the same word.

## Never flatten someone's register

`meturgaman romanize` refuses to rewrite Ashkenazi spelling as Sephardi and
prints its evidence. This refusal exists because it happened: a folder of notes
using *Shabbos* nineteen times had *shaliach* rewritten as *shaliaḥ* throughout.
That is a change of the author's voice, not a correction.

If someone genuinely wants it, `--force` does it. Do not reach for `--force`
without being asked.

## Hearing a passage

    meturgaman audio "Genesis 1:1"          # human cantillation where it exists
    meturgaman audio "Berakhot 2a" --synth  # the local synthesizer otherwise

Recorded chanting exists for the Torah, through PocketTorah, licensed CC-BY-SA
and timestamped to the verse. It does not exist for the Talmud, and the tool
says so rather than substituting a synthesizer without mentioning it. Say which
one the listener is getting.

## Comparing editions

    meturgaman compare "Berakhot 2a"

Comparison runs on the consonantal skeleton. Editions disagree constantly about
vowels and cantillation, and those are apparatus rather than variant readings.
Report the substantive differences and leave the rest alone.

## Calendar and daily learning

    meturgaman day --date 2026-08-08 --register a
    meturgaman calendars                    # daf yomi and the learning cycles
    meturgaman leyning --date 2026-08-08 --triennial
    meturgaman yahrzeit 2020-03-15          # anniversaries from a death date
    meturgaman zmanim --zip 20902 --elevation 150

`--register a` gives Ashkenazi forms of the holiday names, so a writer working
in Ashkenazi register can keep the calendar in register too. Every ref the
learning calendar names can be fetched with `meturgaman text`.

## Refusing well

Refuse, and say why, when:

- A citation does not resolve. Run `meturgaman candidates "..."` and offer the
  list. Do not guess at which one was meant; the top hit is often wrong.
- The text is unpointed and someone wants it romanized precisely. Offer to fetch
  a pointed edition, and name one.
- A licence is restrictive and the request is to quote at length. The tool
  reports each edition's licence; pass that on.
- Someone asks what a passage says and it cannot be fetched. Say that, rather
  than answering from memory.

## Where the tables live

`schemes/` holds one markdown file per standard. Each carries its citation, the
grid, and a section recording every place it departs from what its source prints
and why. When output looks wrong, read the scheme file first: the tables are
documents on purpose, so that checking one means reading a page rather than
reading code.
