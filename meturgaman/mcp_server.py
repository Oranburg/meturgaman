"""An MCP server over the same library the command line uses.

Why this is optional
--------------------
The core of this project is standard library only, and stays that way. The
Model Context Protocol needs its own SDK, so the server is an extra:

    pip install 'meturgaman[mcp]'
    meturgaman-mcp

When the SDK is absent, running the entry point says so and exits, the same
contract the dicta extra keeps. Nothing else in the package imports this
module.

What it serves
--------------
The same operations the CLI exposes, over stdio, for MCP clients such as
Claude Desktop and Claude Code. Every tool returns structured data with the
flags and warnings inside it, because a client that never reads stderr must
still see every uncertainty. Nothing here answers from memory: every tool
calls the same fetching, validating library the CLI calls.
"""

from __future__ import annotations

import dataclasses
import sys
from typing import Any

__all__ = ["build_server", "main"]

_REQUIREMENT = (
    "The MCP server needs the protocol SDK, which is an optional extra:\n"
    "    pip install 'meturgaman[mcp]'\n"
    "The core tool works without it; only `meturgaman-mcp` needs it."
)


def _plain(value: Any) -> Any:
    """Dataclasses to dictionaries, recursively, for the wire."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {key: _plain(item) for key, item in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def build_server():
    """Construct the server. Raises ImportError when the SDK is missing."""
    from mcp.server import MCPServer

    from meturgaman import __version__

    server = MCPServer(
        name="meturgaman",
        version=__version__,
        instructions=(
            "Jewish primary sources, fetched with their editions and "
            "licences, never from memory. Romanization flags mark decisions "
            "the spelling alone cannot settle; treat them as part of the "
            "answer. A citation that does not resolve is a finding, not an "
            "obstacle: offer the candidates instead of guessing."
        ),
    )

    @server.tool(description=(
        "Fetch a passage in its editions, with segment anchors, licences, "
        "and provenance. The only way to quote a text."
    ))
    def text(citation: str, version: str = "", full: bool = True) -> dict:
        from meturgaman.sources import sefaria

        reading = sefaria.read(
            citation, version=version or ("source", "translation")
        )
        return _plain({
            "ref": reading.ref,
            "independent_witnesses": reading.independent_witnesses,
            "providers": list(reading.providers),
            "editions": [
                {
                    "edition": observation.edition,
                    "warnings": observation.warnings,
                    "segments": observation.segments if full
                    else observation.segments[:1],
                }
                for observation in reading.observations
            ],
            "attribution": reading.attribution,
        })

    @server.tool(description=(
        "Everything the tradition built on a passage, in transmission order: "
        "Tanakh through Mishnah, Talmud, commentary, codes, responsa."
    ))
    def chain(citation: str) -> dict:
        from meturgaman.chain import chain as build_chain

        normalized, groups = build_chain(citation)
        return _plain({"ref": normalized, "chain": groups})

    @server.tool(description=(
        "Raw link records for a passage, optionally filtered by Sefaria "
        "category such as Commentary or Halakhah."
    ))
    def links(citation: str, category: str = "") -> dict:
        from meturgaman.sources import sefaria

        ref = sefaria.resolve(citation)
        found = sefaria.links(ref, categories=[category] if category else None)
        return _plain({"ref": ref.normalized, "links": found})

    @server.tool(description=(
        "Romanize Hebrew under a published standard. Flags travel in the "
        "result and mark decisions the orthography cannot settle."
    ))
    def romanize(text: str, scheme: str = "") -> dict:
        from meturgaman.romanize.engine import romanize as run

        result = run(text, scheme or None)
        return {
            "text": result.text,
            "scheme": result.scheme,
            "flags": [str(flag) for flag in result.flags],
        }

    @server.tool(description=(
        "Which romanization standard a Latin-script text already uses, with "
        "the evidence for and against each candidate."
    ))
    def detect(text: str) -> dict:
        from meturgaman.romanize import detect as detector

        return _plain({"guesses": detector.detect(text)})

    @server.tool(description=(
        "Check a draft: every citation validated against Sefaria, every "
        "Hebrew quotation of three or more words checked against the "
        "passages cited in its paragraph, with the first diverging word "
        "named when a quotation fails."
    ))
    def verify_draft(text: str) -> dict:
        from meturgaman.verify import verify as run

        report = run(text)
        return _plain({
            "clean": report.clean,
            "citations": report.citations,
            "quotations": report.quotations,
        })

    @server.tool(description=(
        "Every populated anchor of a work with its segment count, from the "
        "service's shape record. Run before any sentence that counts."
    ))
    def anchors(title: str) -> dict:
        from meturgaman.sources import sefaria

        return _plain({
            "works": sefaria.shape_summary(sefaria.shape(title))
        })

    @server.tool(description=(
        "Find a subject in Sefaria's curated topic ontology; better than "
        "search for anything anyone has thought about before."
    ))
    def topics(query: str, limit: int = 10) -> dict:
        from meturgaman.sources import sefaria

        return _plain({"topics": sefaria.search_topics(query, limit=limit)})

    @server.tool(description="The curated source references for a topic slug.")
    def topic_sources(slug: str, limit: int = 10) -> dict:
        from meturgaman.sources import sefaria

        return _plain({
            "slug": slug,
            "sources": sefaria.topic_sources(slug, limit=limit),
        })

    @server.tool(description="Full-text search of the library, for when no topic fits.")
    def search(query: str, limit: int = 10) -> dict:
        from meturgaman.sources import sefaria

        return _plain({"hits": sefaria.search(query, limit=limit)})

    @server.tool(description=(
        "Dictionary entries for a Hebrew or Aramaic word, with Jastrow's "
        "citations back into the corpus."
    ))
    def word(term: str) -> dict:
        from meturgaman.sources import sefaria

        return _plain({"entries": sefaria.lookup_word(term)})

    @server.tool(description=(
        "The mapped passage boundary containing a Talmud reference. A page "
        "is a physical unit; the argument regularly crosses it."
    ))
    def sugya(citation: str) -> dict:
        from meturgaman.sources import sefaria

        return {"ref": citation, "passage": sefaria.passage_boundary(citation)}

    @server.tool(description=(
        "The daily learning calendar: parashah, daf yomi, and the other "
        "cycles, each with a fetchable reference."
    ))
    def calendars(date: str = "", israel: bool = False) -> dict:
        from meturgaman.sources import sefaria

        return _plain(sefaria.calendars(date=date, diaspora=not israel))

    return server


def main() -> int:
    try:
        server = build_server()
    except ImportError:
        print(_REQUIREMENT, file=sys.stderr)
        return 3
    server.run("stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
