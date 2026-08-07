"""The companion-works document and its run-time half, offline.

The document names the pairs; the graph supplies the passages. These tests
pin the parsing of the real committed document and the pure link filter.
"""

from __future__ import annotations

from meturgaman.pairings import (
    Pairing,
    companions_for,
    filter_companion_links,
    load_pairings,
)


def test_the_committed_document_parses_and_carries_reasons():
    pairings = load_pairings()
    assert pairings, "rules/pairings.md declared no pairs"
    for pairing in pairings:
        assert pairing.work_prefix
        assert pairing.companion
        # Every row promised a reason a reader can check.
        assert len(pairing.why) > 20, pairing


def test_mishneh_torah_pairs_with_the_guide():
    found = companions_for("Mishneh Torah, Repentance")
    assert [p.companion for p in found] == ["Guide for the Perplexed"]


def test_an_unpaired_work_gets_nothing():
    assert companions_for("Genesis") == []


def test_filter_matches_on_index_title_and_deduplicates():
    links = [
        {"ref": "Guide for the Perplexed, Part 3 28:1",
         "index_title": "Guide for the Perplexed"},
        {"ref": "Guide for the Perplexed, Part 3 28:1",
         "index_title": "Guide for the Perplexed"},
        {"ref": "Rashi on Genesis 1:1:1", "index_title": "Rashi on Genesis"},
        "not a dict",
        {"index_title": "Guide for the Perplexed"},  # no ref
    ]
    found = filter_companion_links(links, "Guide for the Perplexed")
    assert found == ["Guide for the Perplexed, Part 3 28:1"]


def test_filter_requires_the_companion_prefix():
    links = [{"ref": "Beit Yosef, Choshen Mishpat 204:4:1",
              "index_title": "Beit Yosef"}]
    assert filter_companion_links(links, "Guide for the Perplexed") == []
    assert filter_companion_links(links, "Beit Yosef") == [
        "Beit Yosef, Choshen Mishpat 204:4:1"
    ]
