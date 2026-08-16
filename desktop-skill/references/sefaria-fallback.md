# Fetching from Sefaria without the CLI

Read this when `scripts/probe.py` reports that sefaria.org is blocked, so the
bundled CLI cannot fetch anything and Claude's own web fetch has to do the work.

Every URL here is a GET, which is all a web fetch can do. Every one was called
and returned HTTP 200 on 2026-08-10. Read
`references/integrity-on-the-fallback.md` alongside this file: these URLs supply
the text, and that file supplies the rules the CLI would otherwise be enforcing.

## Text by reference, with its edition

This is the only permitted way to fetch a passage.

```
https://www.sefaria.org/api/v3/texts/{ref}?version=source&version=translation&return_format=text_only
```

Worked example:

```
https://www.sefaria.org/api/v3/texts/Genesis_1:1?version=source&version=translation&return_format=text_only
```

returns a `versions` array of two entries. The first is *Miqra according to the
Masorah*, `license: "CC-BY-SA"`, `versionSource` at he.wikisource.org. The
second is *THE JPS TANAKH: Gender-Sensitive Edition*, `license: "CC-BY-NC"`,
`versionSource` at jps.org.

Both reference spellings work: `Bava_Metzia_75b:2` and `Bava_Metzia.75b.2` each
return `ref: "Bava Metzia 75b:2"`.

`return_format` accepts `default`, `text_only`, `strip_only_footnotes` and
`wrap_all_entities`. Always send `text_only`. The other formats return HTML, and
the CLI has a stripping step that the fallback path does not: without it,
footnote markers and entities travel into the Hebrew and then into whatever the
user pastes into a manuscript.

**`version=all` returns no text at all.** On Genesis 1:1 it returns an empty
`versions` array and 50 entries in `available_versions`, each carrying licence
and status but no words. To read a specific edition, make a second request
naming it as `languageFamilyName|versionTitle`, where the language token is the
family name (`hebrew`), not the ISO code (`he`).

## Validating a reference

```
https://www.sefaria.org/api/ref/{ref}
```

`https://www.sefaria.org/api/ref/Bava_Metzia_75b:2` returns `is_ref: true`,
`normalized`, `hebrew`, `url_ref`, `index_title`, `depth`, `section_names`, and
a `navigation_refs` object holding `prev_segment_ref` and `next_segment_ref`.

**A fabricated reference returns HTTP 200.** `Genesis_99:99` returns a body
whose only key is `is_ref: false`. There is no error status and no error
message. Check `is_ref` explicitly on every reference before quoting anything,
because reading the status code alone is exactly how a fabricated citation comes
to look validated.

Note for anyone comparing this against the CLI's source: the live response has
no `heRef` key and no `categories` key, though `sefaria.py` still looks for
both. Read `hebrew` for the Hebrew reference and `navigation_refs` for the
neighbouring segments.

## Finding a topic or a work by name

```
https://www.sefaria.org/api/name/{text}?limit=8
```

`https://www.sefaria.org/api/name/charity?limit=8` returns `completion_objects`,
whose first entries are `{"type": "Topic", "key": "tzedakah", "title":
"Charity"}` and then reference entries such as `Sefer HaMiddot, Charity`. The
`type` values are inconsistently cased between `"Topic"` and `"ref"`, so compare
case-insensitively.

This is the only GET route to topic discovery, and it is how a subject question
starts on this path.

## Topics

```
https://www.sefaria.org/api/v2/topics/{slug}?with_refs=1
```

`https://www.sefaria.org/api/v2/topics/tzedakah?with_refs=1` returns
`primaryTitle`, `numSources`, and `refs.about.refs`, each entry carrying `ref`
and an `order` object with `curatedPrimacy`.

**`numSources` and the length of the reference list disagree**: 693 against 608
in the same document. Any sentence that counts must name which field it counted.

## Links, and what was built on a passage

```
https://www.sefaria.org/api/links/{ref}?with_text=0
https://www.sefaria.org/api/links/{ref}?with_text=0&categories=Commentary,Halakhah
```

`Bava_Metzia_75b:2` returns 16 objects and roughly 89 KB even with
`with_text=0`. Each carries `index_title`, `category`, `type`, `ref`,
`anchorRef`, `sourceHeRef`, `compDate` and `collectiveTitle`.

**Never send `with_text=1` on this path.** The response is already near the size
where a fetch will truncate, and a truncated links payload is the single easiest
way to produce a confident, wrong count.

Grouping those links into transmission order is what the CLI's `chain` command
does. Doing it by hand on this path is your own reading, and it has to be
labelled as your reading rather than as the tool's output.

## The rest

```
https://www.sefaria.org/api/related/{ref}
```
Returns `links`, `sheets`, `notes`, `topics`, `manuscripts`, `media`, `guides`.

```
https://www.sefaria.org/api/passages/{ref}
```
The sugya boundary. `Bava_Metzia_75b:2` returns
`{"Bava_Metzia_75b:2": "Bava Metzia 75a:11-75b:4"}`. **The response is keyed by
the string you sent, not by the normalized reference**, so read the single value
rather than looking up a key you built separately.

```
https://www.sefaria.org/api/words/{word}
```
Dictionary entries; URL-encode the Hebrew. `אסמכתא` returns `headword`,
`parent_lexicon: "Jastrow Dictionary"`, and `content.senses`.

```
https://www.sefaria.org/api/shape/{title}
```
Anchors and segment counts. This is the endpoint behind any sentence that
counts, so if its response looks truncated, report that and count nothing.

```
https://www.sefaria.org/api/calendars?year=&month=&day=&diaspora=1
https://www.sefaria.org/api/v2/index/{title}
```

## Endpoints to avoid, and why

**`/api/bulktext/{ref}` is forbidden.** It is the most convenient GET in the API
and it is the one that breaks the governing rule. `Genesis%201:1` returns keys
`en`, `he`, `heRef`, `lang`, `ref`, `url` and **no `versionTitle` and no
`license`**. It also returns raw markup inside the Hebrew. Text fetched this way
is Hebrew with no edition attached, which is a rumour rather than a citation.

**`/api/texts/{ref}` (v1) is a last resort.** It carries licence metadata, but
in a parallel-field shape (`versionTitle` and `license` for the English,
`heVersionTitle` and `heLicense` for the Hebrew), it returns only two versions,
and it returns HTML. Sefaria's own documentation calls v3 the current way to
retrieve texts.

**`/api/search-wrapper` is POST only**, so there is no full-text search on this
path. A GET returns `{"error": "Unsupported HTTP method."}`. Where no topic
fits, say that full-text search is unavailable here and offer to run it in
Claude Code. A web search of sefaria.org is a permitted way to find where a
subject lives, and its result is a lead: fetch the passage through the v3
endpoint before quoting a word of it.

**`/api/find-refs` is POST plus asynchronous polling**, so the citation-finding
behind `refs` and `verify` has no equivalent here.

## One thing that has not been verified

These endpoints were confirmed with direct HTTPS requests. How Claude's web
fetch renders a large JSON body is not known: it may convert, truncate, or
decline a non-HTML content type. The 89 KB links response and the 608-entry
topic response are both large enough that truncation is a live risk, and that
risk lands directly on any sentence that counts. When a response looks cut off,
say so and count nothing from it.
