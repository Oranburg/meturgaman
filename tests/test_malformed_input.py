"""Every command, pointed at input that is wrong rather than input that works.

Why this file exists
--------------------
The rest of the suite points each command at an argument meant to succeed,
which is what a suite written alongside a feature naturally does. Two faults
found on 2026-09-15 were invisible to all of it and were found instead by
running the commands by hand with nonsense in them:

  * `reverse ""` printed one blank candidate per scheme, exit 0, and under
    `--json` reported `is_certain` true on every one of them.
  * `word ""`, `anchors ""` and three others sent the request anyway, and a
    Sefaria path ending in its own slash is a 404 whose body is a web page,
    so the first 300 characters of that page became the stated reason.

Neither crashed, which is why nothing noticed. So this file asserts the three
properties a refusal has to have, across every command that can refuse without
the network: it does not raise, it exits non-zero, and its message is a
sentence rather than a fragment of somebody's HTML.

The network is blocked while these run. A refusal that can be decided from the
arguments alone should cost no request, and this is what holds that line: a
command that starts reaching out to decide that its input is malformed fails
here rather than quietly adding a round trip to every mistake.
"""

from __future__ import annotations

import contextlib
import io

import pytest

from meturgaman import net
from meturgaman.cli import main

#: Each case is the argv and what makes it wrong. Every one of them must be
#: decidable without leaving the machine.
CASES = [
    (["romanize", "שלום", "--scheme", "nonesuch"], "unknown scheme"),
    (["schemes", "--name", "nonesuch"], "unknown scheme, named"),
    (["reverse", ""], "nothing to reverse"),
    (["reverse", "123"], "nothing reversible"),
    (["text", ""], "no citation"),
    (["sugya", ""], "no citation, sugya"),
    (["word", ""], "no word"),
    (["word", "   "], "whitespace for a word"),
    (["anchors", ""], "no work title"),
    (["topics", ""], "no search text"),
    (["sources", ""], "no topic slug"),
    (["candidates", ""], "no search text, candidates"),
    (["calendars", "--date", "not-a-date"], "malformed date"),
    (["calendars", "--date", "2026-13-45"], "impossible date"),
    (["day", "--date", "not-a-date"], "malformed date, hebcal"),
    (["leyning", "--date", "not-a-date"], "malformed date, leyning"),
    (["zmanim", "--date", "not-a-date"], "malformed date, zmanim"),
    (["law", "sources", "nonesuch"], "unknown statute"),
    (["verify", "no/such/file.md"], "missing file"),
]

#: Markup that means a service's error page reached the user instead of a
#: sentence about what they did.
MARKUP = ("<!DOCTYPE", "<html", "<body", "<div", "<p>", "&nbsp;")


@pytest.fixture()
def offline(monkeypatch):
    """No request may leave the machine while a malformed argument is judged."""
    def refuse(*args, **kwargs):
        raise AssertionError(
            "a request left the machine to decide that the input was malformed"
        )

    monkeypatch.setattr(net, "_request", refuse)


@pytest.mark.parametrize("argv,label", CASES, ids=[label for _, label in CASES])
def test_a_malformed_argument_is_refused_cleanly(argv, label, offline):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        # No try: an exception escaping here is the failure, and pytest names
        # it better than any assertion could.
        code = main(argv)

    message = (err.getvalue() + out.getvalue()).strip()
    assert code != 0, f"{label}: malformed input exited 0 saying {message[:80]!r}"
    assert message, f"{label}: refused silently, so nothing says what was wrong"
    for fragment in MARKUP:
        assert fragment not in message, (
            f"{label}: the refusal carries {fragment!r}, so a service's error "
            f"page is standing in for an explanation"
        )


def test_a_date_refusal_names_the_form_it_wanted(offline):
    """Both calendar services, worded alike.

    `sefaria.calendars` wrapped its parse and hebcal's five did not, so the
    same mistake got `'not-a-date' is not a date in YYYY-MM-DD form` from one
    command and a bare `Invalid isoformat string` from another.
    """
    for argv in (
        ["calendars", "--date", "not-a-date"],
        ["day", "--date", "not-a-date"],
        ["leyning", "--date", "not-a-date"],
        ["zmanim", "--date", "not-a-date"],
    ):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            main(argv)
        assert "YYYY-MM-DD" in err.getvalue(), argv
        assert "not-a-date" in err.getvalue(), argv
