"""Run the docstring examples, so an example cannot quietly go stale.

`reverse.reverse` shipped with an example whose printed output was not what
the function returned, and nothing noticed, because doctests were never
collected. The hebcal example talks to the service, so it runs with the
network tests; the other two run offline.
"""

from __future__ import annotations

import doctest

import pytest

import meturgaman.romanize.engine
import meturgaman.romanize.reverse
import meturgaman.sources.israel


@pytest.mark.parametrize(
    "module",
    [
        meturgaman.romanize.engine,
        meturgaman.romanize.reverse,
        meturgaman.sources.israel,
    ],
    ids=["engine", "reverse", "israel"],
)
def test_offline_doctests_pass(module):
    found = doctest.testmod(module)
    assert found.attempted > 0, f"{module.__name__} has doctests to run"
    assert found.failed == 0


@pytest.mark.network
def test_hebcal_doctests_pass():
    from meturgaman.sources import hebcal

    found = doctest.testmod(hebcal)
    assert found.attempted > 0
    assert found.failed == 0
