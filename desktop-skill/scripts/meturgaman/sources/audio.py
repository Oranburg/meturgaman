"""Hear a passage read aloud, two different ways.

There are two honest answers to "read this to me", and they are good at
different things.

**Recorded cantillation.** Sefaria's `/api/related/{ref}` returns a `media` array,
and for the Torah that array holds PocketTorah's recordings: a human being
chanting, with the trope, licensed CC-BY-SA, and timestamped to the verse.
`Genesis 1:1` comes back with an MP3 and the span 2.028 to 9.018 seconds. This is
the real thing and nothing synthetic approaches it.

Its limit is coverage. `Berakhot 2a` returns an empty array, because nobody has
recorded the Talmud verse by verse. This module says so rather than quietly
falling back, because a reader who asked for cantillation and got a robot should
be told.

**Synthetic speech.** macOS ships a Hebrew voice, `Carmit`, for `he_IL`. It is
offline, free, already installed, and will read anything, including Aramaic, the
Talmud, and a phrase you typed. It is also a speech synthesizer reading liturgy,
which is worth knowing before pressing play.

Vocalization matters here more than it seems. Hebrew text without points is
genuinely ambiguous, and a synthesizer given `שבת` has to guess. Passing pointed
text is the difference between a usable reading and a wrong one, so this asks for
a pointed edition when it can and warns when it cannot get one.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from meturgaman import hebrew
from meturgaman.net import get_bytes
from meturgaman.sources import sefaria

__all__ = [
    "Recording",
    "Spoken",
    "recordings",
    "speak",
    "read_aloud",
    "available_voices",
    "HEBREW_VOICE",
]

#: The Hebrew voice macOS installs by default.
HEBREW_VOICE = "Carmit"


@dataclass(frozen=True)
class Recording:
    """A human recording of a passage."""

    ref: str
    url: str
    source: str
    license: str = ""
    start_time: float | None = None
    end_time: float | None = None
    description: str = ""

    @property
    def duration(self) -> float | None:
        if self.start_time is None or self.end_time is None:
            return None
        return round(self.end_time - self.start_time, 3)

    @property
    def attribution(self) -> str:
        parts = [self.source]
        if self.license:
            parts.append(self.license)
        return ", ".join(part for part in parts if part)

    def download(self, destination: Path | str) -> Path:
        """Save the audio file. The whole file, not just this verse's span."""
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(get_bytes(self.url, service=self.source))
        return destination

    def __str__(self) -> str:
        span = ""
        if self.start_time is not None:
            span = f" [{self.start_time:.2f}s to {self.end_time:.2f}s]"
        return f"{self.source}{span}  {self.url}"


@dataclass
class Spoken:
    """The result of asking for synthetic speech."""

    text: str
    voice: str
    path: Path | None = None
    played: bool = False
    warnings: list[str] = field(default_factory=list)


def recordings(citation: str) -> list[Recording]:
    """Human recordings of a passage, if any exist.

    Returns an empty list for most of the library. That is a fact about what has
    been recorded, not a failure, and the caller should say so plainly.
    """
    found: list[Recording] = []
    for entry in sefaria.media(citation):
        url = entry.get("media_url") or entry.get("url")
        if not url:
            continue

        def number(key: str) -> float | None:
            value = entry.get(key)
            if value in (None, ""):
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        found.append(
            Recording(
                ref=str(entry.get("anchorRef") or citation),
                url=str(url),
                source=str(entry.get("source") or "unknown"),
                license=str(entry.get("license") or ""),
                start_time=number("start_time"),
                end_time=number("end_time"),
                description=str(entry.get("description") or ""),
            )
        )
    return found


def available_voices() -> list[str]:
    """Hebrew voices installed on this machine."""
    if not shutil.which("say"):
        return []
    try:
        listing = subprocess.run(
            ["say", "-v", "?"], capture_output=True, text=True, timeout=10
        ).stdout
    except (subprocess.SubprocessError, OSError):  # pragma: no cover
        return []
    voices: list[str] = []
    for line in listing.splitlines():
        if "he_IL" in line:
            voices.append(line.split()[0])
    return voices


def speak(
    text: str,
    *,
    voice: str = HEBREW_VOICE,
    rate: int | None = None,
    output: Path | str | None = None,
    play: bool = True,
) -> Spoken:
    """Read Hebrew aloud with the local synthesizer.

    Nothing leaves the machine. `output` writes an AIFF file instead of, or as
    well as, playing.
    """
    warnings: list[str] = []

    if not shutil.which("say"):
        raise RuntimeError(
            "no local speech synthesizer found. This uses the macOS `say` "
            "command; on another platform, use `recordings()` for the passages "
            "that have human recordings."
        )

    installed = available_voices()
    if installed and voice not in installed:
        warnings.append(
            f"voice {voice!r} is not installed; using {installed[0]!r}. "
            f"Hebrew voices found: {', '.join(installed)}"
        )
        voice = installed[0]
    elif not installed:
        warnings.append(
            "no Hebrew voice is installed. Add one in System Settings, "
            "Accessibility, Spoken Content, System Voice, Manage Voices. "
            "Without one the reading will be wrong in a way that sounds fluent."
        )

    if hebrew.has_hebrew(text) and not any(
        hebrew.is_vowel(character) for character in text
    ):
        warnings.append(
            "this text carries no vowel points, so the synthesizer is guessing "
            "at the vowels. Fetch a pointed edition for a reading worth trusting."
        )

    command = ["say", "-v", voice]
    if rate:
        command += ["-r", str(rate)]
    path: Path | None = None
    if output is not None:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        command += ["-o", str(path)]
    command.append(text)

    try:
        subprocess.run(command, check=True, capture_output=True, timeout=300)
    except subprocess.CalledProcessError as error:  # pragma: no cover
        raise RuntimeError(
            f"speech failed: {error.stderr.decode('utf-8', 'replace')[:200]}"
        ) from error

    return Spoken(
        text=text,
        voice=voice,
        path=path,
        played=play and output is None,
        warnings=warnings,
    )


def read_aloud(
    citation: str,
    *,
    prefer: str = "recorded",
    voice: str = HEBREW_VOICE,
    output: Path | str | None = None,
) -> tuple[list[Recording], Spoken | None]:
    """Fetch a passage and get it read, preferring a human where one exists.

    `prefer="recorded"` returns the recordings when there are any and falls back
    to synthesis when there are none. `prefer="synthetic"` always synthesizes.
    Either way the recordings found are returned too, so the caller can say which
    one the reader is hearing.
    """
    found = recordings(citation) if prefer != "synthetic" else []
    if found and prefer == "recorded":
        return found, None

    reading = sefaria.read(citation, version="source")
    pointed = ""
    for observation in reading.observations:
        text = observation.joined
        if any(hebrew.is_vowel(character) for character in text):
            pointed = text
            break
    if not pointed and reading.observations:
        pointed = reading.observations[0].joined

    if not pointed:
        raise LookupError(f"no text found for {citation}")

    # Cantillation marks confuse the synthesizer without helping it, and the
    # vowels are what it actually needs.
    spoken = speak(
        hebrew.strip_cantillation(pointed), voice=voice, output=output
    )
    return found, spoken
