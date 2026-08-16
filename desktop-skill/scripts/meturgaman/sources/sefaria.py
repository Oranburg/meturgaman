"""Read from Sefaria.

Sefaria holds the largest open collection of Jewish texts there is, and gives it
away with no key and no registration. This module is the whole of how Meturgaman
talks to it.

Written against the contract, not against memory
------------------------------------------------
`docs/api/sefaria-llms.txt` is Sefaria's own index of every endpoint, committed
to this repository so the code can be checked against what the service actually
publishes rather than against what someone recalled. When Sefaria changes, that
file is what to refetch first.

What this module refuses to do
------------------------------
It never returns a text without its edition, its source and its licence. A
Hebrew passage with no edition named is not a citation, it is a rumour, and the
whole reason for reading from a corpus rather than from memory is to be able to
say where a sentence came from. `Edition.provider` is derived from the version's
own stated source rather than from the fact that Sefaria served it, so two
editions that Sefaria happens to host do not count as two independent witnesses
when they came from the same place.
"""

from __future__ import annotations

import html
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import date as _date
from typing import Any, Iterable

from meturgaman.net import Fetched, NetworkError, RateLimit, get_json, post_json

__all__ = [
    "BASE", "ATTRIBUTION",
    "Ref", "Edition", "Segment", "Observation", "Reading",
    "Topic", "SearchHit", "LexiconEntry",
    "resolve", "read", "editions", "related", "media", "links",
    "passage_boundary",
    "calendars", "name_candidates", "find_refs", "lookup_word",
    "topics", "topic", "topic_sources", "search", "search_topics",
    "shape", "shape_summary", "Anchor", "WorkShape", "index_metadata",
    "VERSION_KEYWORDS", "RETURN_FORMATS",
]

BASE = "https://www.sefaria.org/api"
ATTRIBUTION = (
    "Text from Sefaria (https://www.sefaria.org). Each edition's own licence is "
    "reported with it."
)

#: Sefaria is generous about traffic and states no hard limit. This is
#: self-imposed restraint rather than a published rule.
_LIMIT = RateLimit(requests=20, seconds=1.0, name="sefaria")

#: How many editions to name in one query string. Naming fifty at once
#: builds a URL the server refuses with a 502.
_BATCH = 6

#: The special words the v3 `version` parameter accepts, besides a language name
#: or a `language|versionTitle` pair.
VERSION_KEYWORDS = ("primary", "source", "translation", "all")

#: Every value `return_format` takes, per the v3 documentation.
RETURN_FORMATS = (
    "default",
    "text_only",
    "strip_only_footnotes",
    "wrap_all_entities",
)

_TAG = re.compile(r"<[^>]+>")
_FOOTNOTE = re.compile(r"<i\s+class=\"footnote\".*?</i>", re.S | re.I)


def _clean(value: Any) -> str:
    """Flatten one segment of Sefaria text to plain characters.

    Sefaria's default format carries HTML: footnotes, links, emphasis. Asking
    for `return_format=text_only` is the better fix and this module does, but a
    caller who wants the default format still should not get tags in the middle
    of a Hebrew word.
    """
    if isinstance(value, list):
        return " ".join(_clean(item) for item in value)
    text = str(value or "")
    text = _FOOTNOTE.sub("", text)
    text = _TAG.sub("", text)
    # Sefaria's text carries HTML entities as well as tags: a thin space between
    # a word and a paseq comes through as `&thinsp;`, which would otherwise land
    # in the middle of the Hebrew and travel into every downstream file.
    text = html.unescape(text)
    return " ".join(text.split())


@dataclass(frozen=True)
class Ref:
    """A validated citation."""

    raw: str
    normalized: str
    url_ref: str
    hebrew: str = ""
    is_segment: bool = False
    book: str = ""
    categories: tuple[str, ...] = ()

    def __str__(self) -> str:
        return self.normalized


