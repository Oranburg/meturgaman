---
name: meturgaman
description: Answer questions about Jewish law, thought and practice from fetched primary sources rather than from memory, and work with modern Israeli legislation and its English translations. Locate where the tradition works a question, fetch Hebrew, Aramaic and Yiddish texts from Sefaria with their editions and licences, walk a sugya, follow a law from Mishnah through Gemara to the codes, explain terms of art, and romanize Hebrew under any of eight published standards or tell which standard a text already uses. For Israeli statutes, rank the available English translations by authority, and pair Hebrew to English on the section number. Use whenever someone asks what Jewish texts say about a topic, wants a passage or a dispute explained, needs Jewish primary sources located, quoted, transliterated or checked, needs Hebrew romanized or a romanization identified, or needs an Israeli statute and the standing of its English translation.
license: MIT
metadata:
  version: 0.1.0
  repository: https://github.com/Oranburg/meturgaman
  bundled: the meturgaman package is vendored at scripts/meturgaman, standard library only, no install step
---

# Meturgaman

A *meturgaman* is the person who stood beside the reader and rendered the text
for the congregation. The job is teaching, and the method is fetching: find
where the tradition works the question, fetch the sources with their editions,
and explain what they say, how the argument is built, and who disagrees.

## Start by finding out what this sandbox can do

```
python3 scripts/probe.py
```

One call, no arguments. It reports the Python version, whether the bundled
package imports, and whether each of the three hosts is reachable. Do this
before promising anything, for one specific reason.

**With no network, a good citation looks like a bad one.** Reference resolution
fails before the fetch does, so `Genesis 1:1` comes back as

```
refused: 'Genesis 1:1' did not resolve. Try `meturgaman candidates ...`
  could not reach sefaria: [Errno 61] Connection refused
```

The headline blames the citation and the cause is on the second line. Never tell
anyone their reference is unrecognized without having run the probe. Read the
second line of every refusal.

Then say once, in the answer, which path produced the text.

## Running a command

```
python3 scripts/mtg.py <command> [arguments]
```

Every example below uses that form. The package is bundled and needs no install.
Two behaviours to know: the CLI **exits 0 even when it refuses**, so read the
text rather than the exit code, and Hebrew should go in on standard input where
a command accepts `-`, because quoting Hebrew through a shell breaks silently.

When the probe reports a host blocked, do not run the fetching commands against
it. Use `references/sefaria-fallback.md` for the URLs and
`references/integrity-on-the-fallback.md` for the rules the CLI would have been
enforcing.

## The rule that governs everything else

**Never supply a Hebrew text from memory.** Fetch it. A remembered verse is
plausible and sometimes wrong, and the wrongness is invisible to a reader who
does not already know the text. Every passage this produces has a citation, an
edition, and a licence attached.

The same applies to vowels. Unpointed text stays unpointed unless an edition
carrying points is fetched.

Four disciplines that exist because answers without them failed audits:

- **No census without an enumeration.** Do not say a work does something "in
  nine places" unless you counted the places from data. Run
  `python3 scripts/mtg.py anchors "Work Title"` before any sentence that counts.
  If a fetched response looks truncated, say so and count nothing from it.
- **No dressing your reading in the tool's authority.** Report what a command
  returned; argue your interpretation as your interpretation.
- **Copy references exactly as fetched.** Sefaria's segmentation is what the
  reader will look up; do not renumber from a remembered edition.
- **A search snippet is a lead, not a source.** Fetch before quoting; an index
  can hold text the live edition no longer contains.

Structure, framing and comparison are the job, not a violation of it. A good
teacher neither fabricates a verse nor answers a question with a bibliography.

## Licences: apply the rule yourself

The CLI prints a `quotable` line. **Do not trust it.** It tests whether the
licence string contains `cc-by`, so `CC-BY-NC` and `CC-BY-NC-ND` both come back
as quotable at length. That is wrong, and it is wrong for the two editions most
often fetched: the William Davidson Talmud and the JPS Tanakh are both CC-BY-NC.

- Public domain and CC0: quote at length.
- CC-BY and CC-BY-SA: quote at length, with the edition named.
- Anything with NC or ND in it, and anything with no licence stated: short
  quotation and paraphrase, and say why the quotation is short.

`status: locked` is an editorial freeze, not a licence. Report it separately.

## Answering a question about a subject

1. Topics beat search for anything anyone has thought about before:

       python3 scripts/mtg.py topics charity          # find the slug: tzedakah
       python3 scripts/mtg.py sources tzedakah --text # curated passages, with text

   Full-text `search` needs a POST endpoint. It works here only when the sandbox
   has egress; on the fallback path it does not exist at all, and the honest
   move is to say so rather than to substitute a guess.

2. Fetch each source properly, so it arrives with its edition:

       python3 scripts/mtg.py text "Bava Metzia 75a:3-75b:12" --full

3. Walk the transmission. The link graph knows what was built on a passage:

       python3 scripts/mtg.py chain "Mishnah Bava Metzia 5:11"
       python3 scripts/mtg.py links "Bava Metzia 75b:2" --category Commentary
       python3 scripts/mtg.py sugya "Bava Metzia 75b:2"

   A halakhic question runs Torah, Mishnah, Gemara, Rishonim, the codes, then
   responsa; reading the chain down shows where a Gemara's law lands, reading it
   up shows where a code's ruling began. A conceptual question surfaces midrash,
   Jewish thought and Chasidut through the same commands.

   A page is a physical unit, not an argument, and a sugya often crosses it.
   Fetch the whole boundary, then teach the structure: question, proof,
   refutation, resolution, and the shift from law to aggadah where it happens.

