"""`sources --text` must survive one bad item in a topic's curated list.

A curated topic's sources are not all plain text: a Sefaria sheet answers
with a shape `read` cannot parse, and the fetch raises `NetworkError` rather
than a lookup failure. The per-item handler already caught `LookupError` and
`ValueError`; `NetworkError` was not in that tuple, so one such item crashed
the whole command instead of being reported and skipped like any other bad
source.

Reproduced with fabricated data rather than a live topic, since which real
topic currently has a sheet in its source list is not a stable thing to pin
a test to.
"""

from __future__ import annotations

import pytest

from meturgaman.cli import main
from meturgaman.net import NetworkError
from meturgaman.sources import sefaria


@pytest.fixture()
def two_sources_one_broken(monkeypatch):
    # The broken item comes first: the bug was that it crashed the whole
    # command, so nothing after it printed either. Ordering it first is what
    # a passing test on the old code could not fake.
    monkeypatch.setattr(
        sefaria, "topic_sources", lambda slug, limit=10: ["Sheet 409392", "Genesis 1:1"]
    )

    real_edition = sefaria.Edition(
        title="Fabricated", language="he", source="https://example.org", license="CC0"
    )
    good_reading = sefaria.Reading(
        ref=sefaria.Ref(raw="Genesis 1:1", normalized="Genesis 1:1", url_ref="Genesis_1:1"),
        observations=[sefaria.Observation(
            edition=real_edition,
            segments=[sefaria.Segment(anchor="1:1", text="בראשית ברא")],
        )],
    )

    def fake_read(ref, *args, **kwargs):
        if ref == "Sheet 409392":
            raise NetworkError("sefaria returned HTTP 400 for Sheet 409392")
        return good_reading

    monkeypatch.setattr(sefaria, "read", fake_read)


def test_a_network_error_on_one_source_does_not_abort_the_rest(
    two_sources_one_broken, capsys
):
    code = main(["sources", "some-topic", "--text"])
    captured = capsys.readouterr()
    assert code == 0
    assert "Genesis 1:1" in captured.out
    assert "בראשית ברא" in captured.out
    # The broken item is reported in place, not left out and not fatal to
    # the item that follows it.
    assert "Sheet 409392" in captured.out
    assert "HTTP 400" in captured.out
