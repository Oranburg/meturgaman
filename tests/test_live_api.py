"""Contract tests against the live services.

These check that the shape of what Sefaria and Hebcal return is still the shape
this code reads. They are the tests that notice when an API changes underneath a
working program, which is the failure mode that produces confident wrong answers
rather than errors.

They need the network, so they are marked and can be skipped:

    pytest -m "not network"

They are also where several genuinely surprising facts about these APIs are
written down, each of which cost time to find and none of which is documented:

  * `version=all` on Sefaria's v3 texts returns an **empty** `versions` list and
    puts the metadata in `available_versions`. Asking for everything gets you
    nothing.
  * The `version` parameter wants the full language name. `hebrew|Title` works
    and `he|Title` returns nothing at all, with no error.
  * Naming fifty editions in one query string produces a 502.
  * `source_proj` must be true on a search or every `_source` comes back empty.
"""

from __future__ import annotations

import re

import pytest

pytestmark = pytest.mark.network


def _skip_on_network_trouble(error: Exception) -> None:
    from meturgaman.net import NetworkError

    if isinstance(error, NetworkError):
        pytest.skip(f"service unreachable: {error}")
    raise error


# ---------------------------------------------------------------------------
# Sefaria
# ---------------------------------------------------------------------------

def test_a_reference_resolves():
    from meturgaman.sources import sefaria

    try:
        ref = sefaria.resolve("Genesis 1:1")
    except Exception as error:
        _skip_on_network_trouble(error)
    assert ref.normalized == "Genesis 1:1"
    assert ref.url_ref == "Genesis_1:1"


def test_the_canonical_reference_forms_resolve():
    from meturgaman.sources import sefaria

    for citation in (
        "Berakhot 2a",
        "Mishneh Torah, Repentance 1:1",
        "Guide for the Perplexed, Part 1 1",
        "Shulchan Arukh, Orach Chayim 1:1",
    ):
        try:
            assert sefaria.resolve(citation).normalized
        except LookupError:
            pytest.fail(f"{citation!r} no longer resolves")
        except Exception as error:
            _skip_on_network_trouble(error)


def test_a_fabricated_citation_is_refused():
    """The endpoint answers 200 with `is_ref: false` and no error key.

    Without checking that field, every invented citation validated and was
    printed as though it were a passage. This is the single most important
    refusal in the package.
    """
    from meturgaman.sources import sefaria

    for citation in ("Fabricated Book 9:9", "Nonsense 5:5", "Not A Real Work 1:1"):
        try:
            found = sefaria.resolve(citation)
        except LookupError:
            continue
        except Exception as error:
            _skip_on_network_trouble(error)
        pytest.fail(f"{citation!r} validated as {found.normalized!r}")


def test_a_refusal_offers_candidates_without_choosing_one():
    """A shorthand a reader writes is refused, with what it might be.

    `Hilchot Teshuvah` is not a title Sefaria indexes. Naming the candidates
    makes the refusal useful; picking one would be worse than refusing, because
    Sefaria ranks `Mishneh Torah, Repentance` first for `Hilchot Deot` too, and
    that is a different book.
    """
    from meturgaman.sources import sefaria

    try:
        sefaria.resolve("Hilchot Teshuvah 1:1")
    except LookupError as error:
        assert "Did you mean" in str(error)
        assert "Mishneh Torah" in str(error)
        return
    except Exception as error:
        _skip_on_network_trouble(error)
    pytest.fail("a shorthand title resolved when it should have been refused")


def test_a_passage_comes_back_with_its_edition_and_licence():
    from meturgaman.sources import sefaria

    try:
        reading = sefaria.read("Genesis 1:1")
    except Exception as error:
        _skip_on_network_trouble(error)

    assert reading.observations
    for observation in reading.observations:
        assert observation.edition.title
        assert observation.edition.language
    assert reading.independent_witnesses >= 1