@dataclass(frozen=True)
class Edition:
    """One version of a work, with everything needed to cite it."""

    title: str
    language: str
    source: str = ""
    license: str = ""
    notes: str = ""
    is_primary: bool = False
    is_source: bool = False
    direction: str = ""
    actual_language: str = ""

    @property
    def provider(self) -> str:
        """Who digitized this, derived from the version's own stated source.

        Two versions Sefaria happens to host are not two witnesses if they came
        from the same digitization. Deriving the provider from `versionSource`
        rather than from the fact of being on Sefaria is what makes the
        independent-witness count in `Reading` mean anything.
        """
        if not self.source:
            return "(none stated)"
        match = re.search(r"https?://([^/]+)", self.source)
        host = match.group(1) if match else self.source
        return host.removeprefix("www.")

    @property
    def is_quotable_at_length(self) -> bool:
        """True when the stated licence permits quoting freely."""
        text = (self.license or "").lower()
        return any(
            token in text
            for token in ("public domain", "cc0", "cc-by", "creative commons")
        )


@dataclass(frozen=True)
class Segment:
    """One verse, mishnah, or line, with the anchor it is cited by."""

    anchor: str
    text: str


@dataclass
class Observation:
    """One edition's reading of a passage."""

    edition: Edition
    segments: list[Segment]
    warnings: list[str] = field(default_factory=list)

    @property
    def joined(self) -> str:
        return " ".join(segment.text for segment in self.segments if segment.text)


@dataclass
class Reading:
    """Every edition of one passage, side by side."""

    ref: Ref
    observations: list[Observation]
    attribution: str = ATTRIBUTION

    @property
    def providers(self) -> tuple[str, ...]:
        seen: list[str] = []
        for observation in self.observations:
            provider = observation.edition.provider
            if provider not in seen:
                seen.append(provider)
        return tuple(seen)

    @property
    def independent_witnesses(self) -> int:
        """How many distinct digitizations are represented, not how many rows."""
        return len(self.providers)

    def in_language(self, language: str) -> list[Observation]:
        wanted = language.lower()
        return [
            observation
            for observation in self.observations
            if wanted in (observation.edition.language or "").lower()
            or wanted in (observation.edition.actual_language or "").lower()
        ]


@dataclass(frozen=True)
class Topic:
    """A subject, with whatever Sefaria knows about it."""

    slug: str
    name: str
    hebrew_name: str = ""
    description: str = ""
    source_count: int = 0
    categories: tuple[str, ...] = ()


@dataclass(frozen=True)
class SearchHit:
    """One result from a full-text search."""

    ref: str
    text: str
    version: str = ""
    language: str = ""
    score: float = 0.0


@dataclass(frozen=True)
class LexiconEntry:
    """A dictionary entry for one word."""

    headword: str
    lexicon: str
    senses: tuple[str, ...] = ()


