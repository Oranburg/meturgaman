"""study --vocalize wiring, with the model stubbed.

The model itself is a multi-gigabyte optional extra, so these tests exercise
everything around it: the refusal when it is absent, and, with a stub in its
place, the pointing of unvocalized segments, the provenance note, and the
promise that pointed editions are left alone.
"""

from __future__ import annotations

import pytest

from meturgaman.cli import main
from meturgaman.sources import dicta, sefaria


@pytest.fixture()
def fabricated_reading(monkeypatch):
    """A reading with one unpointed Hebrew segment and one pointed one."""
    hebrew_edition = sefaria.Edition(
        title="Fabricated Hebrew", language="he",
        source="https://example.org/he", license="Public Domain",
    )
    observation = sefaria.Observation(
        edition=hebrew_edition,
        segments=[
            sefaria.Segment(anchor="1:1", text="שלום עליכם"),
            sefaria.Segment(anchor="1:2", text="שָׁלוֹם"),
        ],
    )
    reading = sefaria.Reading(
        ref=sefaria.Ref(raw="Test 1", normalized="Test 1", url_ref="Test_1"),
        observations=[observation],
    )
    monkeypatch.setattr(sefaria, "read", lambda *args, **kwargs: reading)
    return reading


def test_without_the_extra_study_refuses_with_the_instruction(
    fabricated_reading, monkeypatch, capsys
):
    monkeypatch.setattr(dicta, "is_available", lambda: False)
    code = main(["study", "Test 1", "--vocalize", "--tier", "block"])
    captured = capsys.readouterr()
    assert code == 3
    assert "meturgaman[dicta]" in captured.err


def test_with_a_stub_only_unpointed_segments_are_pointed(
    fabricated_reading, monkeypatch, capsys
):
    pointed: list[str] = []

    def fake_vocalize(text):
        pointed.append(text)
        return dicta.Vocalized(text="שְׁלוֹם עֲלֵיכֶם", original=text)

    monkeypatch.setattr(dicta, "is_available", lambda: True)
    monkeypatch.setattr(dicta, "vocalize", fake_vocalize)

    code = main(["study", "Test 1", "--vocalize", "--tier", "file", "--quiet"])
    captured = capsys.readouterr()
    assert code == 0
    # Only the unpointed segment went to the model; the edition's own
    # pointing at 1:2 stayed the edition's.
    assert pointed == ["שלום עליכם"]
    assert "שְׁלוֹם עֲלֵיכֶם" in captured.out
    assert "שָׁלוֹם" in captured.out


def test_the_provenance_note_travels_with_the_output(
    fabricated_reading, monkeypatch, capsys
):
    monkeypatch.setattr(dicta, "is_available", lambda: True)
    monkeypatch.setattr(
        dicta, "vocalize",
        lambda text: dicta.Vocalized(text="שְׁלוֹם עֲלֵיכֶם", original=text),
    )
    code = main(["study", "Test 1", "--vocalize", "--tier", "block", "--quiet"])
    captured = capsys.readouterr()
    assert code == 0
    assert "[vocalized-by-model]" in captured.out
    assert "a model's reading, not an edition's" in captured.out


def test_without_the_flag_nothing_is_touched(fabricated_reading, capsys):
    code = main(["study", "Test 1", "--tier", "file", "--quiet"])
    captured = capsys.readouterr()
    assert code == 0
    assert "שלום עליכם" in captured.out
    assert "[vocalized-by-model]" not in captured.out
