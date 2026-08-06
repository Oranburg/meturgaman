---
name: meturgaman
description: Fetch Hebrew, Aramaic and Yiddish primary sources from Sefaria with their editions and licences, romanize them under any of eight published standards, tell which standard a text already uses, find what the tradition says about a subject, and hear a passage read aloud. Use whenever Jewish primary sources need retrieving, quoting, transliterating, or checking, or when someone asks what Jewish texts say about a topic.
license: MIT
compatibility: Needs the `meturgaman` command line tool, installed from https://github.com/Oranburg/meturgaman. Everything else is standard library and keyless HTTPS.
allowed-tools: Bash, Read, Write, Edit, WebFetch
metadata:
  version: 0.1.0
  repository: https://github.com/Oranburg/meturgaman
---

# Meturgaman

A *meturgaman* is the person who stood beside the reader and rendered the text
for the congregation. This does that job: it fetches the source, says which
edition it came from, and renders it into Latin letters under a standard that
is named rather than assumed.

## The rule that governs everything else

**Never supply a Hebrew text from memory.** Fetch it. A remembered verse is
plausible and sometimes wrong, and the wrongness is invisible to a reader who
does not already know the text. Every passage this produces has a citation, an
edition, and a licence attached, because a Hebrew quotation with no edition
behind it is not a citation.

The same applies to vowels. Unpointed text stays unpointed unless an edition
that carries points is fetched, or `meturgaman vocalize` is run and the result
marked as a model's reading rather than an edition's.

## Getting started

    meturgaman schemes                 # the eight standards, each with its source
    meturgaman text "Berakhot 2a"      # a passage, in every edition that has it

## What the tradition says about a subject

This is the most common question and it has a two-step answer. Sefaria has a
curated topic ontology, which is far better than full-text search for anything
anyone has thought about before.

    meturgaman topics charity          # find the slug: `tzedakah`, not `charity`
    meturgaman sources tzedakah --text # the curated passages, with their text

Fall back to search only when no topic fits:

    meturgaman search "ribbit" --filter Halakhah

Then fetch each source properly, so it arrives with its edition:

    meturgaman text "Bava Metzia 75a:3-75b:12"

Report what the sources say. Where they disagree, say they disagree rather than
harmonizing them. Where you found nothing, say you found nothing.

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

The engine prints its output to stdout and its uncertainties to stderr. **A flag
is not a warning to dismiss.** It is the tool saying it made a decision that
orthography alone does not settle.

    qamats-qatan-assumed    read short; a meteg would have made it long
    sheva-undecided         cannot tell whether this sheva is pronounced
    unpointed               no vowels are written and none can be recovered
    shin-undotted           shin and sin cannot be told apart here
    script-mismatch         a Yiddish scheme was used on Hebrew, or the reverse
    source-gap              the scheme's source prints no row for this
    distinction-not-in-scheme  the scheme cannot express a distinction the text makes

When a flag fires, say so in the output. "This is `ḥokhmah`, though the edition
carries no meteg, so a reading of `ḥakhmah` is not excluded" is a useful
sentence. Silently printing `ḥokhmah` is not.

## Romanization as evidence about a text

A transliteration says something about who wrote it and where it was going.
Reading that is a real capability, not a party trick.

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

## Calendar

    meturgaman day --date 2026-08-08 --register a
    meturgaman leyning --date 2026-08-08 --triennial

`--register a` gives Ashkenazi forms of the holiday names, so a writer working
in Ashkenazi register can keep the calendar in register too.

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
