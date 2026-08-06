"""Compare the editions of a passage and report where they actually differ.

The problem with a naive diff
------------------------------
Ask Sefaria for every edition of a verse and you get a dozen strings that differ
in hundreds of places, almost all of which are noise. One edition has
cantillation and another does not. One spells the divine name in full and another
abbreviates. One has vowels, one has none, one has both plus a scribal note.

Diffing the raw strings buries the one disagreement that matters under two
hundred that do not.

What this does instead
----------------------
Comparison happens on the consonantal skeleton: letters only, final forms folded
to their base shapes. Vocalization and cantillation are apparatus, not variant
readings, and an edition that adds vowels is not disagreeing with one that omits
them.

A difference in the skeleton is a different matter. Those are worth a reader's
attention, and they are what this reports.

Three kinds of difference are recognized and separated, because they call for
different responses:

  **substantive**   the editions have different letters. Read both.
  **abbreviation**  one spells out what another abbreviates, `השם` against
                    `ה׳`. Usually not a variant at all.
  **interpolation** one has words the other lacks entirely, which in the Talmud
                    is usually a printed gloss absorbed into the text.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

from meturgaman import hebrew
from meturgaman.sources.sefaria import Observation, Reading

__all__ = ["Difference", "Apparatus", "Comparison", "compare",
           "SUBSTANTIVE", "ABBREVIATION", "INTERPOLATION"]

SUBSTANTIVE = "substantive"
ABBREVIATION = "abbreviation"
INTERPOLATION = "interpolation"

#: Marks that signal an abbreviation rather than a word: geresh and gershayim.
_ABBREVIATION_MARKS = (hebrew.GERESH, hebrew.GERSHAYIM, "'", '"')


@dataclass(frozen=True)
class Difference:
    """One place two editions disagree."""

    kind: str
    left_edition: str
    right_edition: str
    left: str
    right: str
    position: int = 0

    @property
    def is_worth_reading(self) -> bool:
        """True for the differences a scholar would want to look at."""
        return self.kind == SUBSTANTIVE

    def __str__(self) -> str:
        return f"[{self.kind}] {self.left!r} / {self.right!r}"


@dataclass(frozen=True)
class Apparatus:
    """A difference that is not a variant reading.

    Recorded rather than reported as a dispute. To a reader studying
    vocalization this is the interesting content; to a reader quoting the
    consonantal text it is noise. Keeping it labelled serves both, where
    discarding it serves only the second.
    """

    edition: str
    provider: str
    vocalization: str

    def __str__(self) -> str:
        return f"{self.edition} ({self.provider}): {self.vocalization}"


@dataclass
class Comparison:
    """Every edition of a passage, and where they part company."""

    ref: str
    editions: list[str] = field(default_factory=list)
    differences: list[Difference] = field(default_factory=list)
    independent_witnesses: int = 0
    #: How each edition points the text. Not a disagreement, but worth having.
    apparatus: list[Apparatus] = field(default_factory=list)

    @property
    def substantive(self) -> list[Difference]:
        return [item for item in self.differences if item.kind == SUBSTANTIVE]

    #: True when fewer than two editions were available, so nothing was compared.
    nothing_compared: bool = False

    @property
    def agrees(self) -> bool:
        """True only when a comparison happened and found no difference.

        With fewer than two editions there is no agreement to report, and
        saying "the consonantal text agrees everywhere" about a single witness
        is the system agreeing with itself.
        """
        return not self.nothing_compared and not self.differences

    def report(self) -> str:
        lines = [
            f"{self.ref}: {len(self.editions)} editions, "
            f"{self.independent_witnesses} independent witnesses"
        ]
        if self.nothing_compared:
            lines.append(
                "  Fewer than two editions in this language, so nothing was "
                "compared. This is not agreement."
            )
            return "\n".join(lines)

        if self.agrees:
            lines.append(
                "  The consonantal text agrees everywhere. Differences in "
                "vowels and cantillation are apparatus, not variants."
            )
            lines.extend(f"  apparatus: {item}" for item in self.apparatus)
            return "\n".join(lines)

        counts: dict[str, int] = {}
        for item in self.differences:
            counts[item.kind] = counts.get(item.kind, 0) + 1
        summary = ", ".join(f"{count} {kind}" for kind, count in sorted(counts.items()))
        lines.append(f"  {summary}")
        lines.append("")
        for item in self.differences:
            lines.append(f"  [{item.kind}]")
            lines.append(f"  {item.left_edition}  {item.left!r}")
            lines.append(f"  {item.right_edition}  {item.right!r}")
            lines.append("")
        return "\n".join(lines).rstrip()


def _looks_like_abbreviation(left: str, right: str) -> bool:
    """True when one side abbreviates what the other spells out."""
    for short, long in ((left, right), (right, left)):
        if not short or not long:
            continue
        if any(mark in short for mark in _ABBREVIATION_MARKS):
            head = hebrew.consonantal_skeleton(short)[:1]
            if head and hebrew.consonantal_skeleton(long).startswith(head):
                return True
        # A shared first letter and a length ratio is not evidence of an
        # abbreviation. It classified `בן` against `בראשית ברא אלהים` as one,
        # which removed a three-word difference from the report entirely. An
        # abbreviation is marked, and it is one word.
    return False


def _classify(left: str, right: str) -> str:
    if not left or not right:
        return INTERPOLATION
    if _looks_like_abbreviation(left, right):
        return ABBREVIATION
    return SUBSTANTIVE


def _words(observation: Observation) -> list[str]:
    """The words of an edition, reduced to their consonantal skeletons."""
    text = observation.joined
    return [
        hebrew.consonantal_skeleton(word)
        for word in text.split()
        if hebrew.has_hebrew(word)
    ]


def compare(reading: Reading, *, language: str = "he") -> Comparison:
    """Compare every edition of a passage in one language.

    Only editions in the same language are compared. Comparing a Hebrew text
    against its English translation would report every word as a difference,
    which is true and useless.
    """
    observations = [
        observation
        for observation in reading.observations
        if (observation.edition.language or "").lower().startswith(language.lower())
        or (observation.edition.actual_language or "").lower().startswith(language.lower())
    ]

    comparison = Comparison(
        ref=reading.ref.normalized,
        editions=[observation.edition.title for observation in observations],
        independent_witnesses=len(
            {observation.edition.provider for observation in observations}
        ),
    )

    for observation in observations:
        comparison.apparatus.append(
            Apparatus(
                edition=observation.edition.title,
                provider=observation.edition.provider,
                vocalization=hebrew.describe_vocalization(observation.joined),
            )
        )

    if len(observations) < 2:
        comparison.nothing_compared = True
        return comparison

    # Compare each edition against the first. Comparing every pair produces the
    # same findings several times over and reads as noise.
    base = observations[0]
    base_words = _words(base)

    for other in observations[1:]:
        other_words = _words(other)
        matcher = difflib.SequenceMatcher(None, base_words, other_words)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            left = " ".join(base_words[i1:i2])
            right = " ".join(other_words[j1:j2])
            comparison.differences.append(
                Difference(
                    kind=_classify(left, right),
                    left_edition=base.edition.title,
                    right_edition=other.edition.title,
                    left=left,
                    right=right,
                    position=i1,
                )
            )

    return comparison
