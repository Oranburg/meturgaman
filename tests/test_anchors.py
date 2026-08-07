"""shape_summary() on fabricated shape records.

The summarizer is what turns the service's shape payload into a countable
census, and a census is exactly where answers have gone wrong, so the
reduction itself gets pinned here against hand-built payloads whose right
answer is known in advance.
"""

from __future__ import annotations

from meturgaman.sources.sefaria import shape_summary


def _record(chapters, title="Test Work"):
    return [{"title": title, "book": title, "length": len(chapters),
             "chapters": chapters}]


def test_a_sparse_work_counts_only_populated_positions():
    # Chapter 1 empty; chapter 2 holds one gloss at position 5; chapter 3
    # holds glosses at 2 and 7, the latter with two segments.
    (work,) = shape_summary(_record([0, [0, 0, 0, 0, 1], [0, 1, 0, 0, 0, 0, 2]]))
    assert work.chapters == 3
    assert [(a.reference, a.segments) for a in work.anchors] == [
        ("2:5", 1), ("3:2", 1), ("3:7", 2),
    ]
    assert work.populated == 3
    assert work.total_segments == 4


def test_an_evenly_gridded_work_counts_chapters():
    (work,) = shape_summary(_record([8, 11, 12]))
    assert [(a.reference, a.segments) for a in work.anchors] == [
        ("1", 8), ("2", 11), ("3", 12),
    ]
    assert work.total_segments == 31


def test_an_entirely_empty_work_has_no_anchors():
    (work,) = shape_summary(_record([0, 0, [0, 0]]))
    assert work.anchors == ()
    assert work.populated == 0


def test_damaged_payloads_do_not_crash():
    assert shape_summary(None) == []
    assert shape_summary(["not a dict"]) == []
    assert shape_summary({"title": "X", "chapters": "wrong type"})[0].anchors == ()


def test_a_dict_payload_is_treated_as_one_record():
    works = shape_summary({"title": "Solo", "chapters": [3]})
    assert len(works) == 1
    assert works[0].title == "Solo"
