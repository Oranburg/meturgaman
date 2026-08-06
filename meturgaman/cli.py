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
import sys
from datetime import date

from meturgaman import __version__

__all__ = ["main"]


def _print_flags(flags, prefix: str = "  ") -> None:
    for flag in flags:
        print(f"{prefix}{flag}", file=sys.stderr)


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
            print(f"      {observation.segments[0].text[:200]}")
        print()
    print(reading.attribution)
    return 0


def _editions(arguments) -> int:
    from meturgaman.sources import sefaria

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
    print(compare(reading, language=arguments.language).report())
    return 0


def _study(arguments) -> int:
    from meturgaman.emit import markdown
    from meturgaman.sources import sefaria

    reading = sefaria.read(arguments.citation, version=("source", "translation"))
    rendered = {
        "block": markdown.block,
        "teaching": markdown.teaching,
        "file": markdown.study_file,
    }[arguments.tier](reading, scheme=arguments.scheme)
    print(rendered.text)
    if rendered.flags and not arguments.quiet:
        print(file=sys.stderr)
        _print_flags(dict.fromkeys(rendered.flags))
    return 0


# ---------------------------------------------------------------------------
# Romanization
# ---------------------------------------------------------------------------

def _romanize(arguments) -> int:
    from meturgaman.romanize.engine import romanize
    from meturgaman.romanize.register import RegisterConflict, preserve_guard

    text = arguments.text
    if text == "-":
        text = sys.stdin.read()

    scheme = arguments.scheme
    try:
        preserve_guard(text, scheme or "sbl-general", force=arguments.force)
    except RegisterConflict as conflict:
        print(f"refused: {conflict}", file=sys.stderr)
        return 2

    result = romanize(text, scheme)
    print(result.text)
    if result.flags and not arguments.quiet:
        print(file=sys.stderr)
        _print_flags(result.flags)
    return 0


def _detect(arguments) -> int:
    from meturgaman.romanize import detect

    text = sys.stdin.read() if arguments.text == "-" else arguments.text
    print(detect.explain(text))
    return 0


def _reverse(arguments) -> int:
    from meturgaman.romanize import reverse

    for candidate in reverse.reverse(arguments.text, arguments.scheme)[: arguments.limit]:
        print(f"{candidate.letters:20} {candidate.scheme}")
        for note in candidate.ambiguities:
            print(f"    {note}")
    return 0


def _register(arguments) -> int:
    from meturgaman.romanize.register import detect_register

    text = sys.stdin.read() if arguments.text == "-" else arguments.text
    print(detect_register(text).report())
    return 0


def _schemes(arguments) -> int:
    from meturgaman.scheme import all_schemes, scheme_named

    if arguments.name:
        print(scheme_named(arguments.name).text)
        return 0
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
    if not found:
        print(f"no topic matches {arguments.query!r}", file=sys.stderr)
        return 1
    for topic in found:
        print(f"{topic.slug:28} {topic.name}")
    return 0


def _sources(arguments) -> int:
    from meturgaman.sources import sefaria

    refs = sefaria.topic_sources(arguments.slug, limit=arguments.limit)
    if not refs:
        print(
            f"no curated sources for {arguments.slug!r}. "
            f"Try `meturgaman topics {arguments.slug}` for the right slug.",
            file=sys.stderr,
        )
        return 1
    for ref in refs:
        print(ref)
        if arguments.text:
            try:
                reading = sefaria.read(ref)
                for observation in reading.observations[:2]:
                    print(f"    [{observation.edition.language}] {observation.joined[:160]}")
            except (LookupError, ValueError) as error:
                print(f"    ({error})")
            print()
    return 0


def _search(arguments) -> int:
    from meturgaman.sources import sefaria

    hits = sefaria.search(
        arguments.query, limit=arguments.limit, filters=arguments.filter or None
    )
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
    print(found if found else f"no passage mapping for {arguments.ref}")
    return 0


