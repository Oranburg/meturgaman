"""The markdown tiers on fabricated readings.

The renderer had no coverage, and it is the last code every study file passes
through. These tests pin the properties a reader depends on: every tier names
its edition, flags survive into the result, and an empty romanization never
leaves a bare `**` in someone's notes.
"""

from __future__ import annotations

import pytest

from meturgaman.emit import markdown
from meturgaman.sources.sefaria import Edition, Observation, Reading, Ref, Segment

HEBREW = Edition(title="Test Hebrew", language="he",
                 source="https://example.org/he", license="Public Domain")
ENGLISH = Edition(title="Test English", language="en",
                  source="https://example.org/en", license="CC-BY")


def _reading(hebrew_texts: list[str], english_texts: list[str] | None = None) -> Reading:
    observations = [
        Observation(
            edition=HEBREW,
            segments=[
                Segment(anchor=f"1:{index}", text=text)
                for index, text in enumerate(hebrew_texts, start=1)
            ],
        )
    ]
    if english_texts is not None:
        observations.append(
            Observation(
                edition=ENGLISH,
                segments=[
                    Segment(anchor=f"1:{index}", text=text)
                    for index, text in enumerate(english_texts, start=1)
                ],
            )
        )
    ref = Ref(raw="Test 1", normalized="Test 1", url_ref="Test_1")
    return Reading(ref=ref, observations=observations)


def test_block_carries_text_translation_and_citation():
    rendered = markdown.block(_reading(["שָׁלוֹם"], ["Peace"]))
    assert "> שָׁלוֹם" in rendered.text
    assert "> Peace" in rendered.text
    assert "Test 1, Test Hebrew; translation, Test English" in rendered.text


def test_block_flags_an_unused_scheme():
    rendered = markdown.block(_reading(["שָׁלוֹם"]), scheme="sbl-general")
    assert any("scheme-unused" in flag for flag in rendered.flags)


def test_teaching_stacks_hebrew_romanization_translation():
    rendered = markdown.teaching(_reading(["שָׁלוֹם"], ["Peace"]))
    lines = rendered.text.splitlines()
    assert lines[0] == "שָׁלוֹם"
    assert lines[1] == "*shalom*"
    assert lines[2] == "Peace"
    assert "Romanization: sbl-general." in rendered.text


def test_every_tier_refuses_a_reading_with_no_hebrew():
    english_only = _reading([], [])
    english_only.observations = english_only.observations[1:]
    for tier in (markdown.block, markdown.teaching, markdown.interlinear,
                 markdown.study_file):
        with pytest.raises(ValueError):
            tier(english_only)


def test_interlinear_gives_one_line_per_word():
    rendered = markdown.interlinear(_reading(["כׇּל הָאָרֶץ"]))
    body = [line for line in rendered.text.splitlines() if line.startswith(">")]
    assert len(body) == 2


def test_an_empty_romanization_never_prints_bare_asterisks():
    # A sof pasuq alone romanizes to nothing at all.
    for tier in (markdown.teaching, markdown.interlinear):
        rendered = tier(_reading(["׃"]))
        assert "**" not in rendered.text
        assert "* *" not in rendered.text


def test_inline_glosses_a_phrase():
    rendered = markdown.inline("שָׁלוֹם", "peace")
    assert rendered.text == "שָׁלוֹם (*shalom*, peace)"


def test_inline_refuses_empty_text():
    # It used to return " (**)", which pasted invisible garbage into prose.
    with pytest.raises(ValueError):
        markdown.inline("")


def test_study_file_pairs_translation_by_anchor_and_lists_provenance():
    rendered = markdown.study_file(_reading(["שָׁלוֹם", "תּוֹרָה"], ["Peace", "Torah"]))
    assert "**1:1**" in rendered.text
    assert "**1:2**" in rendered.text
    assert "Torah" in rendered.text
    assert "## Provenance" in rendered.text
    assert "Public Domain" in rendered.text


def test_study_file_skips_a_hebrew_edition_with_no_segments():
    empty_hebrew = Observation(edition=HEBREW, segments=[])
    full_hebrew = Observation(
        edition=Edition(title="Full", language="he", source="https://example.org/f"),
        segments=[Segment(anchor="1:1", text="שָׁלוֹם")],
    )
    ref = Ref(raw="Test 1", normalized="Test 1", url_ref="Test_1")
    reading = Reading(ref=ref, observations=[empty_hebrew, full_hebrew])
    rendered = markdown.study_file(reading)
    assert "שָׁלוֹם" in rendered.text


def test_filename_for_is_stable_and_safe():
    reading = _reading(["א"])
    reading.ref = Ref(raw="x", normalized="Test 1:2", url_ref="Test_1:2")
    assert markdown.filename_for(reading) == "Test 1.2.md"


def test_write_refuses_a_directory(tmp_path):
    rendered = markdown.block(_reading(["שָׁלוֹם"]))
    with pytest.raises(IsADirectoryError):
        markdown.write(rendered, tmp_path)
    target = markdown.write(rendered, tmp_path / "out.md")
    assert target.read_text(encoding="utf-8").startswith("> שָׁלוֹם")