def test_version_all_needs_the_two_step_and_gets_several_editions():
    """The undocumented behaviour, pinned so a change is noticed."""
    from meturgaman.sources import sefaria

    try:
        reading = sefaria.read("Genesis 1:1", version="all", max_editions=8)
    except Exception as error:
        _skip_on_network_trouble(error)
    assert len(reading.observations) >= 4, (
        "version=all returned almost nothing, which is what happens when the "
        "two-step fetch stops working"
    )
    assert reading.independent_witnesses >= 2


def test_independent_witnesses_deduplicates_by_provider():
    """Editions that share a digitization source are one witness, not several.

    The old assertion (`witnesses <= editions`) was true by construction and
    tested nothing. This one requires an actual collapse: among the first
    eight editions of Genesis 1:1 at least two share a provider, so the
    witness count must come out strictly below the edition count, and it must
    equal the number of distinct providers.
    """
    from meturgaman.sources import sefaria

    try:
        reading = sefaria.read("Genesis 1:1", version="all", max_editions=8)
    except Exception as error:
        _skip_on_network_trouble(error)
    providers = [observation.edition.provider for observation in reading.observations]
    assert reading.independent_witnesses == len(set(providers))
    assert len(set(providers)) < len(providers), (
        "expected at least two Genesis 1:1 editions from one provider; "
        f"got {providers}"
    )


def test_text_only_leaves_no_markup_behind():
    from meturgaman.sources import sefaria

    try:
        reading = sefaria.read("Exodus 22:24")
    except Exception as error:
        _skip_on_network_trouble(error)
    for observation in reading.observations:
        assert "<" not in observation.joined
        # A bare ampersand is legitimate text ("Rav & Shmuel" in some
        # translation is fine); an ampersand that opens an entity is markup.
        assert not re.search(r"&#?\w+;", observation.joined), (
            "an HTML entity survived; `&thinsp;` used to reach the output"
        )


def test_topic_sources_answer_the_question_they_are_for():
    """"What does the tradition say about X" has to return citations."""
    from meturgaman.sources import sefaria

    try:
        refs = sefaria.topic_sources("lending", limit=5)
    except Exception as error:
        _skip_on_network_trouble(error)
    assert refs, "no curated sources for a topic that certainly has them"
    assert any("Exodus" in ref or "Deuteronomy" in ref or "Bava" in ref for ref in refs)


def test_search_returns_populated_results():
    """Without `source_proj`, every hit comes back with an empty `_source`."""
    from meturgaman.sources import sefaria

    try:
        hits = sefaria.search("ribbit", limit=3)
    except Exception as error:
        _skip_on_network_trouble(error)
    assert hits
    assert any(hit.ref for hit in hits), "hits came back with no references"


def test_the_lexicon_takes_hebrew_in_the_url():
    from meturgaman.sources import sefaria

    try:
        entries = sefaria.lookup_word("צדקה")
    except Exception as error:
        _skip_on_network_trouble(error)
    assert entries
    assert any(entry.senses for entry in entries)


def test_a_talmud_reference_maps_to_its_sugya():
    """The boundary has to be a real passage, not an echo of the input.

    `assert found` passed for any truthy string, including the input itself.
    A mapped sugya is a range in the same tractate that differs from what was
    asked, and for a mid-page reference it spans more than one segment.
    """
    from meturgaman.sources import sefaria

    try:
        found = sefaria.passage_boundary("Bava Metzia 75b:2")
    except Exception as error:
        _skip_on_network_trouble(error)
    assert found is not None
    assert found != "Bava Metzia 75b:2"
    assert found.startswith("Bava Metzia")
    assert "-" in found, f"expected a range, got {found!r}"


# ---------------------------------------------------------------------------
# Hebcal
# ---------------------------------------------------------------------------