def _get(path: str, params: dict[str, Any] | None = None, **kwargs: Any) -> Fetched:
    # Percent-encode the path. Several endpoints take Hebrew in the URL, such as
    # `/api/words/צדקה`, and an unencoded one raises inside http.client rather
    # than reaching the network at all.
    # A space in `safe` leaves spaces in the URL and http.client refuses the
    # request before it leaves the machine; a slash lets user input climb out of
    # its path segment. Neither belongs here.
    head, _, tail = path.partition("?")
    path = urllib.parse.quote(head, safe="/:,._-'()[]") + (f"?{tail}" if tail else "")
    return get_json(
        f"{BASE}{path}",
        params,
        limiter=_LIMIT,
        service="sefaria",
        attribution=ATTRIBUTION,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# References
# ---------------------------------------------------------------------------

def _suggestions_for(citation: str) -> list[str]:
    """Spellings Sefaria recognizes that resemble this one.

    Used to make a refusal useful. It does **not** pick one: `Hilchot Deot`
    brings back `Mishneh Torah, Repentance` as its top-ranked reference, which
    is a different book by a different name, and an earlier version of this
    function returned it. Substituting a text the reader did not ask for is
    worse than refusing, because the reader has no way to notice.
    """
    text = " ".join(citation.strip().split())
    match = re.match(r"^(?P<book>.+?)[\s,]+(?P<locator>[\d]+[ab]?([:.]\d+)*)$", text)
    book = match["book"] if match else text
    try:
        payload = _get(f"/name/{book}", {"limit": 8}).payload
    except (NetworkError, LookupError, ValueError):
        return []
    if not isinstance(payload, dict):
        return []
    found: list[str] = []
    for entry in payload.get("completion_objects") or []:
        if (entry.get("type") or "").lower() == "ref":
            title = entry.get("key") or entry.get("title")
            if title and str(title) not in found:
                found.append(str(title))
    for item in payload.get("completions") or []:
        if str(item) not in found:
            found.append(str(item))
    return found[:6]


def resolve(citation: str) -> Ref:
    """Validate a citation and return its canonical form.

    Raises rather than returning something empty. A citation that does not
    resolve is the single most common way to end up quoting the wrong passage,
    and it is worth stopping on.
    """
    citation = citation.strip()
    if not citation:
        raise ValueError("no citation given")

    quoted = citation.replace(" ", "_")
    try:
        found = _get(f"/ref/{quoted}").payload
    except NetworkError as error:
        raise LookupError(
            f"{citation!r} did not resolve. Try `meturgaman candidates "
            f"{citation!r}` for what Sefaria thinks you might mean.\n  {error}"
        ) from error

    if not isinstance(found, dict) or found.get("error"):
        raise LookupError(f"{citation!r} did not resolve: {found}")

    # The endpoint answers HTTP 200 with `is_ref: false` for a string that is
    # not a reference, and sets no error key. Without this check every
    # fabricated citation validated, which is the exact failure this whole
    # project is built against.
    if found.get("is_ref") is False:
        # Refuse, and make the refusal useful by naming what Sefaria thinks it
        # might be. Deliberately without choosing: `Hilchot Deot` ranks
        # `Mishneh Torah, Repentance` first, which is a different book, and a
        # fabricated title brings back a real one. Picking the top suggestion
        # would answer a question nobody asked, and the reader would have no
        # way to see that it had happened.
        suggestions = _suggestions_for(citation)
        detail = ""
        if suggestions:
            detail = "\n  Did you mean:\n    " + "\n    ".join(suggestions)
        raise LookupError(
            f"{citation!r} is not a reference Sefaria recognizes.{detail}"
        )

    navigation = found.get("navigation_refs") or {}
    path = navigation.get("shortest_path_to_root") or []
    normalized = citation
    for candidate in (found.get("ref"), found.get("normalized"), citation):
        if candidate:
            normalized = str(candidate)
            break

    return Ref(
        raw=citation,
        normalized=normalized,
        url_ref=normalized.replace(" ", "_"),
        hebrew=str(found.get("heRef") or found.get("he") or ""),
        is_segment=bool(found.get("prev_segment_ref") or found.get("next_segment_ref")),
        book=str(path[-1]) if path else "",
        categories=tuple(str(item) for item in (found.get("categories") or [])),
    )


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------

def read(
    citation: str | Ref,
    *,
    version: str | Iterable[str] = ("source", "translation"),
    return_format: str = "text_only",
    fill_in_missing_segments: bool = False,
    max_editions: int = 12,
) -> Reading:
    """Fetch a passage in one or many editions.

    `version` takes the full v3 grammar and every form of it is reachable:

        version="hebrew"                    the primary Hebrew version
        version="english"                   the primary English version
        version="source"                    whatever the original language is
        version="translation"               any translation
        version="primary"                   the highest-priority version
        version="all"                       every version there is
        version="hebrew|Miqra according to the Masorah"
        version=["hebrew", "english"]       two at once, in one request

    `return_format` takes any of `RETURN_FORMATS`. The default here is
    `text_only`, because Sefaria's own default carries HTML footnote markup that
    lands in the middle of the Hebrew.

    One thing worth knowing, because it is surprising and undocumented:
    `version="all"` does **not** return every edition's text. It returns an
    empty `versions` list and fills `available_versions` with metadata instead,
    so asking for `all` naively gets you nothing at all. This function therefore
    treats `all` as a two-step request: ask what exists, then ask for each one by
    its `language|versionTitle` name.
    """
    ref = citation if isinstance(citation, Ref) else resolve(str(citation))

    for wanted in ([version] if isinstance(version, str) else list(version)):
        text = str(wanted)
        if text in VERSION_KEYWORDS:
            continue
        if "|" in text and text.split("|", 1)[0].strip():
            continue
        if text.isalpha():
            continue  # a bare language name such as `hebrew`
        raise ValueError(
            f"version={text!r} is not valid. Use one of "
            f"{', '.join(VERSION_KEYWORDS)}, a language name such as 'hebrew', "
            f"or 'language|Version Title'."
        )

    if return_format not in RETURN_FORMATS:
        raise ValueError(
            f"return_format must be one of {', '.join(RETURN_FORMATS)}, "
            f"not {return_format!r}"
        )

    versions = [version] if isinstance(version, str) else list(version)

    def fetch(wanted: list[str]) -> dict[str, Any]:
        params: dict[str, Any] = {
            "version": wanted,
            "return_format": return_format,
        }
        if fill_in_missing_segments:
            params["fill_in_missing_segments"] = 1
        found = _get(f"/v3/texts/{ref.url_ref}", params).payload
        if not isinstance(found, dict):
            raise LookupError(f"unexpected reply for {ref.normalized}")
        if found.get("error"):
            raise LookupError(f"{ref.normalized}: {found['error']}")
        return found

    payload = fetch(versions)

    if not payload.get("versions") and payload.get("available_versions"):
        # `all` lists rather than fetches. Turn the listing into explicit
        # requests by `language|versionTitle`, which do return the text.
        #
        # Two practical limits. Genesis 1:1 has around fifty editions, and
        # naming them all in one query string builds a URL long enough that the
        # server answers 502, so the names go out in batches. And fifty
        # editions of one verse is not a comparison anyone reads, so the source
        # language comes first and the rest are capped.
        available = list(payload["available_versions"])
        available.sort(
            key=lambda entry: (
                not entry.get("isSource"),
                not entry.get("isPrimary"),
                -float(entry.get("priority") or 0),
            )
        )
        # The `version` parameter wants the full English language name, and the
        # listing reports the ISO code. `hebrew|Miqra according to the Masorah`
        # returns the text; `he|Miqra according to the Masorah` returns nothing
        # at all, with no error to say why. `languageFamilyName` is the field
        # that carries the form the parameter accepts.
        named: list[str] = []
        for entry in available[:max_editions]:
            language = entry.get("languageFamilyName")
            title = entry.get("versionTitle")
            if language and title:
                named.append(f"{language}|{title}")

        merged: list[dict[str, Any]] = []
        for start in range(0, len(named), _BATCH):
            batch = fetch(named[start : start + _BATCH])
            merged.extend(batch.get("versions") or [])
        if merged:
            payload = dict(payload)
            payload["versions"] = merged

    observations: list[Observation] = []
    for entry in payload.get("versions") or []:
        edition = Edition(
            title=str(entry.get("versionTitle") or "(untitled)"),
            language=str(entry.get("language") or ""),
            source=str(entry.get("versionSource") or ""),
            license=str(entry.get("license") or ""),
            notes=_clean(entry.get("versionNotes")),
            is_primary=bool(entry.get("isPrimary")),
            is_source=bool(entry.get("isSource")),
            direction=str(entry.get("direction") or ""),
            actual_language=str(entry.get("actualLanguage") or ""),
        )
        segments = _segments(entry.get("text"), ref.normalized)
        warnings: list[str] = []
        if entry.get("status") == "locked":
            # Sefaria's own editorial freeze on this version, unrelated to
            # copyright. A public-domain edition can be locked, and a
            # restrictively licensed one can be unlocked; the licence is
            # reported separately below and is the thing worth checking for
            # quoting rights. Wording this as a licence warning made a fully
            # quotable public-domain text read as a rights concern.
            warnings.append(
                "Sefaria has frozen this version against further edits or "
                "corrections; that lock says nothing about the licence, "
                "which is reported on its own line"
            )
        if not edition.license:
            warnings.append("no licence stated for this edition")
        if not segments:
            warnings.append("this edition has no text at this reference")
        observations.append(
            Observation(edition=edition, segments=segments, warnings=warnings)
        )

    if not observations:
        raise LookupError(
            f"no edition of {ref.normalized} matched version={versions!r}. "
            f"Try version='all' to see what exists."
        )

    return Reading(ref=ref, observations=observations)


def _segments(payload: Any, base: str) -> list[Segment]:
    """Flatten Sefaria's nested text into anchored segments.

    Sefaria returns a jagged array whose depth depends on the reference: a
    single verse is a string, a chapter is a list, a whole book is a list of
    lists. Flattening while keeping the index path is what lets each line keep a
    citable anchor rather than becoming an anonymous blob.
    """
    segments: list[Segment] = []

    def walk(node: Any, path: tuple[int, ...]) -> None:
        if node is None:
            return
        if isinstance(node, str):
            text = _clean(node)
            if not text:
                return
            anchor = base if not path else f"{base}:{':'.join(str(i + 1) for i in path)}"
            segments.append(Segment(anchor=anchor, text=text))
            return
        if isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, path + (index,))

    walk(payload, ())
    return segments


