# Keeping the discipline when the tool is not enforcing it

Read this whenever a passage is fetched by web fetch rather than by the bundled
CLI, together with `references/sefaria-fallback.md`.

The CLI does not only retrieve text. It refuses on an unresolved reference,
strips markup, builds segment anchors, counts independent witnesses, and reports
each edition's licence. A raw JSON read gives you the words and none of that. On
this path the rules are yours to apply, so here they are as rules rather than as
behaviour.

## Where the metadata lives

Per entry in the `versions` array of a v3 response:

| Field | What it is | What to do with it |
|---|---|---|
| `versionTitle` | the edition name | print it with every quotation |
| `license` | the licence string, verbatim | print it, and set quotation length by it |
| `versionSource` | where the digitization came from | the host is the provider; two editions sharing a host are one witness |
| `status` | `"locked"` is Sefaria's editorial freeze | report separately from the licence, and never as a licence claim |
| `languageFamilyName` | `hebrew`, `english` | this, not the ISO code, is what a second `version=` request accepts |
| `actualLanguage` | ISO code | for filtering by language |
| `versionNotes` | edition description | carries HTML; strip before quoting |

At the top level, `ref` and `heRef` are the reference to copy exactly, and
`warnings` may carry service-side notes worth reading.

## The licence rule, stated in full

Apply this yourself. Do not copy a `quotable` verdict out of CLI output: the
bundled code tests whether the licence string contains `cc-by`, so `CC-BY-NC`
and even `CC-BY-NC-ND` both come back as quotable at length. That is wrong, and
it is wrong for the two editions most often fetched, since the William Davidson
Talmud and the JPS Tanakh are both CC-BY-NC.

- **Public domain, CC0**: quote at length.
- **CC-BY, CC-BY-SA**: quote at length, with attribution to the edition.
- **Anything containing NC or ND, and anything with no licence stated**: short
  quotation and paraphrase, and say in the answer why the quotation is short.

`status: "locked"` is an editorial freeze and says nothing about the licence. A
public-domain edition can be locked and a restricted one need not be. Report the
two separately.

## Counting witnesses

Two versions hosted by Sefaria are not two witnesses if they came from one
digitization. Derive the provider from the host in `versionSource` and count
distinct providers. Two editions both sourced from he.wikisource.org are one
witness, and saying "two editions agree" about them is a claim the evidence does
not support.

## Anchors

The CLI walks the jagged array and builds `Base:1`, `Base:2` anchors from the
index path. A raw fetch gives a bare nested array. Numbering by position is
permitted after reading `depth` and `section_names` from `/api/ref/`, and the
answer has to say that the anchors were derived rather than fetched.

## Refusing on an unresolved reference

Nothing raises on this path. `/api/ref/` returns HTTP 200 with `is_ref: false`
for a fabricated reference, so the refusal has to be a decision rather than an
error you caught.

When a reference does not resolve, fetch `/api/name/{text}?limit=8` and offer
the candidates without choosing among them. The CLI deliberately declines to
pick, and the reason is recorded in its own source: `Hilchot Deot` ranks
`Mishneh Torah, Repentance` first, and an earlier version silently substituted
it. The top hit is often wrong.

## Truncation

This is the rule most likely to be broken quietly, because a truncated JSON
response looks like a complete one that simply had fewer entries.

If a fetched response looks cut off, say so, and count nothing from it. This is
the fallback's version of the standing rule that there is no census without an
enumeration. A links payload for a single Talmud segment runs to roughly 89 KB
and a topic can carry 608 references, so truncation is not a remote possibility.

## Copying the reference

Copy `ref` or `normalized` exactly as returned. Sefaria's segmentation is what
the reader will look up, and renumbering from a remembered edition produces a
citation that does not resolve for anyone else.

## What to say about the path itself

Say once, in the answer, that the passage came from a direct API fetch rather
than from the tool, and name the edition and licence. A reader who knows which
path produced a quotation knows how much checking it has already had.
