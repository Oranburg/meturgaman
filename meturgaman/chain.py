"""Arrange what the tradition built on a passage into its transmission order.

Sefaria's link graph knows what connects to a passage: the Mishnah it discusses,
the commentaries on it, the codes that rule from it, the responsa that cite it.
The graph returns all of that as one flat list, which answers "what points
here" but not the question a learner actually has, which is "where did this go
next".

This module puts the flat list into the order the tradition itself moves:
Scripture, then Mishnah and Tosefta, then Talmud, then the commentators, then
the codes, then responsa and later thought. Reading down the chain from a
Gemara shows where its law lands in the Shulchan Arukh; reading up from a code
shows where its ruling began.

Nothing here is invented: every entry is a link Sefaria records, and every ref
in the output can be fetched. What this adds is only the shelf order, which is
public knowledge of the same standing as an alphabet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

__all__ = ["ChainGroup", "build_chain", "chain", "CATEGORY_ORDER"]

#: Sefaria's own top-level categories, in the order the tradition transmits.
#: A category Sefaria adds later lands after these, alphabetically, rather
#: than disappearing.
CATEGORY_ORDER = (
    "Tanakh",
    "Targum",
    "Mishnah",
    "Tosefta",
    "Talmud",
    "Midrash",
    "Commentary",
    "Quoting Commentary",
    "Halakhah",
    "Kabbalah",
    "Liturgy",
    "Jewish Thought",
    "Chasidut",
    "Musar",
    "Responsa",
)


@dataclass
class ChainGroup:
    """One stage of the chain: a category, and its links grouped by work."""

    category: str
    #: Work name (Sefaria's collectiveTitle, or the index title) to its refs.
    works: dict[str, list[str]] = field(default_factory=dict)

    @property
    def count(self) -> int:
        return sum(len(refs) for refs in self.works.values())


def _work_name(link: dict[str, Any]) -> str:
    collective = link.get("collectiveTitle")
    if isinstance(collective, dict) and collective.get("en"):
        return str(collective["en"])
    return str(link.get("index_title") or link.get("ref") or "(unnamed)")


def build_chain(links: Iterable[dict[str, Any]]) -> list[ChainGroup]:
    """Group raw link records by category and work, in transmission order.

    Pure: takes the list `sefaria.links()` returns and touches no network,
    so it can be tested against fabricated records.
    """
    by_category: dict[str, ChainGroup] = {}
    for link in links:
        if not isinstance(link, dict):
            continue
        ref = str(link.get("ref") or "")
        if not ref:
            continue
        category = str(link.get("category") or "(uncategorized)")
        group = by_category.setdefault(category, ChainGroup(category=category))
        refs = group.works.setdefault(_work_name(link), [])
        if ref not in refs:
            refs.append(ref)

    def position(category: str) -> tuple[int, str]:
        try:
            return (CATEGORY_ORDER.index(category), "")
        except ValueError:
            return (len(CATEGORY_ORDER), category)

    return sorted(by_category.values(), key=lambda group: position(group.category))


def chain(citation: str) -> tuple[str, list[ChainGroup]]:
    """The chain for a real reference: resolve it, fetch its links, order them."""
    from meturgaman.sources import sefaria

    ref = sefaria.resolve(citation)
    return ref.normalized, build_chain(sefaria.links(ref))