def editions(citation: str | Ref) -> list[Edition]:
    """Every version of a work, with its metadata."""
    ref = citation if isinstance(citation, Ref) else resolve(str(citation))
    payload = _get(
        f"/v3/texts/{ref.url_ref}", {"version": "all", "return_format": "text_only"}
    ).payload
    rows = []
    if isinstance(payload, dict):
        rows = payload.get("available_versions") or payload.get("versions") or []
    return [
        Edition(
            title=str(entry.get("versionTitle") or "(untitled)"),
            language=str(entry.get("language") or ""),
            source=str(entry.get("versionSource") or ""),
            license=str(entry.get("license") or ""),
            notes=_clean(entry.get("versionNotes")),
            actual_language=str(entry.get("actualLanguage") or ""),
        )
        for entry in rows
    ]


# ---------------------------------------------------------------------------
# What a passage connects to
# ---------------------------------------------------------------------------

def related(citation: str | Ref) -> dict[str, Any]:
    """Everything Sefaria links to a reference: commentary, sheets, topics, media."""
    ref = citation if isinstance(citation, Ref) else resolve(str(citation))
    return _get(f"/related/{ref.url_ref}").payload


def media(citation: str | Ref) -> list[dict[str, Any]]:
    """Audio recordings attached to a reference.

    This is where recorded Torah reading lives. Each entry carries a URL and, for
    PocketTorah, `start_time` and `end_time` marking the verse inside a longer
    file. Most of the library has none; the Torah has most of what there is.
    """
    payload = related(citation)
    found = payload.get("media") if isinstance(payload, dict) else None
    return list(found or [])


