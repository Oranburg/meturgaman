"""The draft checker's pure logic, offline.

The run finder and the skeleton matcher decide what gets checked and what
counts as found; both must be right before the network parts mean anything.
"""

from __future__ import annotations

from meturgaman.verify import (
    CitationCheck,
    QuotationCheck,
    Report,
    hebrew_runs,
    skeleton_contains,
)


def test_hebrew_runs_finds_a_run_inside_english():
    found = hebrew_runs("The verse says בראשית ברא אלהים and continues.")
    assert found == ["בראשית ברא אלהים"]


def test_hebrew_runs_ignores_short_glosses():
    # Two words is vocabulary being glossed, not a quotation to check.
    assert hebrew_runs("the term אסמכתא בעלמא appears here") == []


def test_hebrew_runs_splits_at_english_interruptions():
    text = "אמר רבי יוחנן משום and then שמעון בן יוחאי אומר דבר"
    found = hebrew_runs(text)
    assert found == ["אמר רבי יוחנן משום", "שמעון בן יוחאי אומר דבר"]


def test_skeleton_contains_survives_pointing_differences():
    pointed = "בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים אֵ֥ת הַשָּׁמַ֖יִם וְאֵ֥ת הָאָֽרֶץ׃"
    assert skeleton_contains(pointed, "ברא אלהים את השמים")


def test_skeleton_contains_requires_contiguity():
    source = "בראשית ברא אלהים את השמים ואת הארץ"
    # The words exist, but not adjacently; a stitched quotation must fail.
    assert not skeleton_contains(source, "בראשית אלהים הארץ")


def test_skeleton_contains_rejects_a_changed_word():
    source = "בראשית ברא אלהים את השמים"
    assert not skeleton_contains(source, "בראשית ברא משה את השמים")


def test_skeleton_contains_rejects_empty_and_oversized_needles():
    assert not skeleton_contains("בראשית ברא", "")
    assert not skeleton_contains("בראשית", "בראשית ברא אלהים")


def test_report_is_clean_only_when_everything_passed():
    good = Report(
        citations=[CitationCheck(text="Genesis 1:1", refs=("Genesis 1:1",), resolved=True)],
        quotations=[QuotationCheck(quotation="א ב ג", found_in="Genesis 1:1")],
    )
    assert good.clean

    bad_citation = Report(
        citations=[CitationCheck(text="Genesis 99:1", refs=(), resolved=False)],
    )
    assert not bad_citation.clean

    bad_quotation = Report(
        quotations=[QuotationCheck(quotation="א ב ג", checked_against=("Genesis 1:1",))],
    )
    assert not bad_quotation.clean


def test_render_marks_each_outcome_distinctly():
    report = Report(
        citations=[
            CitationCheck(text="Genesis 1:1", refs=("Genesis 1:1",), resolved=True),
            CitationCheck(text="Genesis 99:1", refs=(), resolved=False),
        ],
        quotations=[
            QuotationCheck(quotation="א ב ג", found_in="Genesis 1:1"),
            QuotationCheck(quotation="ד ה ו", checked_against=("Genesis 1:1",)),
            QuotationCheck(quotation="ז ח ט"),
        ],
    )
    text = report.render()
    assert "resolved" in text
    assert "UNRESOLVED" in text
    assert "found" in text
    assert "NOT FOUND" in text
    assert "UNCHECKED" in text


def test_an_empty_draft_says_so():
    assert "nothing to check" in Report().render()
