"""The shelf builder, offline.

Checked live on 2026-09-13: rebuilt from Sefaria, Zohar, Balak 13:178, Malbim on
Hosea 10:9:1 and Ibn Ezra on Exodus 20:20:1 matched the shelf records staged the
day before byte for byte, apart from the fetch date. These tests hold the rules
that produced them without touching the network.
"""

from __future__ import annotations

import json

import pytest

from meturgaman import printpdf, shelf
from meturgaman.sources.sefaria import Edition, Observation, Reading, Ref, Segment

ZOHAR_INDEX = {
    "categories": ["Kabbalah", "Zohar"],
    "alt_structs": {"Daf": {"nodes": [{
        "titles": [{"lang": "en", "text": "Volume III"}],
        "nodes": [{
            "titles": [{"lang": "en", "text": "Balak"}],
            "startingAddress": "184b",
            "refs": [f"Zohar, Balak {i + 1}:1-{i + 1}:10" for i in range(20)]
                    + ["Zohar, Balak 13:170-13:190"],
        }],
    }]}},
}


def test_the_zohar_daf_is_counted_from_the_starting_address():
    # Node index 20 from 184b is offset 21: ten leaves on, the b side.
    assert shelf.zohar_daf("Zohar, Balak 13:178", ZOHAR_INDEX) == ("Zohar III:194b", "")


def test_a_segment_no_daf_node_covers_is_refused_not_guessed():
    daf, why = shelf.zohar_daf("Zohar, Balak 99:1", ZOHAR_INDEX)
    assert daf is None and "no daf node" in why


def _reading(ref, editions):
    return Reading(ref=Ref(raw=ref, normalized=ref, url_ref=ref.replace(" ", "_")),
                   observations=[Observation(edition=e, segments=[Segment(anchor=f"{ref}:1", text=t)])
                                 for e, t in editions])


def _raw(indexes):
    def raw(path):
        if path.startswith("/v3/texts/"):
            return {"indexTitle": "Malbim on Hosea"}
        if path.startswith("/topics/"):
            return {"primaryTitle": {"en": "Meir Leibush Weisser (Malbim)"},
                    "properties": {"birthYear": {"value": 1809}, "deathYear": {"value": 1879}}}
        return indexes
    return raw


def test_a_record_names_the_author_not_the_slug_and_flags_an_unstated_licence():
    reading = _reading("Malbim on Hosea 10:9:1",
                       [(Edition(title="Malbim on Hosea--Wikisource", language="he", license=""), "מימי הגבעה")])
    manifest = shelf.Manifest(entries=[], saga="Dan and Idolatry", labelled_by="Labelled translation, test")
    entry = shelf.Entry(ref="Malbim on Hosea 10:9:1", echoes="Judges 18:30 (causal claim)",
                        labelled_translation="From the days of Gibeah.")
    index = {"categories": ["Tanakh", "Acharonim on Tanakh"], "authors": ["malbim"], "pubDate": [1874]}
    record = shelf.build(entry, manifest, today="2026-09-13",
                         read=lambda *a, **k: reading, raw=_raw(index))
    assert 'author: "Meir Leibush Weisser (Malbim)"' in record.text
    assert "malbim\n" not in record.text
    assert 'licence: "unknown, check the licence (Hebrew); translation is not a published edition' in record.text
    assert 'translation: "Labelled translation, test"' in record.text
    assert "From the days of Gibeah." in record.text
    assert "year: 1874" in record.text
    assert 'saga: "Dan and Idolatry"' in record.text
    assert any("no licence stated" in line for line in record.log)


def test_no_source_edition_raises_and_build_all_reports_it(tmp_path):
    reading = _reading("X 1:1", [(Edition(title="English only", language="en", license="CC-BY"), "x")])
    manifest = shelf.Manifest(entries=[shelf.Entry(ref="X 1:1")])
    records, failures = shelf.build_all(manifest, tmp_path, read=lambda *a, **k: reading, raw=_raw({}))
    assert records == [] and "no Hebrew or Aramaic edition" in failures[0]
    assert not any(tmp_path.iterdir())


def test_a_manifest_with_no_entries_is_refused(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"saga": "S", "entries": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        shelf.load_manifest(path)


def test_an_explicit_browser_path_that_does_not_exist_is_refused():
    with pytest.raises(OSError):
        printpdf.find_browser("/no/such/browser")
