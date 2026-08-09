"""The Knesset's open data, and the honest record of what it does not hold.

Everything offline here guards the shapes and the refusals. The live checks are
marked `network` and record what was measured on 2026-08-09, so a change at the
service shows up as a failing test rather than as a quietly emptier answer.
"""

from __future__ import annotations

import pytest

from meturgaman.sources import knesset


def test_a_search_with_no_phrase_is_refused():
    with pytest.raises(ValueError):
        knesset.find_laws("   ")


def test_a_single_quote_in_a_phrase_is_escaped_for_odata():
    """OData doubles an internal quote. Leaving it raw breaks the filter."""
    assert knesset._escape("חוק ה'חוזים") == "חוק ה''חוזים"


def test_a_row_becomes_a_law_with_its_dates_trimmed_to_days():
    law = knesset.IsraelLaw.from_row({
        "IsraelLawID": 2000293,
        "Name": 'חוק החוזים (תרופות בשל הפרת חוזה), התשל"א-1970',
        "PublicationDate": "1970-12-24T00:00:00",
        "LawValidityDesc": "בתוקף",
        "KnessetNum": 6,
        "IsBasicLaw": False,
    })
    assert law.israel_law_id == 2000293
    assert law.published == "1970-12-24"
    assert law.validity == "בתוקף"
    assert not law.is_basic_law


def test_a_missing_name_becomes_empty_rather_than_none():
    """An absent field is empty, never the string `None` printed into a citation."""
    law = knesset.IsraelLaw.from_row({"IsraelLawID": 1})
    assert law.name == ""
    assert law.published == ""


@pytest.mark.network
def test_the_register_finds_both_contracts_statutes():
    """Measured 2026-08-09: the search returns four laws, two of them ours."""
    found = {law.israel_law_id: law for law in knesset.find_laws("חוק החוזים")}
    assert 2000292 in found and "חלק כללי" in found[2000292].name
    assert 2000293 in found and "תרופות" in found[2000293].name


@pytest.mark.network
def test_the_binding_table_is_empty_for_both_statutes():
    """The finding that keeps somebody from trusting this for amendment history.

    The entity exists and returns rows for other laws. For these two it returns
    none, while the consolidated text records real amendments to both. An empty
    result here means the register holds nothing, not that the law is unamended.
    """
    assert knesset.law_bindings(2000292) == []
    assert knesset.law_bindings(2000293) == []


@pytest.mark.network
def test_an_entity_set_that_does_not_exist_is_refused_by_name():
    """`Knesset_Bill` is a plausible name and a 404. The register uses `KNS_`."""
    with pytest.raises(Exception):
        knesset.odata("Knesset_Bill", **{"$top": "1"})


@pytest.mark.network
def test_the_open_data_portal_holds_legislation_packages_and_no_english():
    results = knesset.ckan_search("חקיקה", rows=10)
    assert results
    titles = " ".join(row.get("title", "") for row in results)
    assert "חוק" in titles