def links(
    citation: str | Ref,
    *,
    categories: Iterable[str] | None = None,
    with_text: bool = False,
) -> list[dict[str, Any]]:
    """Texts connected to a reference: commentary, targum, midrash, parallels.

    This is how a cross-text pairing gets evidenced from Sefaria's own link graph
    rather than from a memory of what commentaries exist. `categories` filters
    server-side and takes Sefaria's own category names, such as `Commentary`,
    `Targum`, `Midrash`, `Halakhah`.

    `related()` returns this and much else in one call; this is the narrow
    version for when the link graph is what you want.
    """
    ref = citation if isinstance(citation, Ref) else resolve(str(citation))
    params: dict[str, Any] = {"with_text": 1 if with_text else 0}
    if categories:
        params["categories"] = ",".join(categories)
    payload = _get(f"/links/{ref.url_ref}", params).payload
    return list(payload or [])


def passage_boundary(citation: str | Ref) -> str | None:
    """The sugya containing a Talmud reference, when one is mapped.

    A page of Talmud is a physical unit, not an argument. This maps a reference
    to the whole passage it belongs to, so a quotation can be checked against
    where the discussion actually starts and stops.
    """
    ref = citation if isinstance(citation, Ref) else resolve(str(citation))
    payload = _get(f"/passages/{ref.url_ref}").payload
    if isinstance(payload, dict):
        found = payload.get(ref.normalized) or payload.get(ref.url_ref)
        if found:
            return str(found)
        # No fallback to "whatever string is in there": a mapping for a
        # different ref is not an answer to this one.
    return None


