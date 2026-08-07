"""The draft checker's pure logic, offline.

The run finder and the skeleton matcher decide what gets checked and what
counts as found; both must be right before the network parts mean anything.
"""

from __future__ import annotations

from meturgaman.verify import (
    CitationCheck,
    Divergence,
    QuotationCheck,
    Report,
    diagnose,
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


def test_diagnose_names_the_first_diverging_word():
    source = "בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם"
    found = diagnose(source, "בראשית ברא משה את השמים", ref="Genesis 1:1")
    assert found.matched == "בראשית ברא"
    assert found.draft_word == "משה"
    # The edition's word arrives as the edition prints it, pointing and all.
    assert found.edition_word == "אֱלֹהִים"
    assert "then the draft has" in found.describe()


def test_diagnose_picks_the_best_alignment_not_the_first():
    # The quotation starts mid-verse; the match must anchor there, not at
    # the verse's opening word.
    source = "ויאמר אלהים יהי אור ויהי אור"
    found = diagnose(source, "יהי אור ויהי חשך", ref="Genesis 1:3")
    assert found.matched == "יהי אור ויהי"
    assert found.draft_word == "חשך"
    assert found.edition_word == "אור"


def test_diagnose_says_when_nothing_matches():
    found = diagnose("שמע ישראל", "ברוך אתה", ref="Deuteronomy 6:4")
    assert found.matched == ""
    assert "no run of words matches" in found.describe()


def test_diagnose_reports_a_draft_running_past_the_passage_end():
    found = diagnose("שמע ישראל", "שמע ישראל השם אלקינו", ref="Deuteronomy 6:4")
    assert found.matched == "שמע ישראל"
    assert found.draft_word == "השם"
    assert found.edition_word == ""
    assert "past the passage's end" in found.describe()


def test_render_carries_the_divergence_line():
    report = Report(
        quotations=[
            QuotationCheck(
                quotation="א ב ג",
                checked_against=("Genesis 1:1",),
                divergence=Divergence(
                    ref="Genesis 1:1", matched="א ב",
                    draft_word="ג", edition_word="ד",
                ),
            )
        ],
    )
    text = report.render()
    assert "NOT FOUND" in text
    assert "matches Genesis 1:1 through 'א ב'" in text


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
