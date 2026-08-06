"""Work out which romanization scheme a piece of Latin text was written under.

Why this is useful
------------------
Most of the time nobody tells you. A quotation arrives in an email, a co-author
sends a draft, an old file turns up. Knowing that it says `ḥokhmah` rather than
`chochma` tells you the writer was following SBL, which tells you what to match
when you add to it, and often something about where the piece was going.

How it works
------------
Every signature is derived from the scheme tables rather than listed by hand.
That matters: the previous version kept a hand-written list of tell-tale
characters, the list drifted from the tables, and it went on carrying a spirant
set after the same characters had been deleted from the scheme they came from.
Deriving means a signature cannot outlive its evidence.

The method has two halves. Evidence for a scheme is any value it emits that
appears in the text, weighted by how few schemes emit it: a value only one scheme
produces is worth a whole point, one that four produce is worth a quarter.
Evidence against is any marked character in the text that the scheme cannot
produce at all, which is decisive in the other direction, since a scheme that
cannot write `ḥ` did not write a text containing one.

Absolute uniqueness would be too strict to be useful. The two ALA-LC schemes
share almost every value, so neither has anything all to itself, and requiring
uniqueness would make both undetectable along with SBL general. Rarity
distinguishes them; uniqueness does not.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from meturgaman.scheme import Scheme, all_schemes

__all__ = ["Guess", "signatures", "detect", "explain"]


@dataclass(frozen=True)
class Guess:
    """One scheme, the evidence for it, and the evidence against."""

    scheme: str
    score: float
    matched: tuple[str, ...]
    #: Marked characters in the text this scheme cannot produce. Any entry here
    #: is close to conclusive that the text is not in this scheme.
    impossible: tuple[str, ...] = ()

    @property
    def is_possible(self) -> bool:
        return not self.impossible

    def __str__(self) -> str:
        found = ", ".join(repr(value) for value in self.matched[:6])
        text = f"{self.scheme} ({self.score:.2f}: {found})"
        if self.impossible:
            text += f" but cannot write {', '.join(repr(c) for c in self.impossible)}"
        return text


_SIGNATURES: dict[str, frozenset[str]] | None = None


def signatures(*, reload: bool = False) -> dict[str, frozenset[str]]:
    """For each scheme, the values that only it emits.

    Single letters that every scheme shares (`b`, `m`, `l`) carry no information
    and fall out automatically, because they are not unique to anyone.
    """
    global _SIGNATURES
    if _SIGNATURES is not None and not reload:
        return _SIGNATURES

    schemes = all_schemes()
    emitted = {name: scheme.romanizations() for name, scheme in schemes.items()}

    derived: dict[str, frozenset[str]] = {}
    for name, values in emitted.items():
        derived[name] = frozenset(
            value
            for value in values
            # A bare ASCII letter is never diagnostic on its own; what
            # distinguishes schemes is the marked characters and the digraphs.
            if value and (len(value) > 1 or not value.isascii())
        )

    _SIGNATURES = derived
    return derived


def _rarity() -> dict[str, int]:
    """How many schemes emit each value. A value one scheme emits is worth most."""
    counts: dict[str, int] = {}
    for values in signatures().values():
        for value in values:
            counts[value] = counts.get(value, 0) + 1
    return counts


_PRODUCIBLE: dict[str, frozenset[str]] | None = None


def producible() -> dict[str, frozenset[str]]:
    """Every letter each scheme can put on the page, in lower case.

    This is the evidence-against half, and it works on ASCII as well as on marked
    characters. A text containing `ḥ` was not written under a scheme whose only h
    is `ẖ`; a text containing a bare `q` was not written under ALA-LC, whose qof
    is always `ḳ`. The second case is what separates ALA-LC from SBL general,
    which are otherwise nearly identical and would otherwise tie.

    Lower case throughout, because a scheme that joins its prefixes capitalizes
    what follows, and `H̱okhmah` should still count as BGN's `ẖ`.
    """
    global _PRODUCIBLE
    if _PRODUCIBLE is not None:
        return _PRODUCIBLE

    built: dict[str, frozenset[str]] = {}
    for name, scheme in all_schemes().items():
        characters: set[str] = set()
        for value in scheme.romanizations():
            characters.update(value.lower())
        built[name] = frozenset(characters)
    _PRODUCIBLE = built
    return built


def _occurrences(text: str, value: str) -> int:
    """How many times a romanization value appears, as a whole token where it can be.

    A single marked character such as `ẖ` is counted wherever it appears. A
    digraph such as `kh` is counted only between word boundaries or inside a
    word, never spanning two words.
    """
    if len(value) == 1 and not value.isascii():
        return text.count(value)
    return len(re.findall(re.escape(value), text))


def detect(text: str, *, limit: int = 3) -> list[Guess]:
    """Rank the schemes by how much of the text only they could have produced.

    Returns an empty list when nothing distinctive is present, which is the
    honest answer for a word like `shalom` that half the schemes would spell the
    same way.
    """
    text = unicodedata.normalize("NFC", text)
    lowered = text.lower()
    rarity = _rarity()
    can_produce = producible()
    results: list[Guess] = []

    # Every letter actually on the page. Punctuation is shared by everything and
    # says nothing, so only letters count.
    present = {character for character in lowered if character.isalpha()}

    for name, values in signatures().items():
        matched: list[str] = []
        score = 0.0
        for value in sorted(values, key=len, reverse=True):
            count = _occurrences(lowered, value.lower())
            if count:
                score += count / rarity.get(value, 1)
                matched.append(value)

        impossible = tuple(sorted(present - can_produce[name]))
        if score or impossible:
            results.append(
                Guess(
                    scheme=name,
                    score=round(score, 3),
                    matched=tuple(matched),
                    impossible=impossible,
                )
            )

    # A scheme that cannot produce a character in the text goes below every
    # scheme that can, however much other evidence it accumulated.
    results.sort(key=lambda guess: (bool(guess.impossible), -guess.score, guess.scheme))
    return [guess for guess in results if guess.score or not guess.impossible][:limit]


def explain(text: str) -> str:
    """A short report for a person, naming the evidence rather than just a verdict."""
    guesses = detect(text)
    if not guesses:
        return (
            "No scheme can be identified: this text uses nothing that only one "
            "scheme produces."
        )
    lines = ["Most likely first, with the evidence:"]
    for guess in guesses:
        found = ", ".join(repr(value) for value in guess.matched[:8])
        lines.append(f"  {guess.scheme:34} {guess.score:>3}  {found}")
    if len(guesses) > 1 and guesses[0].score == guesses[1].score:
        lines.append("")
        lines.append("The top two tie, so this is not a determination.")
    return "\n".join(lines)


def undetectable() -> list[str]:
    """Schemes with no marked or multi-character value at all.

    Used by a test. A scheme landing here has nothing to recognize it by, which
    would be worth knowing about.
    """
    return sorted(name for name, values in signatures().items() if not values)