# ---------------------------------------------------------------------------
# Finding things
# ---------------------------------------------------------------------------

def name_candidates(text: str, *, limit: int = 10) -> list[dict[str, Any]]:
    """Ranked guesses for a name, for a person to choose from.

    Deliberately returns the list rather than the top hit. Sefaria's ranking is
    good but not authoritative: `Hilchot Deot` comes back with
    `Mishneh Torah, Repentance` first.
    """
    payload = _get(f"/name/{text}", {"limit": limit}).payload
    if not isinstance(payload, dict):
        return []
    return list(payload.get("completion_objects") or [])


def find_refs(text: str) -> list[dict[str, Any]]:
    """Find citations inside arbitrary prose.

    Point this at a paragraph and it returns the references it recognizes, which
    is how a draft's citations get checked without reading them one at a time.
    """
    body = {"text": {"body": text, "title": ""}}
    payload = post_json(
        f"{BASE}/find-refs",
        body,
        limiter=_LIMIT,
        service="sefaria",
        attribution=ATTRIBUTION,
        use_cache=False,
    ).payload
    if not isinstance(payload, dict):
        return []

    # The endpoint became asynchronous: it answers with a task id and the work
    # happens afterwards. Reading the reply as though it held the results gave
    # an empty list and a success exit code, so a whole feature reported
    # "no citations found" for every input.
    task_id = payload.get("task_id")
    if task_id:
        payload = _await_task(str(task_id))
        if payload is None:
            raise LookupError(
                "Sefaria accepted the text but the reference-finding task did "
                "not finish in time. Try again, or with a shorter passage."
            )

    found: list[dict[str, Any]] = []
    for section in ("body", "title"):
        part = payload.get(section) or {}
        if isinstance(part, dict):
            found.extend(part.get("results") or [])
    return found


def _await_task(task_id: str, *, attempts: int = 15, pause: float = 1.0) -> dict[str, Any] | None:
    """Poll an async task until it finishes, or give up and say so.

    `GET /api/async/{task_id}` reports `state` and `ready`, and carries the
    result once `state` is SUCCESS.
    """
    import time

    for _ in range(attempts):
        time.sleep(pause)
        status = _get(f"/async/{task_id}", use_cache=False).payload
        if not isinstance(status, dict):
            continue
        state = str(status.get("state") or "")
        if state == "SUCCESS":
            result = status.get("result")
            return result if isinstance(result, dict) else {}
        if state == "FAILURE":
            raise LookupError(
                f"Sefaria's reference finder failed: {status.get('error') or 'no reason given'}"
            )
    return None


def search(
    query: str,
    *,
    limit: int = 10,
    filters: Iterable[str] | None = None,
    field: str = "naive_lemmatizer",
    text_type: str = "text",
) -> list[SearchHit]:
    """Search the full text of the library.

    This is the blunt instrument and it is often the right one: a phrase, a word,
    a name. `filters` narrows by category path, for example
    `["Talmud", "Bavli"]` or `["Halakhah"]`.
    """
    # `source_proj` is what makes the reply carry the fields rather than just
    # scores. Without it every `_source` comes back empty and the results are
    # unusable, which is not obvious from the response shape.
    body: dict[str, Any] = {
        "query": query,
        "type": text_type,
        "size": limit,
        "field": field,
        "source_proj": True,
        "filters": list(filters) if filters else [],
        "filter_fields": [],
    }
    if filters:
        body["filter_fields"] = ["path"] * len(body["filters"])

    payload = post_json(
        f"{BASE}/search-wrapper",
        body,
        limiter=_LIMIT,
        service="sefaria",
        attribution=ATTRIBUTION,
    ).payload

    hits: list[SearchHit] = []
    rows = ((payload or {}).get("hits") or {}).get("hits") or []
    for row in rows:
        source = row.get("_source", {}) or {}
        highlight = row.get("highlight", {}) or {}
        snippet = ""
        for values in highlight.values():
            if values:
                snippet = _clean(values[0])
                break
        hits.append(
            SearchHit(
                ref=str(source.get("ref") or row.get("_id") or ""),
                text=snippet or _clean(source.get("exact") or source.get("naive_lemmatizer")),
                version=str(source.get("version") or ""),
                language=str(source.get("lang") or ""),
                score=float(row.get("_score") or 0.0),
            )
        )
    return hits