def _refs(arguments) -> int:
    from meturgaman.sources import sefaria

    text = sys.stdin.read() if arguments.text == "-" else arguments.text
    for entry in sefaria.find_refs(text):
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
    import json

    from meturgaman.sources import hebcal

    payload = hebcal.zmanim(
        arguments.date or date.today(),
        geonameid=arguments.geonameid,
        zip_code=arguments.zip,
        latitude=arguments.latitude,
        longitude=arguments.longitude,
        tzid=arguments.tzid,
    )
    times = payload.get("times", payload)
    for name, value in times.items():
        if isinstance(value, dict):
            value = json.dumps(value, ensure_ascii=False)
        print(f"{name:24} {value}")
    print()
    print(hebcal.ATTRIBUTION)
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
                target = audio.Path(arguments.download)
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

    text = commands.add_parser("text", help="fetch a passage in one or many editions")
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

    editions = commands.add_parser("editions", help="list every edition of a work")
    editions.add_argument("citation")
    editions.set_defaults(handler=_editions)

    compare = commands.add_parser("compare", help="where the editions actually differ")
    compare.add_argument("citation")
    compare.add_argument("--language", default="he")
    compare.add_argument("--max-editions", type=int, default=8)
    compare.set_defaults(handler=_compare)

    study = commands.add_parser("study", help="render a passage as markdown")
    study.add_argument("citation")
    study.add_argument("--tier", default="teaching", choices=("block", "teaching", "file"))
    study.add_argument("--scheme", default=None, help=scheme_help)
    study.add_argument("--quiet", action="store_true")
    study.set_defaults(handler=_study)

    romanize = commands.add_parser("romanize", help="Hebrew to Latin under a scheme")
    romanize.add_argument("text", help="Hebrew text, or - for standard input")
    romanize.add_argument("--scheme", default=None, help=scheme_help)
    romanize.add_argument("--force", action="store_true",
                          help="rewrite Ashkenazi text as Sephardi anyway")
    romanize.add_argument("--quiet", action="store_true", help="suppress flags")
    romanize.set_defaults(handler=_romanize)

    detect = commands.add_parser("detect", help="which scheme a romanization uses")
    detect.add_argument("text", help="Latin text, or - for standard input")
    detect.set_defaults(handler=_detect)

    reverse = commands.add_parser("reverse", help="Latin back to Hebrew letters")
    reverse.add_argument("text")
    reverse.add_argument("--scheme", default=None, help=scheme_help)
    reverse.add_argument("--limit", type=int, default=4)
    reverse.set_defaults(handler=_reverse)

    register = commands.add_parser("register", help="Ashkenazi or Sephardi spelling")
    register.add_argument("text", help="text, or - for standard input")
    register.set_defaults(handler=_register)

    schemes = commands.add_parser("schemes", help="list the schemes, or print one in full")
    schemes.add_argument("--name", default=None)
    schemes.set_defaults(handler=_schemes)

    topics = commands.add_parser("topics", help="find a subject in Sefaria's ontology")
    topics.add_argument("query")
    topics.add_argument("--limit", type=int, default=10)
    topics.set_defaults(handler=_topics)

    sources = commands.add_parser("sources", help="the curated sources on a topic")
    sources.add_argument("slug")
    sources.add_argument("--limit", type=int, default=10)
    sources.add_argument("--text", action="store_true", help="fetch each passage too")
    sources.set_defaults(handler=_sources)

    search = commands.add_parser("search", help="full-text search of the library")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--filter", action="append", help="category path; repeatable")
    search.set_defaults(handler=_search)

    word = commands.add_parser("word", help="dictionary entries for a word")
    word.add_argument("word")
    word.set_defaults(handler=_word)

    candidates = commands.add_parser("candidates", help="ranked guesses for a name")
    candidates.add_argument("name")
    candidates.set_defaults(handler=_candidates)

    sugya = commands.add_parser("sugya", help="the passage containing a Talmud reference")
    sugya.add_argument("ref")
    sugya.set_defaults(handler=_sugya)

    refs = commands.add_parser("refs", help="find citations inside prose")
    refs.add_argument("text", help="prose, or - for standard input")
    refs.set_defaults(handler=_refs)

    day = commands.add_parser("day", help="the Jewish calendar for a date")
    day.add_argument("--date", default=None, help="YYYY-MM-DD, default today")
    day.add_argument("--register", default="s",
                     help="Hebcal locale: s, a, ashkenazi_litvish, and others")
    day.add_argument("--israel", action="store_true")
    day.add_argument("--after-sunset", action="store_true")
    day.set_defaults(handler=_day)

    leyning = commands.add_parser("leyning", help="the Torah reading for a date")
    leyning.add_argument("--date", default=None)
    leyning.add_argument("--israel", action="store_true")
    leyning.add_argument("--triennial", action="store_true")
    leyning.set_defaults(handler=_leyning)

    zmanim = commands.add_parser("zmanim", help="halachic times for a place")
    zmanim.add_argument("--date", default=None)
    zmanim.add_argument("--geonameid", type=int, default=None)
    zmanim.add_argument("--zip", default=None)
    zmanim.add_argument("--latitude", type=float, default=None)
    zmanim.add_argument("--longitude", type=float, default=None)
    zmanim.add_argument("--tzid", default=None)
    zmanim.set_defaults(handler=_zmanim)

    audio = commands.add_parser("audio", help="hear a passage read aloud")
    audio.add_argument("citation")
    audio.add_argument("--synth", action="store_true",
                       help="synthesize even when a recording exists")
    audio.add_argument("--output", default=None, help="write audio to a file")
    audio.add_argument("--download", default=None, help="save the recording here")
    audio.set_defaults(handler=_audio)

    vocalize = commands.add_parser("vocalize", help="add vowel points (needs the dicta extra)")
    vocalize.add_argument("text", help="Hebrew text, or - for standard input")
    vocalize.set_defaults(handler=_vocalize)

    return parser


def main(argv: list[str] | None = None) -> int:
    from meturgaman.net import NetworkError
    from meturgaman.scheme import SchemeError

    parser = build_parser()
    arguments = parser.parse_args(argv)
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
