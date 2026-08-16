"""Go the other way: from a romanization back to Hebrew letters.

What this can and cannot do
---------------------------
Romanization loses information, and how much depends entirely on the scheme.
SBL academic is built to be reversible and very nearly is. SBL general is not:
it writes `t` for both tet and tav and `k` for both kaf and qof, so `torah` could
begin with either of two letters and nothing in the string says which.

So this returns candidates rather than an answer, ranked, with the ambiguities
named. Anyone who wants one answer should say which scheme the text is in, and
`detect.py` will often work that out from the text itself.

Vowels are not reconstructed at all. Pointing a word requires knowing which word
it is, and guessing at it would be inventing text, which this project does not
do anywhere.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from meturgaman import hebrew
from meturgaman.scheme import Scheme, all_schemes, scheme_named

__all__ = ["Candidate", "reverse", "inverse_map"]


@dataclass
class Candidate:
    """One possible Hebrew spelling of a romanized word."""

    letters: str
    scheme: str
    #: Points in the string where more than one letter could have produced the
    #: same romanization.
    ambiguities: list[str] = field(default_factory=list)

    @property
    def is_certain(self) -> bool:
        return not self.ambiguities

    def __str__(self) -> str:
        if self.is_certain:
            return self.letters
        return f"{self.letters}  ({'; '.join(self.ambiguities)})"


def inverse_map(scheme: Scheme) -> dict[str, list[str]]:
    """Every Latin value this scheme emits, mapped back to the letters producing it.

    Built from the scheme's own tables, so it cannot describe a scheme that has
    changed underneath it.
    """
    inverse: dict[str, list[str]] = {}

    def record(value: str, letter: str) -> None:
        if not value:
            return
        inverse.setdefault(value, [])
        if letter not in inverse[value]:
            inverse[value].append(letter)

    for letter, value in scheme.plain.items():
        if hebrew.is_final(letter):
            continue  # a final form spells the same word as its base
        record(value, letter)
    for letter, value in scheme.dagesh.items():
        if hebrew.is_final(letter):
            continue
        record(value, letter)
    for letter, value in scheme.rafe.items():
        record(value, letter + hebrew.RAFE)
    for letter, value in scheme.geresh.items():
        record(value, letter + hebrew.GERESH)
    if scheme.shin:
        record(scheme.shin, hebrew.SHIN + hebrew.SHIN_DOT)
    if scheme.sin:
        record(scheme.sin, hebrew.SHIN + hebrew.SIN_DOT)
    for sequence, value in scheme.sequences.items():
        record(value, sequence)

    return inverse


def _reverse_word(lowered: str, keys: list[str], inverse: dict[str, list[str]],
                   vowels: set[str], scheme_name: str) -> tuple[list[str], list[str]]:
    """The letters and ambiguities for one word, no spaces inside it.

    Factored out of `_reverse_one` so a multi-word phrase can apply the
    final-letter fix-up once per word rather than once for the whole
    reconstruction: run on the joined string, only the very last letter of
    the last word ever saw the fix, and every other word-final consonant
    stayed in its medial shape.
    """
    letters: list[str] = []
    ambiguities: list[str] = []
    position = 0

    while position < len(lowered):
        for key in keys:
            if not key:
                continue
            if lowered.startswith(key.lower(), position):
                options = inverse[key]
                letters.append(options[0])
                if len(options) > 1:
                    ambiguities.append(
                        f"{key!r} could be " + " or ".join(options)
                    )
                position += len(key)
                break
        else:
            character = lowered[position]
            if character in vowels or character in "aeiou":
                # A vowel with no letter of its own was written as a point, and
                # points are not reconstructed.
                pass
            elif character in "-’‘ʾʿʼʻ":
                pass
            else:
                ambiguities.append(f"{character!r} matches nothing in {scheme_name}")
            position += 1

    # Hebrew writes five letters differently at the end of a word, and a
    # reconstruction that ignores that produces a spelling no reader recognizes:
    # `שׁלמ` rather than `שׁלום`.
    if letters:
        tail = letters[-1]
        if len(tail) == 1 and tail in hebrew.BASE_TO_FINAL:
            letters[-1] = hebrew.BASE_TO_FINAL[tail]

    return letters, ambiguities


def _reverse_one(text: str, scheme: Scheme) -> Candidate:
    inverse = inverse_map(scheme)
    keys = sorted(inverse, key=len, reverse=True)
    vowels = {value for value in scheme.vowels.values() if value}
    vowels |= {
        str(scheme.rule(key))
        for key in ("shva_na", "tsere_male", "hireq_male", "holam_male", "shuruq")
    }
    vowels.discard("")

    # Split on whitespace before scanning, not during it: a space is a word
    # boundary, not decoration to discard like an apostrophe. Discarding it
    # in the same branch as diacritics used to run every word together and
    # apply the final-letter fix-up only to the very last letter of the
    # entire phrase.
    words = text.lower().split()
    all_letters: list[str] = []
    all_ambiguities: list[str] = []
    for word in words:
        letters, ambiguities = _reverse_word(word, keys, inverse, vowels, scheme.name)
        all_letters.append("".join(letters))
        all_ambiguities.extend(ambiguities)

    return Candidate(
        letters=" ".join(all_letters), scheme=scheme.name, ambiguities=all_ambiguities
    )


def reverse(text: str, scheme: str | Scheme | None = None) -> list[Candidate]:
    """Hebrew spellings that could have produced this romanization.

    With a scheme named, one candidate. Without, one per scheme, ordered by how
    little had to be guessed.

    >>> reverse("shalom", "sbl-general")[0].letters
    'שׁלם'
    """
    text = unicodedata.normalize("NFC", text)

    if scheme is not None:
        chosen = scheme if isinstance(scheme, Scheme) else scheme_named(scheme)
        return [_reverse_one(text, chosen)]

    candidates = [
        _reverse_one(text, available) for available in all_schemes().values()
    ]
    candidates.sort(key=lambda candidate: (len(candidate.ambiguities), candidate.scheme))
    return candidates
