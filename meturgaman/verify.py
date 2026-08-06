"""Check a draft's citations and Hebrew quotations against real editions.

A manuscript that quotes Hebrew carries two kinds of checkable claim: that
its citations name real passages, and that its quotations match what an
edition actually prints. Both fail silently in ordinary writing, and the
second failure is invisible to any reader who does not already know the
text, which is the same failure this whole project is built against.

This module takes a draft, finds the citations with Sefaria's own reference
finder, validates each one, and then checks every Hebrew quotation against
the fetched text of the passages cited near it. Comparison happens on the
consonantal skeleton, the same ground `compare` uses, because a draft and an
edition may legitimately differ in pointing and cantillation.

What a verdict means:

  **resolved**    the citation names a passage Sefaria recognizes
  **unresolved**  it does not; the reference is wrong or not on Sefaria
  **found**       the quotation's skeleton appears in a cited passage
  **not found**   it appears in none of the passages cited in its paragraph,
                  which means a wrong quotation, a wrong citation, or a
                  paragraph quoting a text it never cites

"Not found" is a flag to check, never proof of fabrication: the quoted
edition may differ substantively from the ones fetched, or the citation may
sit too far from the quotation for the pairing to see.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from meturgaman import hebrew

__all__ = [
    "CitationCheck", "QuotationCheck", "Report",
    "hebrew_runs", "skeleton_contains", "verify",
]

#: A quotation shorter than this many Hebrew words is not checked. Two-word
#: runs are usually vocabulary being glossed, and matching them against a
#: whole chapter proves nothing either way.
MINIMUM_WORDS = 3


@dataclass(frozen=True)
class CitationCheck:
    """One citation the draft makes, and whether it names a real passage."""

    text: str
    refs: tuple[str, ...]
    resolved: bool
    detail: str = ""


@dataclass(frozen=True)
class QuotationCheck:
    """One Hebrew quotation, and where it was or was not found."""

    quotation: str
    found_in: str = ""
    checked_against: tuple[str, ...] = ()

    @property
    def found(self) -> bool:
        return bool(self.found_in)


@dataclass
class Report:
    citations: list[CitationCheck] = field(default_factory=list)
    quotations: list[QuotationCheck] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return (
            all(entry.resolved for entry in self.citations)
            and all(entry.found for entry in self.quotations)
        )

    def render(self) -> str:
        lines: list[str] = []
        if not self.citations and not self.quotations:
            return "nothing to check: no citations found and no Hebrew runs long enough"
        for entry in self.citations:
            if entry.resolved:
                lines.append(f"resolved    {entry.text!r} -> {', '.join(entry.refs)}")
            else:
                lines.append(f"UNRESOLVED  {entry.text!r}  {entry.detail}".rstrip())
        for entry in self.quotations:
            head = " ".join(entry.quotation.split()[:6])
            if entry.found:
                lines.append(f"found       {head}...  in {entry.found_in}")
            elif entry.checked_against:
                lines.append(
                    f"NOT FOUND   {head}...  checked against "
                    f"{', '.join(entry.checked_against)}"
                )
            else:
                lines.append(
                    f"UNCHECKED   {head}...  no citation in its paragraph to check against"
                )
        return "\n".join(lines)


def hebrew_runs(paragraph: str, *, minimum_words: int = MINIMUM_WORDS) -> list[str]:
    """Contiguous stretches of Hebrew inside a paragraph, long enough to check.

    A run is consecutive whitespace-separated words that each contain Hebrew.
    Punctuation and markdown around the words is tolerated; the skeleton
    comparison strips it anyway.
    """
    runs: list[list[str]] = []
    current: list[str] = []
    for word in paragraph.split():
        if hebrew.has_hebrew(word):
            current.append(word)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return [" ".join(run) for run in runs if len(run) >= minimum_words]


def skeleton_contains(source: str, quotation: str) -> bool:
    """Whether the quotation's consonantal skeleton appears in the source's.

    Word-by-word contiguous match on skeletons, so pointing, cantillation and
    punctuation differences do not defeat a genuine quotation, while a wrong
    or reworded quotation still fails.
    """
    needle = [
        hebrew.consonantal_skeleton(word)
        for word in quotation.split()
        if hebrew.has_hebrew(word)
    ]
    haystack = [
        hebrew.consonantal_skeleton(word)
        for word in source.split()
        if hebrew.has_hebrew(word)
    ]
    needle = [word for word in needle if word]
    haystack = [word for word in haystack if word]
    if not needle or len(needle) > len(haystack):
        return False
    for start in range(len(haystack) - len(needle) + 1):
        if haystack[start:start + len(needle)] == needle:
            return True
    return False


def _paragraphs(text: str) -> list[str]:
    return [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]


def _found_refs(text: str) -> list[CitationCheck]:
    """Citations inside the draft, via Sefaria's reference finder.

    One call for the whole draft: the endpoint is asynchronous and polled,
    so per-paragraph calls made a long chapter unbearably slow.
    """
    from meturgaman.sources import sefaria

    checks: list[CitationCheck] = []
    for entry in sefaria.find_refs(text):
        for item in entry if isinstance(entry, list) else [entry]:
            if not isinstance(item, dict):
                continue
            refs = tuple(str(ref) for ref in (item.get("refs") or []))
            text = str(item.get("text") or "")
            if not text:
                continue
            if refs:
                checks.append(CitationCheck(text=text, refs=refs, resolved=True))
            else:
                checks.append(
                    CitationCheck(
                        text=text, refs=(), resolved=False,
                        detail="Sefaria's reference finder matched the shape "
                               "but resolved it to nothing",
                    )
                )
    return checks


def _passage_text(ref: str) -> str:
    """The Hebrew of one cited passage, joined across its source editions."""
    from meturgaman.sources import sefaria

    try:
        reading = sefaria.read(ref, version="source")
    except (LookupError, ValueError):
        return ""
    return " ".join(
        observation.joined for observation in reading.observations
    )


def verify(text: str) -> Report:
    """Check every citation and every long Hebrew run in a draft.

    Quotations are checked against the passages cited in their own paragraph,
    because that is the pairing a reader assumes; a quotation with no
    citation nearby is reported unchecked rather than guessed at.
    """
    report = Report()
    fetched: dict[str, str] = {}
    report.citations = _found_refs(text)

    for paragraph in _paragraphs(text):
        # A citation belongs to the paragraphs that carry its matched text.
        # The finder reports the exact string it matched, so containment is
        # the pairing a reader would make.
        nearby = list(dict.fromkeys(
            ref
            for entry in report.citations
            for ref in entry.refs
            if entry.text and entry.text in paragraph
        ))

        for quotation in hebrew_runs(paragraph):
            found_in = ""
            for ref in nearby:
                if ref not in fetched:
                    fetched[ref] = _passage_text(ref)
                if skeleton_contains(fetched[ref], quotation):
                    found_in = ref
                    break
            report.quotations.append(
                QuotationCheck(
                    quotation=quotation,
                    found_in=found_in,
                    checked_against=tuple(nearby),
                )
            )
    return report
