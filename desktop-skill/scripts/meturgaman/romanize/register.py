"""Tell Ashkenazi spelling from Sephardi, and refuse to convert one into the other.

The incident this exists to prevent
-----------------------------------
A previous version of this tooling was pointed at a folder of notes and asked to
regularize the Hebrew. It changed `shaliach` to `shaliaḥ` throughout a file that
used `Shabbos` nineteen times and `halachah` seven. The file was written in
Ashkenazi register, deliberately, by someone who knows the difference. The edit
was not a correction; it was an error introduced into a correct document, and it
was introduced silently across every occurrence at once.

So: this module identifies which register a piece of text is written in, and the
tool refuses to normalize a file whose register it did not choose.

What separates the two
----------------------
Ashkenazi and Sephardi differ in a small number of places, and each of them
leaves a visible mark in romanization:

  tav without dagesh   Shabbos, Akeidas, Bereishis     against   Shabbat, Akeidat
  qamats               Toyre, Moshiach                 against   Torah, Mashiach
  ḥet and khaf         chochma, halacha, Chanukah      against   ḥokhmah, Hanukkah
  tsere                Bereishis, Sheini               against   Bereshit, Sheni

None of these is decisive alone. `Chanukah` appears in plenty of otherwise
Sephardi writing, and a single `-os` proves nothing. The evidence is counted and
reported with its strength, and a thin margin is reported as thin.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

__all__ = ["Register", "detect_register", "preserve_guard", "RegisterConflict"]

ASHKENAZI = "ashkenazi"
SEPHARDI = "sephardi"
UNDETERMINED = "undetermined"


class RegisterConflict(Exception):
    """Refusal to rewrite a file into a register it was not written in."""


# Each entry is (pattern, register, weight, what it shows).
#
# Whole words score higher than spelling habits, because a word like `Shabbos`
# can only be Ashkenazi while a `ch` can be an accident of someone's keyboard.
_MARKERS: tuple[tuple[str, str, int, str], ...] = (
    (r"\b\w*[oa]s\b(?<!\bas\b)(?<!\bis\b)(?<!\bus\b)", ASHKENAZI, 0, "unused placeholder"),
    (r"\bShabbos\b", ASHKENAZI, 3, "tav read as s"),
    (r"\bShabbes\b", ASHKENAZI, 3, "tav read as s"),
    (r"\bAkeidas\b", ASHKENAZI, 3, "tav read as s"),
    (r"\bBereishis\b", ASHKENAZI, 3, "tav read as s, tsere as ei"),
    (r"\bSukkos\b", ASHKENAZI, 3, "tav read as s"),
    (r"\bShavuos\b", ASHKENAZI, 3, "tav read as s"),
    (r"\bmitzvos\b", ASHKENAZI, 3, "tav read as s"),
    (r"\bhalach", ASHKENAZI, 2, "khaf written ch"),
    (r"\bchochm", ASHKENAZI, 2, "ḥet and khaf written ch"),
    (r"\bToyre\b", ASHKENAZI, 3, "holam read oy"),
    (r"\bMoshiach\b", ASHKENAZI, 2, "qamats read o, ḥet written ch"),
    (r"\byomim\b", ASHKENAZI, 2, "qamats read o"),
    (r"\bShabbat\b", SEPHARDI, 3, "tav read as t"),
    (r"\bSukkot\b", SEPHARDI, 3, "tav read as t"),
    (r"\bShavuot\b", SEPHARDI, 3, "tav read as t"),
    (r"\bmitzvot\b", SEPHARDI, 3, "tav read as t"),
    (r"\bBereshit\b", SEPHARDI, 3, "tav read as t"),
    (r"\bhalakh", SEPHARDI, 2, "khaf written kh"),
    (r"\bḥokhm", SEPHARDI, 2, "ḥet marked, khaf written kh"),
    (r"\bMashiach\b", SEPHARDI, 2, "qamats read a"),
    (r"[ḥṭṣẓḳ]", SEPHARDI, 1, "underdotted consonants, an academic Sephardi habit"),
)

_ASHKENAZI_SUFFIX = re.compile(
    r"\b(?:[A-Za-z]{2,})(?:os|us)\b"
)
_SEPHARDI_SUFFIX = re.compile(r"\b(?:[A-Za-z]{2,})ot\b")


@dataclass
class Register:
    """Which register a text is written in, and why that was concluded."""

    register: str
    ashkenazi_score: int = 0
    sephardi_score: int = 0
    evidence: list[str] = field(default_factory=list)

    @property
    def is_confident(self) -> bool:
        """True when one register leads clearly enough to act on."""
        high = max(self.ashkenazi_score, self.sephardi_score)
        low = min(self.ashkenazi_score, self.sephardi_score)
        return high >= 3 and high >= low * 2

    def __str__(self) -> str:
        if self.register == UNDETERMINED:
            return "register undetermined"
        confidence = "clear" if self.is_confident else "weak"
        return (
            f"{self.register} ({confidence}: "
            f"ashkenazi {self.ashkenazi_score}, sephardi {self.sephardi_score})"
        )

    def report(self) -> str:
        lines = [str(self)]
        lines.extend(f"  {item}" for item in self.evidence)
        return "\n".join(lines)


def detect_register(text: str) -> Register:
    """Decide whether a text is written in Ashkenazi or Sephardi romanization."""
    text = unicodedata.normalize("NFC", text)
    ashkenazi = 0
    sephardi = 0
    evidence: list[str] = []

    for pattern, register, weight, description in _MARKERS:
        if weight == 0:
            continue
        found = re.findall(pattern, text, re.IGNORECASE)
        if not found:
            continue
        points = weight * len(found)
        if register == ASHKENAZI:
            ashkenazi += points
        else:
            sephardi += points
        evidence.append(
            f"{len(found):>3} x {description} ({register}, +{points})"
        )

    # Plural endings, counted together rather than word by word.
    os_endings = len(_ASHKENAZI_SUFFIX.findall(text))
    ot_endings = len(_SEPHARDI_SUFFIX.findall(text))
    if os_endings:
        ashkenazi += os_endings
        evidence.append(f"{os_endings:>3} x plural in -os or -us (ashkenazi, +{os_endings})")
    if ot_endings:
        sephardi += ot_endings
        evidence.append(f"{ot_endings:>3} x plural in -ot (sephardi, +{ot_endings})")

    if ashkenazi == sephardi:
        register = UNDETERMINED
    else:
        register = ASHKENAZI if ashkenazi > sephardi else SEPHARDI

    return Register(
        register=register,
        ashkenazi_score=ashkenazi,
        sephardi_score=sephardi,
        evidence=evidence,
    )


def preserve_guard(text: str, target_scheme: str, *, force: bool = False) -> None:
    """Raise before rewriting text into a register it was not written in.

    The schemes in this project all produce Sephardi or academic spelling, apart
    from the two Yiddish ones. Rewriting an Ashkenazi document under any of them
    replaces the author's usage with a different community's, which is not a
    normalization but a change of voice.

    Pass `force=True` to proceed anyway. The point is that it has to be said out
    loud rather than happening by default.
    """
    if force:
        return

    found = detect_register(text)
    if found.register != ASHKENAZI or not found.is_confident:
        return
    if target_scheme in ("yivo", "ala-lc-yiddish"):
        return  # Both preserve Ashkenazi readings rather than overwriting them.

    raise RegisterConflict(
        f"This text is written in Ashkenazi register "
        f"(ashkenazi {found.ashkenazi_score}, sephardi {found.sephardi_score}), "
        f"and {target_scheme} would rewrite it as Sephardi. That is a change of "
        f"the author's usage rather than a correction.\n"
        + "\n".join(f"  {item}" for item in found.evidence)
        + "\n\nUse --force to do it anyway, or --scheme yivo to stay in register."
    )
