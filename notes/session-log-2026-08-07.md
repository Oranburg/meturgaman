# Session log, 2026-08-07: a capability test battery, and what it found

Ten agents, each given a real task in a genre or a surface the earlier
evaluation had not touched, run in parallel against the live `meturgaman`
CLI and, for one of them, the live MCP server. Every agent was told to
answer its task and then separately assess the tool: what worked, what was
awkward, and any actual bug. This file is the record of what came back, what
survived a second, independent check, and what got fixed.

## The discipline: verify the verifiers too

Nine of the ten reports named at least one thing worth looking at. Before
touching any code, every claimed bug was independently reproduced from this
session, not taken on the reporting agent's word, because a subagent's
"I found a bug" is exactly the kind of plausible unverified claim
[[capabilities-and-limits]] names as the standing risk. Two claims did not
survive that check:

- **`daf --json` does not actually leak prose onto stdout.** The reporting
  agent's capture merged stdout and stderr; run with the streams kept apart,
  stdout is clean, parseable JSON and the human-readable line is correctly
  isolated on stderr, exactly as designed. Not fixed, because there was
  nothing to fix.
- **`study --vocalize`'s "duplicate" provenance note is intended design.**
  One copy lands in the rendered file body (so a saved study file still
  carries its own disclosure with no stderr in sight); one copy is repeated
  as a stderr flag (so a terminal session sees it as an uncertainty to check
  at generation time). Two channels, one fact, on purpose.
- **A third claim, "script-mismatch never fires for Hebrew under a Yiddish
  scheme," was half right.** Reading `engine.py` and testing a pointed word
  directly showed the flag fires exactly as designed for pointed input; it
  does not fire for unpointed Hebrew-script words, because an unpointed
  Hebrew word and a loshn-koydesh Yiddish spelling are the same string, and
  guessing which one a bare Hebrew word is would be inventing a
  distinction the spelling does not support. Left alone. A narrower, real
  gap underneath it (the ligature check only catches precomposed Yiddish
  ligature codepoints, not the far more common plain two-letter digraphs)
  is recorded below as a follow-up rather than a fix, because a good fix
  needs a Yiddish-orthography heuristic this project has no documented
  basis for yet.

## What was confirmed and fixed, each with a regression test

1. **`meturgaman text` without `--full` silently truncated a segment at 200
   characters with no mark.** A reader trusting the default preview could
   quote a clipped ruling as a complete one. Now appends
   `"… (--full for the rest)"` when a preview is actually cut.
   `tests/test_live_api.py::test_a_clipped_preview_says_so`.
2. **`meturgaman verify` on a missing file leaked a raw
   `[Errno 2] No such file or directory: '...'`.** Now a sentence in the
   tool's own voice. `tests/test_cli.py::test_verify_on_a_missing_file_refuses_in_its_own_voice`.
3. **`meturgaman sources <slug> --text` crashed the whole command** when one
   curated source was a Sefaria sheet rather than plain text: the per-item
   handler caught `LookupError` and `ValueError` but not the `NetworkError`
   a sheet's malformed fetch raises. One bad item no longer costs the rest
   of the list. `tests/test_sources_resilience.py`.
