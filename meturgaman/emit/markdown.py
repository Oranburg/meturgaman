"""Render a passage as markdown, in whichever of three shapes the use calls for.

The three tiers exist because a Hebrew quotation does three different jobs in a
piece of writing, and they want different amounts of room.

**Tier 1, the block quotation.** A passage quoted at length, Hebrew and
translation, with the citation and the edition under it. What goes in an article
when the text itself is the evidence.

**Tier 2, the teaching block.** Hebrew, romanization and translation stacked in
three lines. What goes in notes and in teaching material, where a reader is meant
to be able to say the words.

**Tier 3, the inline gloss.** A phrase inside a sentence, Hebrew with its
romanization and a short translation in parentheses. What goes in running prose.

Every tier names its edition. A Hebrew quotation with no edition behind it is not
a citation, and this refuses to produce one.
"""

from __future__ import annotations

from dataclasses import dataclass

from meturgaman.romanize.engine import romanize
from meturgaman.scheme import Scheme
from meturgaman.sources.sefaria import Reading

__all__ = ["block", "teaching", "inline", "study_file", "Rendered"]


@dataclass
class Rendered:
    """Markdown, and anything the reader should check before using it."""

    text: str
    flags: list[str]

    def __str__(self) -> str:
        return self.text


def _hebrew_and_translation(reading: Reading) -> tuple[str, str, str, str]:
    """Pick the Hebrew and the English out of a reading, with their editions."""
    hebrew_text = translation = ""
    hebrew_edition = translation_edition = ""
    for observation in reading.observations:
        language = (observation.edition.actual_language or observation.edition.language or "").lower()
        if not hebrew_text and language.startswith("he"):
            hebrew_text = observation.joined
            hebrew_edition = observation.edition.title
        elif not translation and language.startswith("en"):
            translation = observation.joined
            translation_edition = observation.edition.title
    return hebrew_text, hebrew_edition, translation, translation_edition


def block(reading: Reading, *, scheme: Scheme | str | None = None) -> Rendered:
    """Tier 1: a long quotation, for an article."""
    text, edition, english, english_edition = _hebrew_and_translation(reading)
    if not text:
        raise ValueError(f"no Hebrew found for {reading.ref.normalized}")

    lines = [f"> {text}", ">"]
    if english:
        lines += [f"> {english}", ">"]
    citation = f"> {reading.ref.normalized}"
    if edition:
        citation += f", {edition}"
    if english_edition and english_edition != edition:
        citation += f"; translation, {english_edition}"
    lines.append(citation)

    return Rendered(text="\n".join(lines), flags=[])


def teaching(
    reading: Reading, *, scheme: Scheme | str | None = None
) -> Rendered:
    """Tier 2: Hebrew, romanization and translation stacked."""
    text, edition, english, english_edition = _hebrew_and_translation(reading)
    if not text:
        raise ValueError(f"no Hebrew found for {reading.ref.normalized}")

    romanized = romanize(text, scheme)
    lines = [
        text,
        f"*{romanized.text}*",
    ]
    if english:
        lines.append(english)
    lines.append("")
    footer = f"{reading.ref.normalized}"
    if edition:
        footer += f" ({edition})"
    footer += f". Romanization: {romanized.scheme}."
    lines.append(footer)

    return Rendered(text="\n".join(lines), flags=[str(flag) for flag in romanized.flags])


def inline(
    text: str, translation: str = "", *, scheme: Scheme | str | None = None
) -> Rendered:
    """Tier 3: a phrase for the middle of a sentence."""
    romanized = romanize(text, scheme)
    gloss = f"{text} (*{romanized.text}*"
    if translation:
        gloss += f", {translation}"
    gloss += ")"
    return Rendered(text=gloss, flags=[str(flag) for flag in romanized.flags])


def study_file(
    reading: Reading,
    *,
    scheme: Scheme | str | None = None,
    title: str = "",
) -> Rendered:
    """A whole study file: heading, the passage segment by segment, and provenance."""
    heading = title or reading.ref.normalized
    lines = [f"# {heading}", ""]

    hebrew_text, edition, english, english_edition = _hebrew_and_translation(reading)
    flags: list[str] = []

    hebrew_observation = next(
        (
            observation
            for observation in reading.observations
            if (observation.edition.actual_language or observation.edition.language or "")
            .lower()
            .startswith("he")
        ),
        None,
    )
    english_observation = next(
        (
            observation
            for observation in reading.observations
            if (observation.edition.actual_language or observation.edition.language or "")
            .lower()
            .startswith("en")
        ),
        None,
    )

    if hebrew_observation is None:
        raise ValueError(f"no Hebrew edition for {reading.ref.normalized}")

    english_by_anchor = {}
    if english_observation is not None:
        english_by_anchor = {
            segment.anchor: segment.text for segment in english_observation.segments
        }

    for segment in hebrew_observation.segments:
        romanized = romanize(segment.text, scheme)
        flags.extend(str(flag) for flag in romanized.flags)
        lines.append(f"**{segment.anchor}**")
        lines.append("")
        lines.append(segment.text)
        lines.append("")
        lines.append(f"*{romanized.text}*")
        rendered_english = english_by_anchor.get(segment.anchor)
        if rendered_english:
            lines.append("")
            lines.append(rendered_english)
        lines.append("")

    lines.append("## Provenance")
    lines.append("")
    for observation in reading.observations:
        entry = observation.edition
        lines.append(
            f"- **{entry.title}** ({entry.language}), "
            f"{entry.source or 'no source stated'}, "
            f"licence {entry.license or 'unstated'}"
        )
    lines.append("")
    lines.append(reading.attribution)

    if flags:
        lines.append("")
        lines.append("## Check these")
        lines.append("")
        for flag in dict.fromkeys(flags):
            lines.append(f"- {flag}")

    return Rendered(text="\n".join(lines), flags=flags)
