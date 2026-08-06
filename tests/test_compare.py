"""compare() on fabricated readings.

Every reading here is built by hand, so each test knows exactly what the right
answer is before the code runs. This module had no coverage at all, and it is
where the reconciliation logic lives, so a regression here would have shipped
silently.
"""

from __future__ import annotations

from meturgaman.compare import (
    ABBREVIATION,
    INTERPOLATION,
    SUBSTANTIVE,
    compare,
)
from meturgaman.sources.sefaria import Edition, Observation, Reading, Ref, Segment


def _reading(*observations: Observation) -> Reading:
    ref = Ref(raw="Test 1:1", normalized="Test 1:1", url_ref="Test_1:1")
    return Reading(ref=ref, observations=list(observations))


def _observation(title: str, text: str, *, language: str = "he",
                 source: str = "") -> Observation:
    edition = Edition(
        title=title,
        language=language,
        source=source or f"https://example.org/{title}",
    )
    return Observation(edition=edition, segments=[Segment(anchor="1:1", text=text)])


def test_identical_editions_agree():
    found = compare(_reading(
        _observation("A", "בראשית ברא אלהים"),
        _observation("B", "בְּרֵאשִׁית בָּרָא אֱלֹהִים"),
    ))
    assert found.agrees
    assert found.differences == []
    # Vocalization differences are recorded as apparatus, not as variants.
    assert len(found.apparatus) == 2


def test_a_single_edition_compares_nothing():
    found = compare(_reading(_observation("A", "בראשית ברא")))
    assert found.nothing_compared
    # And crucially: one witness is not "agreement".
    assert not found.agrees
    assert "not agreement" in found.report()


def test_no_editions_compares_nothing():
    found = compare(_reading())
    assert found.nothing_compared
    assert not found.agrees


def test_different_letters_are_substantive():
    found = compare(_reading(
        _observation("A", "בראשית ברא אלהים"),
        _observation("B", "בראשית ברא אלוהים"),
    ))
    kinds = [item.kind for item in found.differences]
    assert kinds == [SUBSTANTIVE]
    assert found.substantive == found.differences
    assert found.differences[0].is_worth_reading


def test_a_marked_abbreviation_is_not_a_variant():
    found = compare(_reading(
        _observation("A", "אמר ה׳ אל משה"),
        _observation("B", "אמר השם אל משה"),
    ))
    kinds = [item.kind for item in found.differences]
    assert kinds == [ABBREVIATION]
    assert not found.differences[0].is_worth_reading


def test_missing_words_are_interpolation():
    found = compare(_reading(
        _observation("A", "אמר רבא"),
        _observation("B", "אמר רבא בר בר חנה"),
    ))
    kinds = [item.kind for item in found.differences]
    assert kinds == [INTERPOLATION]


def test_translations_are_not_compared_against_the_hebrew():
    found = compare(_reading(
        _observation("A", "בראשית ברא"),
        _observation("English", "In the beginning", language="en"),
    ))
    # Only one Hebrew edition remains, so nothing was compared, rather than
    # every Hebrew word being reported as a difference from the English.
    assert found.nothing_compared
    assert found.editions == ["A"]


def test_independent_witnesses_counts_providers_not_rows():
    same_host = "https://tanach.us/x"
    found = compare(_reading(
        _observation("A", "בראשית", source=same_host),
        _observation("B", "בראשית", source=same_host),
        _observation("C", "בראשית", source="https://elsewhere.org/y"),
    ))
    assert len(found.editions) == 3
    assert found.independent_witnesses == 2


def test_report_lists_each_difference_once():
    found = compare(_reading(
        _observation("A", "שמע ישראל"),
        _observation("B", "שמע שראל"),
    ))
    text = found.report()
    assert "substantive" in text
    assert text.count("[substantive]") == 1