# ---------------------------------------------------------------------------
# Topics: what the tradition has to say about a subject
# ---------------------------------------------------------------------------

def topics(*, limit: int = 0) -> list[Topic]:
    """Every topic in Sefaria's ontology.

    Large. `topic_sources` is usually what you want instead, once you know the
    slug you are after.
    """
    payload = _get("/topics", {"limit": limit} if limit else None).payload
    rows = payload if isinstance(payload, list) else []
    found: list[Topic] = []
    for row in rows:
        primary = row.get("primaryTitle") or {}
        found.append(
            Topic(
                slug=str(row.get("slug") or ""),
                name=str(primary.get("en") or row.get("slug") or ""),
                hebrew_name=str(primary.get("he") or ""),
                description=_clean((row.get("description") or {}).get("en")),
                source_count=int(row.get("numSources") or 0),
            )
        )
    return found


def topic(slug: str) -> Topic:
    """One topic's metadata."""
    payload = _get(f"/v2/topics/{slug}").payload
    if not isinstance(payload, dict) or payload.get("error") or not payload:
        # An unknown slug comes back as `{}`, which is a dict and carries no
        # error, so without the emptiness check this returned a Topic named
        # after whatever was asked for.
        raise LookupError(f"no topic {slug!r}")
    primary = payload.get("primaryTitle") or {}
    return Topic(
        slug=slug,
        name=str(primary.get("en") or slug),
        hebrew_name=str(primary.get("he") or ""),
        description=_clean((payload.get("description") or {}).get("en")),
        source_count=int(payload.get("numSources") or 0),
        categories=tuple(
            str(item) for item in (payload.get("categories") or []) if item
        ),
    )


def topic_sources(slug: str, *, limit: int = 20) -> list[str]:
    """The passages Sefaria's editors curated for a topic, best first.

    This is the answer to "what does the tradition say about X". It is a curated
    list rather than a search result, which makes it a much better starting point
    than full-text search for a subject anyone has thought about before.
    """
    payload = _get(f"/v2/topics/{slug}", {"with_refs": 1}).payload
    if not isinstance(payload, dict):
        return []
    refs: list[str] = []
    for entry in ((payload.get("refs") or {}).get("about") or {}).get("refs") or []:
        ref = entry.get("ref") if isinstance(entry, dict) else entry
        if ref and ref not in refs:
            refs.append(str(ref))
        if len(refs) >= limit:
            break
    if not refs:
        # Older shape: a flat list under `sources`.
        for entry in payload.get("sources") or []:
            ref = entry.get("ref") if isinstance(entry, dict) else entry
            if ref and ref not in refs:
                refs.append(str(ref))
            if len(refs) >= limit:
                break
    return refs


def search_topics(query: str, *, limit: int = 10) -> list[Topic]:
    """Find topics whose name matches a phrase, via the autocompleter."""
    found: list[Topic] = []
    for entry in name_candidates(query, limit=limit * 3):
        if (entry.get("type") or "").lower() != "topic":
            continue
        found.append(
            Topic(
                slug=str(entry.get("key") or ""),
                name=str(entry.get("title") or entry.get("key") or ""),
                hebrew_name=str(entry.get("he") or ""),
            )
        )
        if len(found) >= limit:
            break
    return found


# ---------------------------------------------------------------------------
# Words, structure, calendar
# ---------------------------------------------------------------------------