4. **`meturgaman links --category X` said "nothing links to REF"** when
   only the category filter came back empty, which was false whenever the
   ref had other, uncategorized-by-the-filter links (Genesis 28:12 has 99
   Commentary links; asking for `--category Grammar` reported "nothing
   links" as if it had none at all). Now names the category.
   `tests/test_live_api.py::test_a_category_filter_with_nothing_in_it_names_the_category`.
5. **`meturgaman sugya` echoed a non-Talmud reference back as if it were a
   confirmed passage boundary.** Sefaria's `/passages/` endpoint answers a
   ref it has nothing mapped for by returning that same ref, and the CLI
   printed it as though a real, if trivial, boundary had been found. Now
   recognized as the service's own no-op and reported as no mapping,
   in both the CLI and the MCP `sugya` tool.
   `tests/test_live_api.py::test_sugya_does_not_echo_a_ref_back_as_its_own_boundary`.
6. **The "this version is locked" warning read as a licensing caution.**
   `status: locked` is Sefaria's own editorial freeze against further edits,
   unrelated to copyright; a fully public-domain, freely quotable edition
   can carry it. Reworded so it no longer tells a reader to check the
   licence over something the licence field, reported separately, already
   answers. `tests/test_live_api.py::test_the_locked_warning_does_not_read_as_a_licence_warning`.
7. **`meturgaman reverse` on multi-word input ran every word together and
   only fixed the final letter of the whole string.** The space character
   was discarded in the same branch as diacritic apostrophes, and the
   word-final letter fix-up ran once on `letters[-1]` for the entire
   reconstruction rather than once per word, so `"gegebn vegn"` came back
   as one run-on string with a medial nun where a final one belonged.
   Word boundaries are now kept and the fix-up runs per word.
   `tests/test_romanize.py::test_reverse_keeps_word_boundaries_and_finals_per_word`.
8. **The MCP `romanize` tool gave a cold client no way to know the eight
   scheme names without guessing and eating an error.** `scheme` is now a
   proper JSON Schema enum, built from the schemes actually loaded rather
   than typed out by hand, with the blank default kept as a valid member.
9. **The MCP `calendars` tool either leaked a raw Python unpack error or
   silently forwarded garbage to the service**, depending on how many
   hyphens the malformed date string happened to contain. `sefaria.calendars`
   now parses with `date.fromisoformat` and raises one clear message,
   inherited by both the CLI and the MCP surface from the one fix.
   `tests/test_mcp_server.py::test_calendars_refuses_a_malformed_date_cleanly`.

All thirteen MCP tools also gained `readOnlyHint: true`, since every one of
them is a pure lookup; a strict client can now auto-approve them rather than
prompting a person for a read. `tests/test_mcp_server.py::test_every_tool_is_marked_read_only`.

## Genuinely good news, not just bugs

Several agents reported the tool working as intended in territory tonight's
earlier evaluation never reached:

- **Aggada and liturgy are not second-class inside the mechanics that
  matter most.** `related`, `chain`, and `links --category` correctly
  surfaced Genesis Rabbah, the Zohar, Chasidic readings, and a real
  Talmudic anchor (Chullin 91b) for Jacob's ladder, and correctly connected
  a Siddur blessing to its Talmudic warrant (Taanit 2a, 2a:12, Sanhedrin
  113a) — the one capability the question most needed, and it worked on
  liturgy, not only on Talmud and codes.
- **`study --vocalize` is live, not stubbed, and its judgment calls are
  good.** Tested against a genuinely unpointed Shulchan Arukh edition
  (Lemberg 1893), it produced a fully pointed, defensible reading, correctly
  used the qamats-qatan glyph, and left abbreviations and numerals alone.
- **`study --paired` found a real, substantively correct link** (Mishneh
  Torah, Foundations of the Torah 2:2, to Guide for the Perplexed 3:28) and
  correctly reported absence, rather than guessing, where the link graph
  had nothing.
- **`meturgaman chain` traced hashavat aveidah from Mishnah through Rambam
  to the Shulchan Arukh** and surfaced a real split (Mishnah 2:11 lands in
  both Choshen Mishpat and Yoreh De'ah, and in both Mishneh Torah's
  property-law and honor-law sections) that a memory-based answer would
  have missed.
- **A Rabbi Uziel responsum on dissection**, surfaced by `topics` and
  `sources --text` for a bioethicist with no background in the field,
  relocated the whole bodily-autonomy question away from consent in a way
  neither the asker nor a generic search would have found unprompted.
- **The MCP protocol layer itself behaves correctly under adversarial
  input**: every bad call in the cold-client audit came back as a proper
  `CallToolResult` with `is_error: true`, never a crash or a hung
  connection, and the same session kept serving correct results
  immediately afterward.

## Follow-ups, deliberately not fixed tonight

- **The Yiddish ligature check only catches precomposed ligature
  codepoints**, not the far more common plain two-letter spellings (וו, וי,
  יי) that almost all real Yiddish text actually uses. A good fix needs a
  linguistically grounded way to tell "Hebrew word, plain letters" from
  "Yiddish word, plain letters," and inventing one without a documented
  basis is exactly the kind of quiet guess this project exists to refuse.
- **`chain`'s Talmud category can surface a parallel/echo passage** (shared
  language, not the direct sugya on the mishnah in question) with no signal
  distinguishing it from a genuine sugya link. Worth a look at whether
  Sefaria's own link metadata can support the distinction before building
  anything.
- **The MCP surface has no `audio` tool**, though the CLI's `audio`/
  `read_aloud` capability is real and part of the project's own pitch. A
  client limited to MCP cannot discover it exists.
- **Generic MCP tool names** (`text`, `search`, `links`, `word`) carry real
  collision risk in a multi-server client. A future breaking change, not a
  tonight change.
- **Two adjacent Tanya segments (Iggeret HaKodesh 8:10 and 8:11) returned
  identical English text for different Hebrew.** This looks like a Sefaria
  alignment artifact upstream, not a meturgaman defect; flagged rather than
  chased.

## State at the end

273 tests, up from 263 at the start of this session (244 offline plus 22
network-marked, plus the MCP suite that needs the `mcp` extra installed).
Fresh clone with the `[dev]` extra alone passes 229 offline, with the
dicta- and mcp-dependent tests correctly skipped rather than failed. All
nine confirmed bugs carry a regression test that reproduces the original
failure before asserting the fix.
