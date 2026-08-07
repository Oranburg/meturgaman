"""The command line.

Every documented option of every service is reachable from here. That is a
deliberate constraint rather than completeness for its own sake: a tool that
exposes only the options its author happened to need is a tool that has to be
edited before it can answer a new question.

Refusals go to stderr with a reason and a non-zero exit. An empty result that
looks like an answer is the failure mode this whole project is built against.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from datetime import date

from meturgaman import __version__

__all__ = ["main"]


def _print_flags(flags, prefix: str = "  ") -> None:
    for flag in flags:
        print(f"{prefix}{flag}", file=sys.stderr)


def _emit_json(data) -> int:
    """Print one JSON document to stdout, for a script or another program.

    Every value passes through `_plain` first, so dataclasses arrive as
    objects rather than as their repr strings. Flags and warnings live inside
    the document under their own keys: a consumer of `--json` is not reading
    stderr, and an uncertainty that only went to stderr would be an
    uncertainty silently dropped.
    """
    print(json.dumps(_plain(data), ensure_ascii=False, indent=2, default=str))
    return 0


def _plain(value):
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {key: _plain(item) for key, item in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _positive_limit(text: str) -> int:
    """An argparse type for --limit: a whole number from 1 to 100.

    Unbounded values went straight into a service's query and came back as an
    HTTP 500, which read as the service failing rather than the input.
    """
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a whole number")
    if not 1 <= value <= 100:
        raise argparse.ArgumentTypeError("limit must be between 1 and 100")
    return value


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------

def _text(arguments) -> int:
    from meturgaman.sources import sefaria

    reading = sefaria.read(
        arguments.citation,
        version=arguments.version or ("source", "translation"),
        return_format=arguments.format,
        fill_in_missing_segments=arguments.fill_gaps,
        max_editions=arguments.max_editions,
    )
    if arguments.json:
        return _emit_json({
            "ref": reading.ref,
            "independent_witnesses": reading.independent_witnesses,
            "providers": list(reading.providers),
            "editions": [
                {
                    "edition": observation.edition,
                    "warnings": observation.warnings,
                    "segments": observation.segments,
                }
                for observation in reading.observations
            ],
            "attribution": reading.attribution,
        })
    print(reading.ref.normalized)
    if reading.ref.hebrew:
        print(reading.ref.hebrew)
    print(
        f"{len(reading.observations)} editions, "
        f"{reading.independent_witnesses} independent witnesses"
    )
    print(f"providers: {', '.join(reading.providers)}")
    print()
    for observation in reading.observations:
        edition = observation.edition
        print(f"--- {edition.title}")
        print(f"    language   {edition.language} ({edition.actual_language})")
        print(f"    source     {edition.source or '(none stated)'}")
        print(f"    licence    {edition.license or '(unstated)'}")
        print(
            f"    quotable   "
            f"{'yes' if edition.is_quotable_at_length else 'check the licence'}"
        )
        for warning in observation.warnings:
            print(f"    warning    {warning}")
        if arguments.full:
            for segment in observation.segments:
                print(f"    {segment.anchor}")
                print(f"      {segment.text}")
        elif observation.segments:
            preview = observation.segments[0].text
            # A cut without a mark reads as the whole ruling. This is exactly
            # the shape of error the project exists to prevent, so a clipped
            # preview says so rather than looking complete.
            if len(preview) > 200:
                preview = preview[:200] + "… (--full for the rest)"
            print(f"      {preview}")
        print()
    print(reading.attribution)
    return 0


def _editions(arguments) -> int:
    from meturgaman.sources import sefaria

    if arguments.json:
        return _emit_json({"editions": sefaria.editions(arguments.citation)})
    for edition in sefaria.editions(arguments.citation):
        print(f"{edition.language:6} {edition.title}")
        print(
            f"       {edition.provider}  |  {edition.license or '(unstated)'}  |  "
            f"{'quotable' if edition.is_quotable_at_length else 'check the licence'}"
        )
    return 0


def _compare(arguments) -> int:
    from meturgaman.compare import compare
    from meturgaman.sources import sefaria

    reading = sefaria.read(arguments.citation, version="all", max_editions=arguments.max_editions)
    comparison = compare(reading, language=arguments.language)
    if arguments.json:
        return _emit_json(comparison)
    print(comparison.report())
    return 0


def _links(arguments) -> int:
    from meturgaman.sources import sefaria

    ref = sefaria.resolve(arguments.citation)
    found = sefaria.links(ref, categories=arguments.category or None)
    if arguments.json:
        return _emit_json({"ref": ref.normalized, "links": found})
    if not found:
        if arguments.category:
            # "Nothing links" was false whenever a category filter was the
            # reason for the empty list: the ref can carry other links the
            # filter excluded, and the message should not claim otherwise.
            categories = ", ".join(arguments.category)
            print(f"no {categories} links for {ref.normalized}", file=sys.stderr)
        else:
            print(f"nothing links to {ref.normalized}", file=sys.stderr)
        return 1
    if arguments.refs_only:
        for link in found:
            if link.get("ref"):
                print(link["ref"])
        return 0
    print(f"{ref.normalized}: {len(found)} links")
    by_work: dict[tuple[str, str], list[str]] = {}
    for link in found:
        collective = link.get("collectiveTitle") or {}
        work = collective.get("en") if isinstance(collective, dict) else ""
        work = work or str(link.get("index_title") or "(unnamed)")
        key = (str(link.get("category") or "(uncategorized)"), work)
        if link.get("ref"):
            by_work.setdefault(key, []).append(str(link["ref"]))
    for (category, work), refs in sorted(by_work.items()):
        print(f"  [{category}] {work} ({len(refs)})")
        for one in refs:
            print(f"      {one}")
    return 0


def _related(arguments) -> int:
    from meturgaman.sources import sefaria

    ref = sefaria.resolve(arguments.citation)
    payload = sefaria.related(ref)
    if not isinstance(payload, dict):
        print(f"no related data for {ref.normalized}", file=sys.stderr)
        return 1
    if arguments.json:
        return _emit_json({"ref": ref.normalized, "related": payload})
    print(ref.normalized)
    links = payload.get("links") or []
    by_category: dict[str, int] = {}
    for link in links:
        if isinstance(link, dict):
            category = str(link.get("category") or "(uncategorized)")
            by_category[category] = by_category.get(category, 0) + 1
    if by_category:
        print(f"links      {len(links)} in {len(by_category)} categories:")
        for category, count in sorted(by_category.items(), key=lambda kv: -kv[1]):
            print(f"    {count:4}  {category}")
    for name in ("sheets", "webpages", "manuscripts", "media", "notes"):
        entries = payload.get(name) or []
        if entries:
            print(f"{name:10} {len(entries)}")
    topics = payload.get("topics") or []
    if topics:
        print("topics:")
        for entry in topics:
            if isinstance(entry, dict):
                slug = entry.get("topic") or entry.get("slug") or ""
                title = entry.get("title")
                name = title.get("en") if isinstance(title, dict) else str(title or "")
                print(f"    {slug:28} {name}")
    print()
    print("Use `meturgaman links` for the refs, `meturgaman chain` for the order.")
    return 0


def _chain(arguments) -> int:
    from meturgaman.chain import chain

    normalized, groups = chain(arguments.citation)
    if arguments.json:
        return _emit_json({"ref": normalized, "chain": groups})
    if not groups:
        print(f"nothing links to {normalized}", file=sys.stderr)
        return 1
    print(f"{normalized}: what the tradition built on this passage")
    print()
    for group in groups:
        print(f"{group.category}  ({group.count})")
        for work, refs in group.works.items():
            if arguments.full:
                print(f"    {work}")
                for one in refs:
                    print(f"        {one}")
            else:
                preview = refs[0] if len(refs) == 1 else f"{refs[0]}  and {len(refs) - 1} more"
                print(f"    {work:32} {preview}")
        print()
    return 0


def _study(arguments) -> int:
    from meturgaman.emit import markdown
    from meturgaman.sources import sefaria

    citation = arguments.citation
    if arguments.sugya:
        boundary = sefaria.passage_boundary(citation)
        if boundary:
            print(f"expanded to the mapped passage: {boundary}", file=sys.stderr)
            citation = boundary
        else:
            print(
                f"no passage mapping for {citation}; using it as given",
                file=sys.stderr,
            )

    reading = sefaria.read(citation, version=("source", "translation"))

    vocalized_count = 0
    if arguments.vocalize:
        from meturgaman import hebrew
        from meturgaman.sources import dicta

        if not dicta.is_available():
            print(dicta.requirement_message(), file=sys.stderr)
            return 3
        for observation in reading.observations:
            language = (
                observation.edition.actual_language
                or observation.edition.language
                or ""
            ).lower()
            if not language.startswith("he"):
                continue
            segments = []
            for segment in observation.segments:
                if segment.text and not any(
                    hebrew.is_vowel(ch) for ch in segment.text
                ):
                    segments.append(sefaria.Segment(
                        anchor=segment.anchor,
                        text=dicta.vocalize(segment.text).text,
                    ))
                    vocalized_count += 1
                else:
                    segments.append(segment)
            observation.segments = segments

    rendered = {
        "block": markdown.block,
        "teaching": markdown.teaching,
        "interlinear": markdown.interlinear,
        "file": markdown.study_file,
    }[arguments.tier](reading, scheme=arguments.scheme)

    if vocalized_count:
        # The pointing in those segments is no longer the edition's, and a
        # study file that did not say so would be attributing a model's
        # reading to a printed source.
        from meturgaman.sources.dicta import MODEL

        note = (
            f"[vocalized-by-model] {vocalized_count} segment(s) carried no "
            f"vowels and were pointed by {MODEL}, run locally. The vowels "
            f"are a model's reading, not an edition's; check before quoting "
            f"as pointing."
        )
        rendered.text = rendered.text + f"\n\n{note}"
        rendered.flags.append(note)

    if arguments.paired:
        from meturgaman.pairings import companions_for, filter_companion_links

        title = reading.ref.book or reading.ref.normalized
        applicable = companions_for(title)
        if applicable:
            links = sefaria.links(reading.ref)
            lines = ["", "## Companions", ""]
            for pairing in applicable:
                found = filter_companion_links(links, pairing.companion)
                lines.append(f"**{pairing.companion}.** {pairing.why}")
                lines.append("")
                if found:
                    lines.extend(f"- {ref}" for ref in found)
                else:
                    # Absence is a finding: the graph is sparse, and saying
                    # so beats inventing a passage the graph never linked.
                    lines.append(
                        f"- The link graph records no {pairing.companion} "
                        f"passage for {reading.ref.normalized}."
                    )
                lines.append("")
            rendered.text = rendered.text + "\n" + "\n".join(lines).rstrip()
        else:
            print(
                f"no companion work is declared for {title} in rules/pairings.md",
                file=sys.stderr,
            )

    if arguments.output:
        target = Path(arguments.output)
        if target.is_dir():
            # A directory means "name it for me": the stable name derived
            # from the normalized reference, so one passage means one file.
            target = target / markdown.filename_for(reading)
        written = markdown.write(rendered, target)
        print(f"wrote {written}")
    else:
        print(rendered.text)
    for observation in reading.observations:
        for warning in observation.warnings:
            print(f"  {observation.edition.title}: {warning}", file=sys.stderr)
    if rendered.flags and not arguments.quiet:
        print(file=sys.stderr)
        _print_flags(dict.fromkeys(rendered.flags))
    return 0


def _daf(arguments) -> int:
    from meturgaman.sources import sefaria

    payload = sefaria.calendars(
        date=arguments.date or "", diaspora=not arguments.israel
    )
    wanted = arguments.cycle.lower()
    for item in payload.get("calendar_items") or []:
        title = item.get("title") or {}
        name = str(title.get("en") if isinstance(title, dict) else title)
        if name.lower() != wanted:
            continue
        ref = str(item.get("ref") or "")
        if not ref:
            print(f"{name} names no fetchable ref today", file=sys.stderr)
            return 1
        arguments.citation = ref
        print(f"{name}: {ref}", file=sys.stderr)
        return _text(arguments)
    names = [
        str((item.get("title") or {}).get("en", ""))
        for item in payload.get("calendar_items") or []
    ]
    print(
        f"no learning cycle named {arguments.cycle!r} today. "
        f"Cycles: {', '.join(name for name in names if name)}",
        file=sys.stderr,
    )
    return 1


# ---------------------------------------------------------------------------
# Romanization
# ---------------------------------------------------------------------------

def _romanize(arguments) -> int:
    from meturgaman.romanize.engine import romanize
    from meturgaman.romanize.register import RegisterConflict, preserve_guard
    from meturgaman.scheme import default_scheme

    text = arguments.text
    if text == "-":
        text = sys.stdin.read()

    scheme = arguments.scheme
    try:
        # The guard is told the scheme that will actually run, so a changed
        # default cannot leave it judging against a scheme nobody asked for.
        preserve_guard(text, scheme or default_scheme().name, force=arguments.force)
    except RegisterConflict as conflict:
        print(f"refused: {conflict}", file=sys.stderr)
        return 2

    result = romanize(text, scheme)
    if arguments.json:
        return _emit_json({
            "text": result.text,
            "scheme": result.scheme,
            "flags": [str(flag) for flag in result.flags],
        })
    print(result.text)
    if result.flags and not arguments.quiet:
        print(file=sys.stderr)
        _print_flags(result.flags)
    return 0


def _detect(arguments) -> int:
    from meturgaman.romanize import detect

    text = sys.stdin.read() if arguments.text == "-" else arguments.text
    if arguments.json:
        return _emit_json({"guesses": detect.detect(text)})
    print(detect.explain(text))
    return 0


def _reverse(arguments) -> int:
    from meturgaman.romanize import reverse

    candidates = reverse.reverse(arguments.text, arguments.scheme)[: arguments.limit]
    if arguments.json:
        return _emit_json({"candidates": candidates})
    for candidate in candidates:
        print(f"{candidate.letters:20} {candidate.scheme}")
        for note in candidate.ambiguities:
            print(f"    {note}")
    return 0


def _register(arguments) -> int:
    from meturgaman.romanize.register import detect_register

    text = sys.stdin.read() if arguments.text == "-" else arguments.text
    finding = detect_register(text)
    if arguments.json:
        return _emit_json(finding)
    print(finding.report())
    return 0


def _schemes(arguments) -> int:
    from meturgaman.scheme import all_schemes, scheme_named

    if arguments.name:
        print(scheme_named(arguments.name).text)
        return 0
    if arguments.json:
        return _emit_json({
            "schemes": [
                {
                    "name": name,
                    "citation": scheme.citation,
                    "script": scheme.script,
                    "source": scheme.source,
                    "is_default": scheme.is_default,
                }
                for name, scheme in sorted(all_schemes().items())
            ]
        })
    for name, scheme in sorted(all_schemes().items()):
        marker = " (default)" if scheme.is_default else ""
        print(f"{name}{marker}")
        print(f"    {scheme.citation}")
        print(f"    script {scheme.script}, from {scheme.source}")
    return 0


# ---------------------------------------------------------------------------
# Finding things
# ---------------------------------------------------------------------------

def _topics(arguments) -> int:
    from meturgaman.sources import sefaria

    found = sefaria.search_topics(arguments.query, limit=arguments.limit)
    if arguments.json:
        return _emit_json({"topics": found})
    if not found:
        print(f"no topic matches {arguments.query!r}", file=sys.stderr)
        return 1
    for topic in found:
        print(f"{topic.slug:28} {topic.name}")
    return 0


def _sources(arguments) -> int:
    from meturgaman.sources import sefaria

    refs = sefaria.topic_sources(arguments.slug, limit=arguments.limit)
    if arguments.json:
        return _emit_json({"slug": arguments.slug, "sources": refs})
    if not refs:
        print(
            f"no curated sources for {arguments.slug!r}. "
            f"Try `meturgaman topics {arguments.slug}` for the right slug.",
            file=sys.stderr,
        )
        return 1
    from meturgaman.net import NetworkError

    for ref in refs:
        print(ref)
        if arguments.text:
            try:
                reading = sefaria.read(ref)
                for observation in reading.observations[:2]:
                    print(f"    [{observation.edition.language}] {observation.joined[:160]}")
            except (LookupError, ValueError, NetworkError) as error:
                # A curated topic's sources are not all plain text: a sheet
                # ref answers with a shape `read` cannot parse and the fetch
                # raises NetworkError rather than a lookup failure. One bad
                # item should not cost the rest of the list.
                print(f"    ({error})")
            print()
    return 0


def _search(arguments) -> int:
    from meturgaman.sources import sefaria

    hits = sefaria.search(
        arguments.query, limit=arguments.limit, filters=arguments.filter or None
    )
    if arguments.json:
        return _emit_json({"query": arguments.query, "hits": hits})
    if not hits:
        print(f"nothing found for {arguments.query!r}", file=sys.stderr)
        return 1
    for hit in hits:
        print(f"{hit.ref}")
        print(f"    {hit.text[:200]}")
    return 0


def _word(arguments) -> int:
    from meturgaman.sources import sefaria

    entries = sefaria.lookup_word(arguments.word)
    if arguments.json:
        return _emit_json({"word": arguments.word, "entries": entries})
    if not entries:
        print(f"no dictionary entry for {arguments.word!r}", file=sys.stderr)
        return 1
    for entry in entries:
        print(f"{entry.headword}  ({entry.lexicon})")
        for sense in entry.senses:
            print(f"    {sense}")
    return 0


def _candidates(arguments) -> int:
    from meturgaman.sources import sefaria

    found = sefaria.name_candidates(arguments.name)
    if arguments.json:
        return _emit_json({"name": arguments.name, "candidates": found})
    if not found:
        print("no candidates", file=sys.stderr)
        return 1
    print("Sefaria's ranked order. The top hit is often wrong; choose one.")
    for index, entry in enumerate(found):
        print(f"  [{index}] {entry.get('key') or entry.get('title')}  ({entry.get('type', '')})")
    return 0


def _sugya(arguments) -> int:
    from meturgaman.sources import sefaria

    found = sefaria.passage_boundary(arguments.ref)
    if found is not None and found == sefaria.resolve(arguments.ref).normalized:
        # The service's own no-op: asked for a boundary and handed back
        # exactly the ref that was given. That is Sefaria saying nothing is
        # mapped here, not confirmation that the passage is one segment
        # wide, and printing it back as a boundary would read as the second
        # thing.
        found = None
    if arguments.json:
        return _emit_json({"ref": arguments.ref, "passage": found})
    print(found if found else f"no passage mapping for {arguments.ref}")
    return 0


def _anchors(arguments) -> int:
    from meturgaman.sources import sefaria

    works = sefaria.shape_summary(sefaria.shape(arguments.title))
    if arguments.json:
        return _emit_json({"works": works})
    if not works or all(not work.anchors for work in works):
        print(f"no populated anchors found for {arguments.title!r}", file=sys.stderr)
        return 1
    for work in works:
        print(f"{work.title}")
        print(
            f"    {work.chapters} chapters, {work.populated} populated "
            f"anchors, {work.total_segments} segments"
        )
        for anchor in work.anchors:
            plural = "s" if anchor.segments != 1 else ""
            print(f"    {anchor.reference:12} {anchor.segments} segment{plural}")
    return 0


def _verify(arguments) -> int:
    from meturgaman.verify import verify

    if arguments.path == "-":
        text = sys.stdin.read()
    else:
        try:
            text = Path(arguments.path).read_text(encoding="utf-8")
        except OSError as error:
            # A bare OSError repr ("[Errno 2] No such file or directory: ...")
            # is Python's voice, not this tool's; say the same thing in a
            # sentence a reader did not have to already know errno for.
            print(f"refused: could not read {arguments.path!r}: {error.strerror}",
                  file=sys.stderr)
            return 1
    report = verify(text)
    if arguments.json:
        _emit_json({
            "clean": report.clean,
            "citations": report.citations,
            "quotations": report.quotations,
        })
    else:
        print(report.render())
    return 0 if report.clean else 1


def _refs(arguments) -> int:
    from meturgaman.sources import sefaria

    text = sys.stdin.read() if arguments.text == "-" else arguments.text
    found = sefaria.find_refs(text)
    if arguments.json:
        return _emit_json({"found": found})
    for entry in found:
        for item in entry if isinstance(entry, list) else [entry]:
            if isinstance(item, dict) and item.get("refs"):
                print(f"{item.get('text', '')!r} -> {', '.join(item['refs'])}")
    return 0


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

def _day(arguments) -> int:
    from meturgaman.sources import hebcal

    day = hebcal.read_day(
        arguments.date,
        locale=arguments.register,
        israel=arguments.israel,
        after_sunset=arguments.after_sunset,
    )
    if arguments.json:
        return _emit_json(day)
    print(f"{day.gregorian.isoformat()}  ->  {day.hebrew_date}")
    if day.hebrew_date.hebrew:
        print(f"            {day.hebrew_date.hebrew}")
    print(f"register    {day.locale}")
    for event in day.events:
        print(f"event       {event.title}")
    if day.reading:
        print(f"parashah    {day.reading.name} {day.reading.hebrew_name}")
        if day.reading.haftarah:
            print(f"haftarah    {day.reading.haftarah}")
        for aliyah in day.reading.aliyot:
            print(f"  aliyah {aliyah}")
    for entry in day.study:
        print(f"study       {entry.cycle:14} {entry.ref}")
    print()
    print(day.attribution)
    return 0


def _leyning(arguments) -> int:
    from meturgaman.sources import hebcal

    reading = hebcal.leyning(
        arguments.date or date.today(),
        israel=arguments.israel,
        triennial=arguments.triennial,
    )
    if arguments.json:
        return _emit_json(reading)
    if reading is None:
        print("no reading for that date", file=sys.stderr)
        return 1
    print(f"{reading.name} {reading.hebrew_name}")
    for aliyah in reading.aliyot:
        print(f"  {aliyah}")
    if reading.haftarah:
        print(f"haftarah: {reading.haftarah}")
    if arguments.triennial and reading.triennial:
        print("triennial:")
        for aliyah in reading.triennial:
            print(f"  {aliyah}")
    print()
    print(hebcal.ATTRIBUTION)
    return 0


def _zmanim(arguments) -> int:
    from meturgaman.sources import hebcal

    payload = hebcal.zmanim(
        arguments.date or date.today(),
        geonameid=arguments.geonameid,
        zip_code=arguments.zip,
        latitude=arguments.latitude,
        longitude=arguments.longitude,
        tzid=arguments.tzid,
        elevation=arguments.elevation,
    )
    if arguments.json:
        return _emit_json(payload)
    times = payload.get("times", payload)
    for name, value in times.items():
        if isinstance(value, dict):
            value = json.dumps(value, ensure_ascii=False)
        print(f"{name:24} {value}")
    print()
    print(hebcal.ATTRIBUTION)
    return 0


def _calendars(arguments) -> int:
    from meturgaman.sources import sefaria

    payload = sefaria.calendars(
        date=arguments.date or "", diaspora=not arguments.israel
    )
    items = payload.get("calendar_items") or []
    if arguments.json:
        return _emit_json(payload)
    if not items:
        print("no learning calendar for that date", file=sys.stderr)
        return 1
    shown = str(payload.get("date") or arguments.date or "today")
    print(f"learning cycles for {shown}:")
    for item in items:
        title = item.get("title") or {}
        name = title.get("en") if isinstance(title, dict) else str(title)
        display = item.get("displayValue") or {}
        value = display.get("en") if isinstance(display, dict) else str(display)
        ref = item.get("ref") or ""
        line = f"  {name:26} {value}"
        if ref and ref != value:
            line += f"  ({ref})"
        print(line)
    print()
    print("Fetch any of these with `meturgaman text`.")
    return 0


def _yahrzeit(arguments) -> int:
    from meturgaman.sources import hebcal

    entries = hebcal.yahrzeit(
        arguments.death_date,
        years=arguments.years,
        after_sunset=arguments.after_sunset,
        name=arguments.name,
    )
    if arguments.json:
        return _emit_json({"death_date": arguments.death_date, "yahrzeits": entries})
    if not entries:
        print("no yahrzeit dates returned", file=sys.stderr)
        return 1
    for entry in entries:
        when = entry.get("date") or ""
        hebrew = entry.get("hdate") or ""
        print(f"{when}  {hebrew}")
    print()
    print(hebcal.ATTRIBUTION)
    return 0


def _clear_cache(arguments) -> int:
    from meturgaman.net import cache_directory, clear_cache

    where = cache_directory()
    removed = clear_cache()
    print(f"removed {removed} cached response(s) from {where}")
    return 0


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

def _audio(arguments) -> int:
    from meturgaman.sources import audio

    if arguments.synth:
        found, spoken = audio.read_aloud(
            arguments.citation, prefer="synthetic", output=arguments.output
        )
    else:
        found, spoken = audio.read_aloud(arguments.citation, output=arguments.output)

    if found:
        print(f"{len(found)} recording(s):")
        for recording in found:
            print(f"  {recording}")
            print(f"      {recording.attribution}")
            if arguments.download:
                # One path per recording, so several do not overwrite each other.
                target = Path(arguments.download)
                if target.is_dir() or len(found) > 1:
                    target = Path(arguments.download) / Path(recording.url).name
                print(f"      saved to {recording.download(target)}")
    elif not spoken:
        print(
            f"no recording exists for {arguments.citation}. "
            f"Add --synth to hear it read by the local synthesizer.",
            file=sys.stderr,
        )
        return 1

    if spoken:
        if not found:
            print("no human recording exists for this passage; synthesized instead.")
        print(f"spoken with {spoken.voice}" + (f", saved to {spoken.path}" if spoken.path else ""))
        _print_flags(spoken.warnings)
    return 0


def _vocalize(arguments) -> int:
    from meturgaman.sources import dicta

    if not dicta.is_available():
        print(dicta.requirement_message(), file=sys.stderr)
        return 3
    text = sys.stdin.read() if arguments.text == "-" else arguments.text
    result = dicta.vocalize(text)
    print(result.text)
    print(result.provenance, file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    from meturgaman.sources.sefaria import RETURN_FORMATS

    parser = argparse.ArgumentParser(
        prog="meturgaman",
        description=(
            "Fetch Hebrew, Aramaic and Yiddish primary sources, romanize them "
            "under a published standard, and hear them read aloud."
        ),
    )
    parser.add_argument("--version", action="version", version=f"meturgaman {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    scheme_help = "romanization scheme; see `meturgaman schemes`"

    # Shared flags, attached per-subcommand so they can be typed after the
    # subcommand name, which is where a hand reaches for them.
    machine = argparse.ArgumentParser(add_help=False)
    machine.add_argument("--json", action="store_true",
                         help="print one JSON document instead of prose")
    machine.add_argument("--no-cache", action="store_true",
                         help="bypass the response cache for this run")
    fresh = argparse.ArgumentParser(add_help=False)
    fresh.add_argument("--no-cache", action="store_true",
                       help="bypass the response cache for this run")

    text = commands.add_parser("text", parents=[machine],
                               help="fetch a passage in one or many editions")
    text.add_argument("citation")
    text.add_argument("--version", action="append", dest="version",
                      help="source, translation, primary, all, a language name, "
                           "or 'language|Version Title'. Repeatable.")
    text.add_argument("--format", default="text_only", choices=RETURN_FORMATS)
    text.add_argument("--full", action="store_true", help="every segment, not a preview")
    text.add_argument("--fill-gaps", action="store_true",
                      help="fill missing segments from other versions")
    text.add_argument("--max-editions", type=int, default=12)
    text.set_defaults(handler=_text)

    editions = commands.add_parser("editions", parents=[machine],
                                   help="list every edition of a work")
    editions.add_argument("citation")
    editions.set_defaults(handler=_editions)

    compare = commands.add_parser("compare", parents=[machine],
                                  help="where the editions actually differ")
    compare.add_argument("citation")
    compare.add_argument("--language", default="he")
    compare.add_argument("--max-editions", type=int, default=8)
    compare.set_defaults(handler=_compare)

    links = commands.add_parser(
        "links", parents=[machine],
        help="what connects to a passage: commentary, midrash, codes",
    )
    links.add_argument("citation")
    links.add_argument("--category", action="append",
                       help="filter to a Sefaria category such as Commentary "
                            "or Halakhah; repeatable")
    links.add_argument("--refs-only", action="store_true",
                       help="print bare references, one per line, for piping")
    links.set_defaults(handler=_links)

    related = commands.add_parser(
        "related", parents=[machine],
        help="everything Sefaria attaches to a passage, summarized",
    )
    related.add_argument("citation")
    related.set_defaults(handler=_related)

    chain = commands.add_parser(
        "chain", parents=[machine],
        help="what the tradition built on a passage, in transmission order",
    )
    chain.add_argument("citation")
    chain.add_argument("--full", action="store_true",
                       help="every ref in every work, not counts")
    chain.set_defaults(handler=_chain)

    study = commands.add_parser("study", parents=[fresh],
                                help="render a passage as markdown")
    study.add_argument("citation")
    study.add_argument("--tier", default="teaching", choices=("block", "teaching", "interlinear", "file"))
    study.add_argument("--scheme", default=None, help=scheme_help)
    study.add_argument("--quiet", action="store_true")
    study.add_argument("--sugya", action="store_true",
                       help="expand a Talmud reference to its mapped passage first")
    study.add_argument("--paired", action="store_true",
                       help="append companion passages from rules/pairings.md "
                            "and the link graph")
    study.add_argument("--vocalize", action="store_true",
                       help="point unvocalized Hebrew with Dicta's local model, "
                            "marked as a model's reading (needs the dicta extra)")
    study.add_argument("--output", default=None,
                       help="write to this file, or into this directory "
                            "under a name derived from the reference")
    study.set_defaults(handler=_study)

    daf = commands.add_parser(
        "daf", parents=[machine],
        help="fetch today's daf yomi, or any other learning cycle's reading",
    )
    daf.add_argument("--cycle", default="Daf Yomi",
                     help="a cycle name from `meturgaman calendars`")
    daf.add_argument("--date", default=None, help="YYYY-MM-DD, default today")
    daf.add_argument("--israel", action="store_true")
    daf.add_argument("--version", action="append", dest="version",
                     help="as for `meturgaman text`")
    daf.add_argument("--format", default="text_only", choices=RETURN_FORMATS)
    daf.add_argument("--full", action="store_true", help="every segment, not a preview")
    daf.add_argument("--fill-gaps", action="store_true")
    daf.add_argument("--max-editions", type=int, default=12)
    daf.set_defaults(handler=_daf)

    romanize = commands.add_parser("romanize", parents=[machine],
                                   help="Hebrew to Latin under a scheme")
    romanize.add_argument("text", help="Hebrew text, or - for standard input")
    romanize.add_argument("--scheme", default=None, help=scheme_help)
    romanize.add_argument("--force", action="store_true",
                          help="rewrite Ashkenazi text as Sephardi anyway")
    romanize.add_argument("--quiet", action="store_true", help="suppress flags")
    romanize.set_defaults(handler=_romanize)

    detect = commands.add_parser("detect", parents=[machine],
                                 help="which scheme a romanization uses")
    detect.add_argument("text", help="Latin text, or - for standard input")
    detect.set_defaults(handler=_detect)

    reverse = commands.add_parser("reverse", parents=[machine],
                                  help="Latin back to Hebrew letters")
    reverse.add_argument("text")
    reverse.add_argument("--scheme", default=None, help=scheme_help)
    reverse.add_argument("--limit", type=_positive_limit, default=4)
    reverse.set_defaults(handler=_reverse)

    register = commands.add_parser("register", parents=[machine],
                                   help="Ashkenazi or Sephardi spelling")
    register.add_argument("text", help="text, or - for standard input")
    register.set_defaults(handler=_register)

    schemes = commands.add_parser("schemes", parents=[machine],
                                  help="list the schemes, or print one in full")
    schemes.add_argument("--name", default=None)
    schemes.set_defaults(handler=_schemes)

    topics = commands.add_parser("topics", parents=[machine],
                                 help="find a subject in Sefaria's ontology")
    topics.add_argument("query")
    topics.add_argument("--limit", type=_positive_limit, default=10)
    topics.set_defaults(handler=_topics)

    sources = commands.add_parser("sources", parents=[machine],
                                  help="the curated sources on a topic")
    sources.add_argument("slug")
    sources.add_argument("--limit", type=_positive_limit, default=10)
    sources.add_argument("--text", action="store_true", help="fetch each passage too")
    sources.set_defaults(handler=_sources)

    search = commands.add_parser("search", parents=[machine],
                                 help="full-text search of the library")
    search.add_argument("query")
    search.add_argument("--limit", type=_positive_limit, default=10)
    search.add_argument("--filter", action="append", help="category path; repeatable")
    search.set_defaults(handler=_search)

    word = commands.add_parser("word", parents=[machine],
                               help="dictionary entries for a word")
    word.add_argument("word")
    word.set_defaults(handler=_word)

    candidates = commands.add_parser("candidates", parents=[machine],
                                     help="ranked guesses for a name")
    candidates.add_argument("name")
    candidates.set_defaults(handler=_candidates)

    sugya = commands.add_parser("sugya", parents=[machine],
                                help="the passage containing a Talmud reference")
    sugya.add_argument("ref")
    sugya.set_defaults(handler=_sugya)

    refs = commands.add_parser("refs", parents=[machine],
                               help="find citations inside prose")
    refs.add_argument("text", help="prose, or - for standard input")
    refs.set_defaults(handler=_refs)

    verify = commands.add_parser(
        "verify", parents=[machine],
        help="check a draft's citations and Hebrew quotations against editions",
    )
    verify.add_argument("path", help="a file, or - for standard input")
    verify.set_defaults(handler=_verify)

    anchors = commands.add_parser(
        "anchors", parents=[machine],
        help="every populated anchor in a work, counted from data",
    )
    anchors.add_argument("title", help="a work's title, as Sefaria names it")
    anchors.set_defaults(handler=_anchors)

    day = commands.add_parser("day", parents=[machine],
                              help="the Jewish calendar for a date")
    day.add_argument("--date", default=None, help="YYYY-MM-DD, default today")
    day.add_argument("--register", default="s",
                     help="Hebcal locale: s, a, ashkenazi_litvish, and others")
    day.add_argument("--israel", action="store_true")
    day.add_argument("--after-sunset", action="store_true")
    day.set_defaults(handler=_day)

    leyning = commands.add_parser("leyning", parents=[machine],
                                  help="the Torah reading for a date")
    leyning.add_argument("--date", default=None)
    leyning.add_argument("--israel", action="store_true")
    leyning.add_argument("--triennial", action="store_true")
    leyning.set_defaults(handler=_leyning)

    zmanim = commands.add_parser("zmanim", parents=[machine],
                                 help="halachic times for a place")
    zmanim.add_argument("--date", default=None)
    zmanim.add_argument("--geonameid", type=int, default=None)
    zmanim.add_argument("--zip", default=None)
    zmanim.add_argument("--latitude", type=float, default=None)
    zmanim.add_argument("--longitude", type=float, default=None)
    zmanim.add_argument("--tzid", default=None)
    zmanim.add_argument("--elevation", type=int, default=None,
                        help="metres above sea level; changes sunrise and sunset")
    zmanim.set_defaults(handler=_zmanim)

    calendars = commands.add_parser(
        "calendars", parents=[machine],
        help="today's learning cycles: daf yomi, parashah, and the rest",
    )
    calendars.add_argument("--date", default=None, help="YYYY-MM-DD, default today")
    calendars.add_argument("--israel", action="store_true")
    calendars.set_defaults(handler=_calendars)

    yahrzeit = commands.add_parser(
        "yahrzeit", parents=[machine],
        help="yahrzeit dates for the coming years",
    )
    yahrzeit.add_argument("death_date", help="Gregorian date of death, YYYY-MM-DD")
    yahrzeit.add_argument("--years", type=_positive_limit, default=20)
    yahrzeit.add_argument("--after-sunset", action="store_true")
    yahrzeit.add_argument("--name", default="")
    yahrzeit.set_defaults(handler=_yahrzeit)

    clear_cache = commands.add_parser(
        "clear-cache", help="delete every cached network response"
    )
    clear_cache.set_defaults(handler=_clear_cache)

    audio = commands.add_parser("audio", parents=[fresh],
                                help="hear a passage read aloud")
    audio.add_argument("citation")
    audio.add_argument("--synth", action="store_true",
                       help="synthesize even when a recording exists")
    audio.add_argument("--output", default=None, help="write audio to a file")
    audio.add_argument("--download", default=None, help="save the recording here")
    audio.set_defaults(handler=_audio)

    vocalize = commands.add_parser("vocalize", parents=[fresh],
                                   help="add vowel points (needs the dicta extra)")
    vocalize.add_argument("text", help="Hebrew text, or - for standard input")
    vocalize.set_defaults(handler=_vocalize)

    return parser


def main(argv: list[str] | None = None) -> int:
    from meturgaman import net
    from meturgaman.net import NetworkError
    from meturgaman.scheme import SchemeError

    parser = build_parser()
    arguments = parser.parse_args(argv)
    if getattr(arguments, "no_cache", False):
        net.CACHE_DISABLED = True
    try:
        return arguments.handler(arguments)
    except KeyboardInterrupt:  # pragma: no cover
        return 130
    except (SchemeError, NetworkError) as error:
        # Both subclass Exception directly, so neither was caught before and a
        # mistyped scheme name or an unreachable service produced a traceback.
        print(f"refused: {error}", file=sys.stderr)
        return 1
    except (ValueError, RuntimeError, OSError, OverflowError) as error:
        print(f"refused: {error}", file=sys.stderr)
        return 1
    except LookupError as error:
        # LookupError is the base of KeyError and IndexError, so an internal
        # fault would otherwise print as `refused: 'somekey'` and read like the
        # user's mistake.
        if type(error) in (KeyError, IndexError):
            raise
        print(f"refused: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