def lookup_word(word: str, *, lookup_ref: str = "") -> list[LexiconEntry]:
    """Dictionary entries for a Hebrew or Aramaic word."""
    params = {"lookup_ref": lookup_ref} if lookup_ref else None
    payload = _get(f"/words/{word}", params).payload
    rows = payload if isinstance(payload, list) else []
    entries: list[LexiconEntry] = []
    for row in rows:
        content = row.get("content") or {}
        senses: list[str] = []
        for sense in content.get("senses") or []:
            definition = _clean(sense.get("definition"))
            if definition:
                senses.append(definition)
        if not senses:
            definition = _clean(content.get("definition"))
            if definition:
                senses.append(definition)
        entries.append(
            LexiconEntry(
                headword=str(row.get("headword") or word),
                lexicon=str(row.get("parent_lexicon") or ""),
                senses=tuple(senses),
            )
        )
    return entries


def calendars(*, date: str = "", diaspora: bool = True) -> dict[str, Any]:
    """Sefaria's own daily learning schedule: parashah, daf yomi, and the rest."""
    params: dict[str, Any] = {"diaspora": 1 if diaspora else 0}
    if date:
        # A strict ISO parse, not a `.split("-")` unpack: a malformed string
        # with no hyphens once raised a raw "not enough values to unpack",
        # and a string with exactly two hyphens but nonsense fields (e.g.
        # "not-a-date") unpacked into garbage and reached the service
        # silently rather than being refused.
        try:
            parsed = _date.fromisoformat(date)
        except ValueError as error:
            raise ValueError(
                f"{date!r} is not a date in YYYY-MM-DD form: {error}"
            ) from error
        params.update({"year": parsed.year, "month": parsed.month, "day": parsed.day})
    return _get("/calendars", params).payload


def shape(title: str) -> Any:
    """The shape of a work: how many chapters, how many verses in each."""
    return _get(f"/shape/{title.replace(' ', '_')}").payload


@dataclass(frozen=True)
class Anchor:
    """One populated place in a work: where it is, and how many segments."""

    reference: str
    segments: int


@dataclass(frozen=True)
class WorkShape:
    """A work's populated anchors, counted from the service's shape record.

    This exists so a count can be made from data instead of from memory.
    An answer once described a work's glosses "in nine places" from memory
    and was wrong; enumerating the shape record is what makes a census
    sentence checkable.
    """

    title: str
    chapters: int
    anchors: tuple[Anchor, ...]

    @property
    def populated(self) -> int:
        return len(self.anchors)

    @property
    def total_segments(self) -> int:
        return sum(anchor.segments for anchor in self.anchors)


def shape_summary(payload: Any) -> list[WorkShape]:
    """Turn a raw shape payload into countable anchors. Pure, no network.

    The service's `chapters` value is an int per chapter for evenly gridded
    works, and a list per chapter for sparse ones, where each entry is the
    segment count at that position and zero means nothing is there. Both
    forms reduce to the same question: which positions hold text, and how
    much.
    """
    works: list[WorkShape] = []
    for record in payload if isinstance(payload, list) else [payload]:
        if not isinstance(record, dict):
            continue
        title = str(record.get("title") or record.get("book") or "(untitled)")
        chapters = record.get("chapters")
        anchors: list[Anchor] = []
        if isinstance(chapters, list):
            for chapter_index, chapter in enumerate(chapters, start=1):
                if isinstance(chapter, list):
                    for position, count in enumerate(chapter, start=1):
                        if isinstance(count, int) and count > 0:
                            anchors.append(Anchor(
                                reference=f"{chapter_index}:{position}",
                                segments=count,
                            ))
                elif isinstance(chapter, int) and chapter > 0:
                    anchors.append(Anchor(
                        reference=str(chapter_index), segments=chapter
                    ))
        works.append(WorkShape(
            title=title,
            chapters=len(chapters) if isinstance(chapters, list) else 0,
            anchors=tuple(anchors),
        ))
    return works


def index_metadata(title: str) -> Any:
    """A work's record: categories, structure, authors, description."""
    return _get(f"/v2/index/{title.replace(' ', '_')}").payload
