"""Offline tests for sefaria_bulk: shape walking, counting, resume, and rate limits."""

from __future__ import annotations

import json
import sys
import urllib.error
from pathlib import Path

from meturgaman import bulk
from meturgaman.net import NetworkError

COMPLEX_SHAPE = [{
    "title": "Work", "isComplex": True,
    "chapters": [
        {"title": "Work, Introduction", "chapters": 3},
        {"title": "Work, Part 1", "chapters": [2, 0, 1]},
    ],
}]

VERSIONS = [
    {"versionTitle": "Free English", "language": "en", "languageFamilyName": "english",
     "actualLanguage": "en", "license": "Public Domain", "versionSource": "x"},
    {"versionTitle": "Closed Hebrew", "language": "he", "languageFamilyName": "hebrew",
     "actualLanguage": "he", "license": "unknown", "versionSource": "y"},
]

TEXTS = {
    "/v3/texts/Work,_Introduction": ["a", "b", "c"],
    "/v3/texts/Work,_Part_1.1": ["d", "e"],
    "/v3/texts/Work,_Part_1.3": ["f"],
}


def fake_service(calls, fail_on=None):
    def get(path, params=None):
        calls.append(path)
        if fail_on and path == fail_on:
            raise NetworkError("sefaria returned HTTP 429") from urllib.error.HTTPError(
                path, 429, "Too Many Requests", {}, None)
        if path.startswith("/shape/"):
            return COMPLEX_SHAPE
        if path.startswith("/texts/versions/"):
            return VERSIONS
        names = params["version"]
        assert names == ["english|Free English"], names
        return {"versions": [{"versionTitle": "Free English", "language": "en",
                              "license": "Public Domain", "text": TEXTS[path]}]}
    return get


def test_leaves_walk_a_complex_shape():
    found = bulk.leaves(COMPLEX_SHAPE)
    assert [(leaf.title, leaf.expected_chapters, leaf.expected_segments) for leaf in found] == [
        ("Work, Introduction", 1, 3), ("Work, Part 1", 2, 3)]
    assert bulk.section_refs(found[1]) == [("Work, Part 1 1", 2), ("Work, Part 1 3", 1)]


def test_a_simple_shape_is_one_leaf():
    (leaf,) = bulk.leaves([{"title": "Simple", "chapters": [4, 5]}])
    assert leaf.expected_chapters == 2 and leaf.expected_segments == 9


def test_flatten_anchors_like_sefaria():
    assert bulk.flatten(["x", "", "y"], "Work, Part 1 2", False) == [
        ("Work, Part 1 2:1", "x"), ("Work, Part 1 2:3", "y")]
    assert bulk.flatten(["x"], "Work, Introduction", True) == [("Work, Introduction 1", "x")]


def test_fetch_counts_against_shape_and_skips_unknown_licence(tmp_path):
    calls = []
    manifest = bulk.fetch_work("Work", tmp_path, get=fake_service(calls), sleep=lambda s: None)
    (row,) = manifest["versions"]
    assert row["complete_against_shape"] is True and row["segments"] == 6
    assert manifest["skipped_versions"][0]["title"] == "Closed Hebrew"
    assert not (tmp_path / "Work" / "he-Closed-Hebrew.json").exists()
    saved = json.loads((tmp_path / "Work" / "en-Free-English.json").read_text(encoding="utf-8"))
    assert saved["segments"][0] == {"ref": "Work, Introduction 1", "text": "a"}


def test_second_run_resumes_without_refetching(tmp_path):
    bulk.fetch_work("Work", tmp_path, get=fake_service([]), sleep=lambda s: None)
    calls = []
    bulk.fetch_work("Work", tmp_path, get=fake_service(calls), sleep=lambda s: None)
    assert not [c for c in calls if c.startswith("/v3/")]


def test_rate_limited_is_not_fetched_yet_never_missing(tmp_path):
    calls = []
    manifest = bulk.fetch_work("Work", tmp_path, retries=2, sleep=lambda s: None,
                               get=fake_service(calls, fail_on="/v3/texts/Work,_Part_1.3"))
    assert calls.count("/v3/texts/Work,_Part_1.3") == 3
    (gap,) = manifest["sections_not_fetched_yet"]
    assert gap["ref"] == "Work, Part 1 3" and "not fetched yet" in gap["reason"]
    assert manifest["versions"][0]["complete_against_shape"] is False
    # and a later run fills the gap
    manifest = bulk.fetch_work("Work", tmp_path, get=fake_service([]), sleep=lambda s: None)
    assert manifest["sections_not_fetched_yet"] == []
    assert manifest["versions"][0]["complete_against_shape"] is True


def test_one_title_in_two_languages_stays_two_files(tmp_path):
    listing = [
        {"versionTitle": "Same", "language": "en", "languageFamilyName": "english",
         "actualLanguage": "en", "license": "Public Domain"},
        {"versionTitle": "Same", "language": "he", "languageFamilyName": "hebrew",
         "actualLanguage": "he", "license": "Public Domain"},
    ]

    def get(path, params=None):
        if path.startswith("/shape/"):
            return [{"title": "Small", "chapters": [1]}]
        if path.startswith("/texts/versions/"):
            return listing
        return {"versions": [
            {"versionTitle": "Same", "language": "en", "text": ["english words"]},
            {"versionTitle": "Same", "language": "he", "text": ["מילים"]},
        ]}

    manifest = bulk.fetch_work("Small", tmp_path, get=get, sleep=lambda s: None)
    assert [(row["language"], row["segments"]) for row in manifest["versions"]] == [
        ("en", 1), ("he", 1)]
    assert all(row["complete_against_shape"] for row in manifest["versions"])
