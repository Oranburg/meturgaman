Meturgaman is a study companion for Jewish texts. Ask it what the tradition
says about a subject and it finds the sources, fetches them with their
editions and licences, and teaches from what it fetched. Underneath sits a
careful instrument: retrieval that names its edition every time, romanization
under eight published standards, edition comparison, recorded cantillation,
and the Jewish calendar.

The one rule that governs everything: **no Hebrew text is ever supplied from
memory.** Every passage arrives with a citation, an edition, and a licence,
and every romanization decision the orthography cannot settle is flagged out
loud. What the agent built on this tool can and cannot do is measured, with
transcripts and hostile verification reports, in
[notes/agent-evaluation.md](https://github.com/Oranburg/meturgaman/blob/main/notes/agent-evaluation.md).

## The pages here

- [[Asking a Question]] describes the workflow from a real question to a
  taught answer: topics, sources, fetching, and the disciplines that keep an
  answer honest.
- [[The Corpus and Its Chains]] covers how the library is organized and how
  `chain`, `links`, `related`, and `sugya` walk it.
- [[The Eight Schemes]] says when to pick which romanization standard.
- [[Flags]] lists every uncertainty flag the engine raises and what to do
  about each one.
- [[Sefaria API Traps]] records the service behaviors that cost real
  debugging time, useful to anyone building on Sefaria.
- [[Adding a Ninth Scheme]] is the recipe for bringing in a new published
  standard without breaking the project's integrity claim.

## Quick start

```
git clone https://github.com/Oranburg/meturgaman.git
cd meturgaman
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m tools.fetch_sources
.venv/bin/python -m pytest -m "not network"
```

Then:

```
meturgaman topics charity
meturgaman sources tzedakah --text
meturgaman text "Berakhot 2a"
meturgaman chain "Mishnah Bava Metzia 5:11"
meturgaman romanize "כָּל־הָאָרֶץ"
meturgaman verify chapter.md
meturgaman daf
meturgaman anchors "Work Title"
```

`verify` checks a manuscript: every citation validated against Sefaria,
every Hebrew quotation checked against the passages cited in its
paragraph, on the consonantal skeleton. `daf` fetches today's daf yomi,
or any other learning cycle's reading with `--cycle`. `anchors` prints
every populated anchor of a work with its segment count, so a census
is counted rather than remembered. Study files can carry companions
(`study --paired`, from `rules/pairings.md` and the link graph) and
model-pointed vowels marked as such (`study --vocalize`, dicta extra).
An optional MCP server (`pip install 'meturgaman[mcp]'`, then
`meturgaman-mcp`) serves thirteen tools to Claude Desktop and Claude
Code over stdio.

Every command that talks to a service takes `--json` for structured output
and `--no-cache` to force a fresh fetch.
