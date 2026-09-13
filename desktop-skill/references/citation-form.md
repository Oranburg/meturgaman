How to cite a passage once it has been fetched, as distinct from how to fetch
it. Written 2026-09-13 after building a bibliographic record type for 71
passages and finding that meturgaman's own references said nothing about
citation form — `quoting-conventions.md` covers editions, romanization and
registers, `corpus-and-chains.md` covers navigation, and neither reaches the
question of what string names the work or the locator in a citation.

Everything here was checked live against Sefaria's index API and the Library
of Congress name authority file on 2026-09-13, not recalled. Where a claim
rests on a source this project could not open (the SBL Handbook itself was
behind a 403 on both PDFs), that is stated, not hidden behind a confident
sentence.

## The locator: cite the received division, not the digital segmentation

A digital edition's segment numbers exist to fetch text. They are not always
the citation a reader holding a printed volume can follow. The two coincide
for the Bavli, the Mishnah, the Yerushalmi, the Tanakh, and the codes —
Sefaria's own ref for `Sanhedrin 98a:12-13` or `Isaiah 60:22` already is the
traditional locator. They diverge on the Zohar, and probably on any other
complex-structure text whose print pagination and digital segmentation were
built independently.

**The trap.** `Zohar I:117a` and `Zohar 1:117a` both answer `is_ref: true` and
both silently normalize to `"Zohar"`, the book, not the passage — see the
trap of the same name in `sefaria-api-traps.md`. Fetching text requires the
segmented form (`Zohar, Vayera 30:445`).

**Getting the traditional daf back out.** Fetch the index record
(`GET /api/v2/raw/index/Zohar`) and read `alt_structs.Daf`. Its top nodes are
titled `Volume I`, `Volume II`, `Volume III` (Sefaria's own Roman-numeral
strings — not invented here). Each is an `ArrayMapNode` carrying a
`startingAddress` (the first daf the node covers) and an ordered `refs` list,
one entry per daf side. The daf for any segment is the `startingAddress`
counted forward by the segment's position in that node's `refs` list. This is
computed from the index record Sefaria already serves, not renumbered from a
remembered edition — it satisfies the tool's own rule against supplying a
citation from memory.

Two things to watch when doing this:

- **A parasha can have more than one ArrayMapNode**, when a later stratum
  (the Ra'aya Mehemna in Nasso, for one) is interleaved with the main text.
  The nodes can disagree on which daf a given segment lands on. Report both
  and let a person choose, the same discipline the tool already applies to
  Sefaria's ranked name suggestions.
- **A ref spanning a whole chapter** (`Zohar, Balak 47`, no segment number)
  may cross a daf boundary; the daf is only exact for a single segment.
  Narrow to a segment before citing a daf.

**The rule, stated once.** Cite the work by its own divisions; let the digital
edition be the access path. Record both: the traditional locator as the
citation, the fetched ref as the machine-verifiable retrieval key, so a
reader with a printed volume and a reader following the link both land on the
passage.

## The work: name it as its own tradition names it, once

Do not compose a corpus prefix onto a tractate name (`Talmud Bavli, Sanhedrin`,
`Talmud Yerushalmi, Berakhot`). Checked live against three index records:

- Sanhedrin's own `title` is `"Sanhedrin"`. The corpus lives in `categories`
  (`["Talmud", "Bavli", "Seder Nezikin"]`), not in the title. None of its
  thirteen listed title variants composes the corpus word onto the name.
- Mishnah Sotah's own `title` is `"Mishnah Sotah"` — the prefix is already
  part of the title, with no comma.
- Jerusalem Talmud Berakhot's own `title` is `"Jerusalem Talmud Berakhot"` —
  same pattern, no comma.

So the corpus distinction Sefaria itself makes is: the Mishnah and the
Yerushalmi carry their prefix inside the title with no comma; the Bavli
carries none at all, because a bare tractate name with a daf-and-side locator
can only be the Bavli. Fetch `index_record.title` verbatim and stop there. If
a corpus label is wanted separately, take it from `categories`, which
resolves the same ambiguity a different way and is already on the record
Sefaria returns.

**Not fully grounded, said plainly.** SBL Handbook of Style 2nd ed. §8.3.8
governs Mishnaic and Talmudic abbreviations; SBL Press's own blog post on it
(sblhs2.com, checked live) uses the shape `m. Bava Metzi'a` — a one-letter
siglum, a tractate name, no corpus word — which is the same shape Sefaria's
own titles already produce. That corroborates the pattern above but is not a
quotation of the Handbook itself, which returned HTTP 403 from sbl-site.org
on both the full text and its free student supplement when checked. Confirm
against a held copy before treating the specific sigla (`m.` `t.` `b.` `y.`)
as quoted rather than inferred.

## The author: a work with no stated author is not a work with a corporate one

Sefaria's index API distinguishes a work with `authors: []` from a work with
one stated. Checked live: Sanhedrin, Mishnah Sotah, Genesis, and the Zohar all
return `authors: []` — present, empty, not absent. Mishneh Torah returns
`authors: ["rambam"]`.

Do not fill Author for the Tanakh, the Mishnah, either Talmud, the classical
midrashim, or the Zohar with something like "the Sages" or "the Babylonian
Talmud." The Library of Congress name authority file establishes **Talmud**
at `n80020282` (`id.loc.gov`, checked live) typed as a title authority, not a
personal or corporate name — the Talmud is a uniform title, entered under its
title, with no author heading at all. That matches Sefaria's own position
rather than contradicting it. A traditional attribution (Judah ha-Nasi as
redactor of the Mishnah) is a historical claim for prose or a notes field,
never an author field; neither Sefaria's index nor the Library of Congress
authority record makes that attribution in the author slot.

**Resolving an author slug to a citable name.** Where `authors` is non-empty,
the value is a topic slug (`rambam`, `joseph-karo`), not a name — fetch
`GET /api/topics/{slug}` and read `primaryTitle.en`. That gives a readable
name and, often, birth-death years, but not necessarily the form a library
catalogue would use: checked live, Sefaria gives Rambam's dates as 1137-1204
while the Library of Congress name authority record gives 1135-1204. Where the
library catalogue form matters, look up the person at `id.loc.gov` rather than
trusting either source alone; where it doesn't, the Sefaria form is
attributed and traceable, which is what matters most.