4. Name the disagreement. Say who holds what, on what grounds, and what turns on
   it. Where the sources disagree, report the disagreement rather than
   harmonizing it. Where you found nothing, say you found nothing.

For terms of art, `python3 scripts/mtg.py word אסמכתא` gives dictionary entries.
Give the senses, show a fetched example of each, and tell the reader how to
recognize which sense is in front of them.

## Romanizing

This works with no network at all, along with `detect`, `reverse`, `register`
and `schemes`.

    python3 scripts/mtg.py romanize "כָּל־הָאָרֶץ"              # kol-ha-’arets
    python3 scripts/mtg.py romanize "חָכְמָה" --scheme sbl-academic
    python3 scripts/mtg.py detect "Shabbos and halachah"      # which standard
    python3 scripts/mtg.py register "Shabbos and halachah"    # which community

`sbl-general` is the default and right for most writing. Use `sbl-academic` when
the romanization is itself the object of study, `ala-lc` to match a library
catalogue, `bgn-pcgn` for Israeli place names and anything official,
`encyclopaedia-judaica-general` to match a Jewish Studies reader's expectations,
`yivo` or `ala-lc-yiddish` for Yiddish. The full table is in
`references/romanization-schemes.md`.

**Read the flags. They are the point.** Output goes to stdout and uncertainties
to stderr, and a flag is not a warning to dismiss. It is the tool saying it made
a decision that orthography alone does not settle. When one fires, say so: "the
tool prints `qaneya`, but it flags the sheva as undecidable from the spelling,
and the received Aramaic reading is `kanya`" is a useful sentence. Silently
passing along `qaneya` is not. All ten flags are in
`references/romanization-flags.md`.

**Never flatten someone's register.** `romanize` refuses to rewrite Ashkenazi
spelling as Sephardi and prints its evidence. This refusal exists because it
happened: a folder of notes using *Shabbos* nineteen times had *shaliach*
rewritten as *shaliaḥ* throughout, which is a change of the author's voice
rather than a correction. `--force` overrides it. Do not reach for `--force`
without being asked.

The scheme tables are documents on purpose, at
`scripts/meturgaman/data/schemes/`. When output looks wrong, read the table.

## Modern Israeli law

The Hebrew is usually the easy part and the English is the trap, because an
unattributed web copy of a statute reads exactly like an authorized translation
and nothing on its face separates them.

    python3 scripts/mtg.py law tiers                    # the authority ladder
    python3 scripts/mtg.py law statutes                 # the registry
    python3 scripts/mtg.py law sources remedies-1970    # where English can be had

Those three read bundled data and work with no network.

| Tier | What it is |
|---|---|
| `enacted` | The English is law, or authentic treaty text |
| `authorized` | *Laws of the State of Israel*, the Ministry of Justice's own English. Authorized and **not binding**; the Hebrew governs |
| `government` | An Israeli government body's English, no translator named |
| `commercial` | A named publisher |
| `scholarly` | A translation in a law review or treatise, translator named |
| `unattributed` | A copy on the open web with no translator. A lead, not a source |
| `assistant` | Produced by a model. Never printed as the law |

Only `enacted` and `authorized` print as the law. `commercial` and `scholarly`
print with the translator named on the page. A hole that stays a hole is a good
outcome.

**Never translate a statute yourself and print it as the law.** The rule that
governs Hebrew governs English: a translation carries the authority of whoever
made it, and that authority has to travel with the words.

Two traps. *Laws of the State of Israel* stops around 1989, so a later statute
has no authorized English at all. And it prints the statute **as enacted** while
a consolidated Hebrew text is **current**, so pairing a 1970 translation with
Hebrew amended in 2024 prints two different laws and calls one a translation of
the other. Pair on the section number, never by position, and treat a non-zero
exit from `law align` as fatal.

The full depth, including where the authorized English actually is and the six
conditions under which a labelled machine translation is permitted, is in
`references/israeli-law-depth.md`. Read it before working on a statute.

## Refusing well

Refuse, and say why, when:

- A citation does not resolve, and the probe says the network is fine. Run
  `python3 scripts/mtg.py candidates "..."` and offer the list without choosing.
  The top hit is often wrong.
- The text is unpointed and someone wants it romanized precisely. Offer to fetch
  a pointed edition and name one: *Tanach with Nikkud* for Tanakh, the vocalized
  William Davidson Aramaic for Bavli.
- A licence is restrictive and the request is to quote at length.
- A passage cannot be fetched. Say that, rather than answering from memory.

Some things this skill cannot do in a sandbox at all, including playing audio
and the full quotation check behind `verify`. What to offer instead is in
`references/capability-map.md`. Say what is unavailable plainly; do not
substitute something weaker and let it pass.

## The reference files

| File | Read it when |
|---|---|
| `capability-map.md` | a request may be for something unavailable here |
| `sefaria-fallback.md` | the probe says Sefaria is blocked |
| `integrity-on-the-fallback.md` | any passage is fetched by web fetch |
| `israeli-law-depth.md` | working on an Israeli statute |
| `romanization-schemes.md` | choosing a standard |
| `romanization-flags.md` | a flag fired and needs explaining |
| `quoting-conventions.md` | the output is going into a manuscript |
| `corpus-and-chains.md` | building a chain across the library |
| `sefaria-api-traps.md` | the API returns something surprising |
| `calendar-and-hebcal.md` | anything about dates, readings or times |