def test_the_committed_spec_still_matches_the_service():
    """A locale from the committed enum is still one the live service accepts.

    The old version of this test was marked network and made no network call,
    so it could never notice Hebcal dropping a locale. Now it asks the live
    service for a date in the rarest Ashkenazi locale the spec lists and
    requires an answer, which fails if the enum has drifted.
    """
    from meturgaman.sources import hebcal

    assert "s" in hebcal.LOCALES
    assert "a" in hebcal.LOCALES
    assert "ashkenazi_litvish" in hebcal.ASHKENAZI_LOCALES
    assert "sh" not in hebcal.ASHKENAZI_LOCALES, (
        "the spec's own table says sh is Sephardic transliteration with Hebrew"
    )
    try:
        day = hebcal.read_day("2026-09-12", locale="ashkenazi_litvish")
    except Exception as error:
        _skip_on_network_trouble(error)
    assert day.locale == "ashkenazi_litvish"
    assert day.hebrew_date.year == 5787
    # The proof the locale reached the service: Rosh Hashanah comes back in
    # Litvish dress.
    assert any("Reish Hashono" in event.title for event in day.events), (
        [event.title for event in day.events]
    )


def test_a_date_converts_and_carries_its_hebrew():
    from meturgaman.sources import hebcal

    try:
        found = hebcal.convert("2026-08-08")
    except Exception as error:
        _skip_on_network_trouble(error)
    assert found.year == 5786
    assert found.month
    assert found.hebrew


def test_the_locale_actually_changes_the_transliteration():
    """`a` should give Ashkenazi forms where `s` gives Sephardi ones."""
    from meturgaman.sources import hebcal

    try:
        sephardi = hebcal.read_day("2026-08-08", locale="s")
        ashkenazi = hebcal.read_day("2026-08-08", locale="a")
    except Exception as error:
        _skip_on_network_trouble(error)

    sephardi_titles = " ".join(event.title for event in sephardi.events)
    ashkenazi_titles = " ".join(event.title for event in ashkenazi.events)
    assert sephardi_titles != ashkenazi_titles, (
        "the locale made no difference, so it is probably not being sent"
    )


def test_leyning_returns_aliyot_and_a_haftarah():
    from meturgaman.sources import hebcal

    try:
        reading = hebcal.leyning("2026-08-08")
    except Exception as error:
        _skip_on_network_trouble(error)
    assert reading is not None
    assert reading.name
    assert len(reading.aliyot) >= 7
    assert reading.haftarah


def test_an_undocumented_parameter_is_refused():
    """Validation comes from the committed spec, so it should reject nonsense."""
    from meturgaman.sources import hebcal

    with pytest.raises(ValueError):
        hebcal.read_day("2026-08-08", locale="klingon")


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

def test_recorded_cantillation_exists_for_the_torah():
    from meturgaman.sources import audio

    try:
        found = audio.recordings("Genesis 1:1")
    except Exception as error:
        _skip_on_network_trouble(error)
    assert found, "PocketTorah recordings have gone from Sefaria's media array"
    recording = found[0]
    assert recording.url.endswith(".mp3")
    assert recording.license
    assert recording.duration and recording.duration > 0


def test_the_talmud_has_no_recordings_and_says_so():
    """The honest negative. Nobody has recorded the Talmud verse by verse."""
    from meturgaman.sources import audio

    try:
        found = audio.recordings("Berakhot 2a")
    except Exception as error:
        _skip_on_network_trouble(error)
    assert found == []


def test_find_refs_returns_the_citations_it_finds():
    """The endpoint became asynchronous and the reader did not notice.

    It answered with a task id, the code read that as though it held results,
    and the feature reported "no citations found" for every input with a
    success exit code. Nothing in the suite covered it.
    """
    from meturgaman.sources import sefaria

    try:
        found = sefaria.find_refs("See Genesis 1:1 and also Berakhot 2a.")
    except Exception as error:
        _skip_on_network_trouble(error)

    refs = [ref for entry in found for ref in (entry.get("refs") or [])]
    assert "Genesis 1:1" in refs, refs
    assert "Berakhot 2a" in refs, refs
