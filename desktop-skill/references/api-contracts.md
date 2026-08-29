# The API contracts, and how to read them without reading them

Three documents ship inside this skill, at `scripts/meturgaman/data/api/`:

| File | What it is | Bytes |
|---|---|---|
| `sefaria-openapi.json` | Sefaria's own OpenAPI 3.0.2 document, 60 paths | 1,218,551 |
| `sefaria-llms.txt` | Sefaria's index of its documentation, one line per page | 29,925 |
| `hebcal-openapi.json` | Hebcal's own OpenAPI document | 55,108 |

**Do not open any of them.** The Sefaria spec alone is over a megabyte and would
swallow the context window whole. Query it instead:

```
python3 scripts/api.py                                # every endpoint, one line each
python3 scripts/api.py texts                          # parameters of everything matching
python3 scripts/api.py --responses api/ref/           # the response shape
python3 scripts/api.py --docs passages                # where the prose about it lives
```

`api.py` reads both specs, prints what it found and nothing else, so a question
about a parameter costs a few hundred tokens rather than thirty thousand. Every
type, default and allowed value it prints came out of the document, so what it
says is what the service publishes about itself.

Sefaria's base is `https://www.sefaria.org`, Hebcal's is
`https://www.hebcal.com`. **Neither takes a key, a token, or a registration.**

## The prose, and why the spec is not enough

`--docs` searches Sefaria's documentation index and prints the page URLs.
Appending `.md` to any of them returns that page as markdown, which is what
makes them readable by a web fetch when the sandbox has egress to that host.

Go there when the spec's answer is a shape rather than a meaning: what a
complex text's schema actually looks like, how commentaries are addressed, how
the topic ontology is organized, what the linker does. `index-and-versions`,
`the-index-schema`, `text-references`, `commentaries` and `topic-ontology` are
the pages worth knowing exist.

**A spec is not a description of behaviour, and this one is sometimes wrong.**
Of `version=all` it says "get all texts in the required language"; what the
service does is return an *empty* `versions` array and put the edition metadata
in `available_versions`. Every divergence anyone here has met is in
`references/sefaria-api-traps.md`. Read the spec for what to send, that file for
what comes back, and believe that file where they disagree.

## What each command is doing underneath

The left column is what to run. The right column is what it would cost to skip
the CLI and call the endpoint directly, which is the reason to prefer the left
column even when the endpoint looks simple.

| Command | Endpoint | What the CLI adds |
|---|---|---|
| `text`, `editions`, `compare` | `GET /api/v3/texts/{tref}` | two-step version fetch, HTML stripping, and `Edition.provider` derived from each version's own stated source, so two editions from one digitization do not count as two witnesses |
| `candidates`, `topics` | `GET /api/name/{name}` | spaces rather than underscores, case-insensitive `type` comparison, and no auto-picking of the first suggestion |
| (every command, first) | `GET /api/ref/{tref}` | the `is_ref` check. The endpoint answers HTTP 200 for a fabricated citation, so the status code alone validates anything |
| `links` | `GET /api/links/{tref}` | category filtering and flattening |
| `related` | `GET /api/related/{tref}` | counts and topic summary |
| `chain` | `GET /api/links/{tref}` | grouping by category and work, in the order the tradition runs |
| `sugya` | `GET /api/passages/{refs}` | mapping a page reference to the passage boundary that crosses it |
| `anchors` | `GET /api/shape/{title}` | the census: every populated anchor with its segment count |
| `sources` | `GET /api/v2/topics/{slug}?with_refs=1` | curated refs in `curatedPrimacy` order, then fetched |
| `word` | `GET /api/words/{word}` | percent-encoding the Hebrew, which `http.client` will otherwise raise on |
| `calendars`, `daf` | `GET /api/calendars` | the learning cycles, named |
| `day`, `leyning`, `zmanim`, `yahrzeit` | Hebcal | parameter names validated against the committed spec at import time |
| `law hebrew`, `law amendments` | `GET he.wikisource.org/w/api.php` | the revision id, and the amendment stamps read out of the text |
| `search` | `POST /api/search-wrapper` | `source_proj: true`, without which every `_source` comes back empty |
| `verify` | `POST /api/find-refs`, then poll | the async handshake, and the consonantal-skeleton comparison |

## The two POST endpoints, and the async handshake

A web fetch cannot POST, so `search` and `verify` exist only when the sandbox
itself has egress. Both are worth knowing in full because both fail quietly.

**`POST /api/search-wrapper`** takes `query`, `type` (the ElasticSearch index:
`text`, `sheet` or `merged`), `field` (`exact` or `naive_lemmatizer`),
`filters` with a matching `filter_fields`, `size`, `slop`, and
`source_proj`. Send `source_proj: true`. Without it the request succeeds, the
hit count is right, and every document body is empty.

**`POST /api/find-refs`** is asynchronous and says so only in its status code.
It returns HTTP 202 and `{"task_id": ...}`. Poll `GET /api/async/{task_id}`,
which returns 202 while the state is `PENDING`, `STARTED` or `RETRY`, 200 with a
`result` field on `SUCCESS`, and 500 with an `error` field on `FAILURE`. Treat
the first response as a receipt, never as an answer.

## Etiquette this skill already keeps

Sefaria is rate limited here to 20 requests a second, Hebcal to 80 in ten
seconds against a published limit of 90, and he.wikisource.org to 10 a second.
Responses are cached for 24 hours, and `--no-cache` on any command forces a
fresh fetch. The client sends
`User-Agent: meturgaman/0.1 (+https://github.com/Oranburg/meturgaman)`.

If you ever call an endpoint by hand rather than through the CLI, keep all four:
identify yourself, stay under the limit, do not hammer a failing host, and
remember that **some of these services answer failures as HTTP 200 with an
`error` key in the body**. Cache one of those and a transient outage lives on
for a day.
