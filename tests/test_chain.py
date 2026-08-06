"""build_chain() on fabricated link records.

The chain is what turns Sefaria's flat link list into the shelf order a
learner walks. These tests pin the order, the grouping, and the tolerance for
records that arrive damaged.
"""

from __future__ import annotations

from meturgaman.chain import CATEGORY_ORDER, build_chain


def _link(ref: str, category: str, work: str = "") -> dict:
    record: dict = {"ref": ref, "category": category}
    if work:
        record["collectiveTitle"] = {"en": work, "he": ""}
    return record


def test_categories_come_out_in_transmission_order():
    links = [
        _link("Shulchan Arukh, Choshen Mishpat 201:1", "Halakhah"),
        _link("Genesis 1:1", "Tanakh"),
        _link("Rashi on Bava Metzia 74a:3:1", "Commentary", "Rashi"),
        _link("Mishnah Bava Metzia 5:11", "Mishnah"),
    ]
    found = [group.category for group in build_chain(links)]
    assert found == ["Tanakh", "Mishnah", "Commentary", "Halakhah"]


def test_an_unknown_category_lands_after_the_known_ones():
    links = [
        _link("Something 1", "Brand New Category"),
        _link("Genesis 1:1", "Tanakh"),
    ]
    found = [group.category for group in build_chain(links)]
    assert found == ["Tanakh", "Brand New Category"]


def test_links_group_by_work_and_deduplicate():
    links = [
        _link("Rashi on Bava Metzia 74a:3:1", "Commentary", "Rashi"),
        _link("Rashi on Bava Metzia 74a:3:1", "Commentary", "Rashi"),
        _link("Rashi on Bava Metzia 74a:5:1", "Commentary", "Rashi"),
        _link("Tosafot on Bava Metzia 74a:3:1", "Commentary", "Tosafot"),
    ]
    (commentary,) = build_chain(links)
    assert commentary.works["Rashi"] == [
        "Rashi on Bava Metzia 74a:3:1",
        "Rashi on Bava Metzia 74a:5:1",
    ]
    assert commentary.count == 3


def test_a_link_without_a_collective_title_uses_the_index_title():
    links = [{"ref": "Tur, Choshen Mishpat 201", "category": "Halakhah",
              "index_title": "Tur"}]
    (halakhah,) = build_chain(links)
    assert list(halakhah.works) == ["Tur"]


def test_damaged_records_are_dropped_rather_than_crashing():
    links = [
        "not a dict",
        {"category": "Halakhah"},          # no ref at all
        {"ref": "", "category": "Tanakh"},  # empty ref
        _link("Genesis 1:1", "Tanakh"),
    ]
    found = build_chain(links)
    assert len(found) == 1
    assert found[0].count == 1


def test_the_order_constant_is_free_of_duplicates():
    assert len(CATEGORY_ORDER) == len(set(CATEGORY_ORDER))
