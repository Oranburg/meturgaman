# What this skill can do here, and what it cannot

Read this when a request may be for something the sandbox cannot deliver. Run
`python3 scripts/probe.py` first; the three lists below depend on what it found.

## Works with no network at all

Confirmed by running each with egress blocked and a cold cache.

| Command | What it gives |
|---|---|
| `romanize` | Hebrew to Latin under any of eight schemes |
| `detect` | which scheme a romanization already uses |
| `reverse` | Latin back to Hebrew letters |
| `register` | Ashkenazi or Sephardi spelling, with the evidence |
| `schemes`, `schemes --name X` | the scheme list, or one table in full |
| `law tiers` | the seven-tier translation authority ladder |
| `law statutes` | the statutes in the bundled registry |
| `law sources {id}` | where an English text of that statute can be had |
| `law parse`, `law align`, `law reconcile` | statute text processing over files |

The `law` registries are bundled data, not fetches, which is why they survive
with no egress. `law parse`, `align` and `reconcile` work on files, so the user
has to attach the file to the conversation first rather than name a path.

The scheme tables live at `scripts/meturgaman/data/schemes/*.md`, one file per
standard, each carrying its citation and a note on every place it departs from
its source. When output looks wrong, read the table before doubting the word.

## Needs network, and has a web-fetch fallback

`text`, `editions`, `compare`, `links`, `related`, `chain`, `sugya`, `word`,
`topics`, `sources`, `candidates`, `anchors`, `calendars`, `day`, `daf`,
`leyning`, `yahrzeit`, `zmanim`, `study`, `law hebrew`, `law amendments`.

With egress, run these through `scripts/mtg.py`. Without it, use
`references/sefaria-fallback.md` and `references/integrity-on-the-fallback.md`.

Three qualifications:

- **`chain` and `anchors` degrade into your own reading.** Their grouping and
  counting are pure functions over a fetched payload, so the work can be done by
  hand, but then it is your reading rather than the tool's output and must be
  labelled that way. `anchors` exists to make counting sentences checkable, so a
  hand count from a possibly-truncated payload is worse than no count.
- **The calendar family talks to a different host.** `day`, `leyning`, `zmanim`
  and `yahrzeit` reach hebcal.com, while `calendars` and `daf` reach Sefaria,
  and `law hebrew` reaches he.wikisource.org. Partial egress is a real state,
  which is why the probe tests all three.
- **`study` writes a file** into the sandbox, so it has to be handed to the user
  as a download rather than as a path.

## Cannot work here, and what to offer instead

**`search`.** Sefaria's search endpoint is POST only, and a web fetch cannot
POST. Use `/api/name/` and `/api/v2/topics/{slug}` for anything the tradition
has a topic for, which is most things anyone has thought about before. Where no
topic fits, say plainly that full-text search is not available on this path,
offer to run it in Claude Code, and treat any web search result as a lead to be
fetched properly before quoting.

**`refs` and `verify`.** Both need a POST endpoint and asynchronous polling. The
honest degraded offer, and it should be described in exactly these terms: the
citations in a draft can be extracted and each one validated against
`/api/ref/`, and each cited passage can be fetched and read. What cannot be done
is the consonantal-skeleton comparison that catches a quotation which has
drifted from its edition, which is the part that finds real problems. Offer
citation validation, call it citation validation, and do not call it `verify`.

**`audio`.** The sandbox cannot play sound, and the synthesizer path shells out
to the macOS `say` command, which does not exist there. Recorded cantillation
does exist for the Torah through PocketTorah, CC-BY-SA and timestamped to the
verse. Name the recording, its licence and its URL, and hand the user the link.
Never say a passage was played or heard.

**`vocalize`, and `study --vocalize`.** These need Dicta's models through
PyTorch and Transformers, several hundred megabytes that are not in this bundle
and cannot be downloaded without egress. Offer the better answer instead, which
is an edition that already carries points: *Tanach with Nikkud* for Tanakh, and
the vocalized William Davidson Aramaic for Bavli, which `version=source` returns
for a Talmud reference. A fetched pointed edition beats a model's pointing, and
it comes with a citation.

## Two things about running the CLI at all

**Exit codes say nothing.** A refusal is a line on stdout starting `refused:`,
and the process still exits 0. Read the text.

**Pass Hebrew on standard input, not on the command line.** Quoting Hebrew
through a shell is a place things break silently. `romanize` and `register`
accept `-` and read stdin. `word` does not, so its Hebrew argument needs care.
