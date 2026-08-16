"""Companion works, read from `rules/pairings.md`.

The pairing of a code with its author's reasoning (Mishneh Torah with the
Guide, Shulchan Arukh with the Beit Yosef) is reading practice, not data the
services provide, so it lives in a rules document a person can check and
extend. What this module adds is the run-time half: given a passage, ask
Sefaria's link graph which companion passages are actually recorded, and
report absence as absence.

Nothing here supplies a citation. The document names works; every
passage-level reference in the output is a link the graph returned.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from meturgaman.romanize.rules import rules_directory

__all__ = ["Pairing", "load_pairings", "companions_for", "filter_companion_links"]

_PAIRINGS: list["Pairing"] | None = None


@dataclass(frozen=True)
class Pairing:
    """One row of the table: study this, also open that, because."""

    work_prefix: str
    companion: str
    why: str


def load_pairings() -> list[Pairing]:
    """Every pairing the document declares. Empty when the file is absent."""
    global _PAIRINGS
    if _PAIRINGS is not None:
        return _PAIRINGS

    directory = rules_directory()
    found: list[Pairing] = []
    if directory is not None and (directory / "pairings.md").exists():
        for line in (directory / "pairings.md").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line.startswith("|") or set(line) <= set("|-: "):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) < 3 or cells[0].lower() == "when studying":
                continue
            found.append(Pairing(work_prefix=cells[0], companion=cells[1], why=cells[2]))
    _PAIRINGS = found
    return found


def companions_for(title: str) -> list[Pairing]:
    """The pairings that apply to a work, matched by title prefix."""
    return [
        pairing for pairing in load_pairings()
        if title.startswith(pairing.work_prefix)
    ]


def filter_companion_links(
    links: Iterable[dict[str, Any]], companion: str
) -> list[str]:
    """The refs among raw link records that belong to the companion work.

    Pure, so it is testable against fabricated records. Matches on the index
    title, which is the string the pairings document promises to use.
    """
    found: list[str] = []
    for link in links:
        if not isinstance(link, dict):
            continue
        ref = str(link.get("ref") or "")
        index_title = str(link.get("index_title") or "")
        if ref and index_title.startswith(companion) and ref not in found:
            found.append(ref)
    return found
