# The committed API contracts

Three documents the services publish about themselves, committed here so the
code is written against a recorded spec rather than against anyone's memory of
one, and so a skill running in a sandbox with no browser still has the contract
to hand. Each is verbatim as fetched. Nothing here is edited, because the moment
it is edited it stops being evidence about the service and becomes a claim about
it.

`meturgaman/data/api` is a symlink to this directory, so every packaged build of
the skill carries these files at `scripts/meturgaman/data/api/`.

| File | What it is | Bytes | Retrieved |
|---|---|---|---|
| `sefaria-openapi.json` | Sefaria's OpenAPI 3.0.2 document, 60 paths | 1,218,551 | 2026-08-29 |
| `sefaria-llms.txt` | Sefaria's own index of its documentation, one line per page | 29,793 | 2026-08-06 |
| `hebcal-openapi.json` | Hebcal's OpenAPI document | 54,424 | 2026-08-06 |

Every size and hash below is of the file **as the service serves it**, with LF
line endings. `.gitattributes` marks this directory `-text` so that stays true on
a machine with `core.autocrlf=true`; see the note at the end.

## Provenance

**`sefaria-openapi.json`**

- URL `https://raw.githubusercontent.com/Sefaria/Sefaria-Project/master/docs/openAPI.json`
- SHA-256 `2bd2618411afc668eef1d100da546b04431ce82b984da0ae96823f24a8f890e4`
- The same document that powers the reference at developers.sefaria.org, which
  links to it as its source. It carries every path, every query parameter with
  its type, default and enum, every request body, and the response schemas.

**`sefaria-llms.txt`**

- URL `https://developers.sefaria.org/llms.txt`
- SHA-256 `697b7a5561cea0e4e497bb8a6eff682e000a2ca28cb0bfff0585e4578bb607ac`
- An index rather than a contract: one line per documentation page, each with a
  URL and a sentence. It is the map to the prose, and the prose is where the
  behaviour that no schema records lives. Append `.md` to any of those URLs to
  get the page as markdown.

**`hebcal-openapi.json`**

- URL not recorded when it was committed; the document names itself
  *Hebcal REST APIs*, OpenAPI 3.0.3, CC-BY-4.0, server `https://www.hebcal.com`.
  Hebcal publishes it from its developer APIs page.
- SHA-256 `dc2b20a9763024ebd0c3c7125f5e67297a28fc4d3978d24ab140b0e383607f66`
- Read at import time by `meturgaman/sources/hebcal.py`, which validates its
  parameter names against it rather than trusting the ones in the code.

## Why both a spec and an index, for Sefaria

The OpenAPI document says what the parameters are, and it is better than most:
it records, for instance, that `/api/ref/` answers HTTP 200 with
`is_ref: false` rather than an error status for a string that is no reference at
all, which is the single most important check in the package.

Where it is wrong, it is wrong confidently. Of `version=all` on
`/api/v3/texts/{tref}` it says "get all texts in the required language." What
the service actually does is return an **empty** `versions` array and put the
edition metadata, licences and all, in `available_versions`, so asking for
everything gets you nothing and a second request naming one edition is needed.
That divergence and a dozen others are recorded in
`desktop-skill/references/sefaria-api-traps.md`, each one having been met rather
than anticipated.

Read the spec for what to send, the traps file for what comes back, and believe
the traps file where they disagree.

## Refetching

```
curl -sSL -o docs/api/sefaria-openapi.json \
  https://raw.githubusercontent.com/Sefaria/Sefaria-Project/master/docs/openAPI.json
curl -sSL -o docs/api/sefaria-llms.txt https://developers.sefaria.org/llms.txt
```

Then record the new byte count, SHA-256 and date in the table above, and run
`python tools/build_skill.py --sync`, which copies the file into
`desktop-skill/scripts/meturgaman/data/api/`. That is a real directory rather
than a symlink, because a zip cannot carry one and LawOS builds its online skill
set by copying it whole.

`sefaria-llms.txt` drifts: it is a living index of a documentation site, and
upstream had already moved on from the copy here by 2026-08-29. The hash above is
of what is committed, which is the point of recording it. Refetch when the index
matters; the endpoint list in the OpenAPI document is the stable thing.

## A hash is only worth what the line endings are

The three hashes above were recorded once from Windows working copies and were
wrong, all three, in a way nothing would have caught. `core.autocrlf=true`
rewrites LF to CRLF on checkout, so the bytes on disk were not the bytes the
service served, and a colleague verifying on Linux would have got a mismatch on a
file that was in fact correct. `.gitattributes` now marks this directory and the
vendored copy `-text`, which turns every conversion off. A provenance hash has to
be of the artifact, not of one platform's rendering of it.
