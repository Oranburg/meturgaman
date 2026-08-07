# Session log, the night of 2026-08-06

One overnight session, working from the handoff brief and then from Seth's
instructions as they arrived. This file is the narrative index; the commit
log carries the detail, and every capability claim below points at evidence
in this repository.

## What the night was for

The brief asked one question above all others: can the agent built on this
tool actually teach, and can that be known rather than claimed? Everything
else (tests, fixes, features) either served that question or came out of
what answering it revealed.

## The order of events

**1. Hardening before concurrency.** Six evaluation agents were about to
share one response cache, and the cache write was not atomic. Fixed first,
verified with an eight-process hammer: zero corrupt reads across 2,400
cycles. Commit `a628bd2`.

**2. The baseline evaluation.** The six questions from the brief, asked of
the agent exactly as it stood, answers saved verbatim, and every
citation-bearing claim handed to a separate verification agent instructed to
fetch it and try to refute it. Findings: far stronger than the brief feared,
with three specific failure kinds and no invented texts. Transcripts and
reports in `notes/evaluation/`, judgement in `notes/agent-evaluation.md`.

**3. The capability build.** chain, links, related, calendars, yahrzeit,
clear-cache; `--json` and `--no-cache` everywhere; bounded limits. Along the
way, four real bugs surfaced and were fixed with tests: the silently broken
yahrzeit parameters, the misfiled `sh` locale, the unreachable abbreviation
classifier, and the fetcher's flag interactions. Commits `9b10c59` through
`ac9049a`.

**4. The rewrite and the re-evaluation.** The agent spec was rebuilt around
teaching, with the baseline's three failure kinds turned into standing
rules. The same six questions again, verified the same hostile way:
measurable improvement on every failure kind, with a narrow residue (counts
and reference anchors) named honestly in the evaluation and in the README.
Commits `730a265`, `95803bf`.

**5. The debt from the brief's inventory.** Tests for the four uncovered
modules (160 tests became 226), the six weak assertions repaired, doctests
running (one was stale and caught immediately), and all thirteen scheme-file
disclosure gaps verified against the source documents through both channels
before any file changed. Commits `87a19ed`, `44f86aa`.

**6. Documentation and the wiki.** README rewritten to lead with the work
and point at the evidence; seven wiki pages written, staged, and then
published once Seth created the wiki's first page. Commits `7ed83b6`,
`66e298f`, plus the wiki repository's own history.

**7. Seth's follow-on: three features, then five.** First round: `verify`
(the draft checker), `daf`, and `study --sugya` / `--output`, all
live-tested. Commit `48e6df7`. Then the five-feature list, built in order:

- **anchors** (commit "anchors: a census from data"): every populated anchor
  of a work with its segment count, from the service's shape record. Against
  the very work both evaluation rounds miscounted, it prints the verified
  census: twelve anchors, thirteen segments, the shor gloss at 4:3.
- **verify diagnostics** ("a miss becomes a diagnosis"): a failed quotation
  now names the closest passage, the words that do match, and the first word
  where the draft parts from the edition.
- **paired texts** ("the ruling with its reasoning, honestly sourced"):
  `rules/pairings.md` names the companion works with checkable reasons; the
  link graph supplies passage-level connections at run time; absence is
  reported as absence, because the graph was probed and found sparse before
  the document was written.
- **study --vocalize** ("point the unpointed, and say a model did it"):
  Dicta's local model points exactly the segments that carry no vowels, and
  the output is stamped as a model's reading. The model stack is a
  multi-gigabyte optional download and was deliberately not installed on
  this machine; the wiring is stub-tested and the refusal path is tested for
  real.
- **the MCP server** ("kept out of the core on purpose"): thirteen tools
  over stdio behind the `mcp` extra, handshake-tested through the real
  protocol.

## The state at the end

- 263 tests, all passing, up from 160 at the start of the night; a fresh
  clone installs and passes offline.
- The core remains standard library only; dicta and mcp are extras that
  refuse politely when absent.
- The wiki is live and matches the staged copy in `wiki/`; Seth has not yet
  chosen whether the staged copy stays as the source of record.
- The evaluation verdict, unchanged and evidence-backed: the agent teaches
  from fetched sources and survives hostile citation checking; its counts
  and anchors deserve a check when they matter, and `anchors` now exists to
  make that check one command.

## Judgement calls a future reader should know about

- Question 6 of the evaluation carried one added context sentence, because
  "find me something on this" needs a referent; both rounds used the same
  sentence, and the transcripts say so.
- The pairings document was written only after live probes showed which
  connections the link graph actually records; the probe results are stated
  in the document itself.
- Package code was twice edited while background agents were invoking the
  CLI, and both times a concurrently starting process saw an inconsistent
  intermediate state. The lesson is recorded in the project memory: freeze
  the package during agent waves.
