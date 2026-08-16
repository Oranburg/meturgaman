#!/usr/bin/env python3
"""Classify the sandbox before promising anything. One call, no arguments.

This exists because of a specific failure. With no network egress, meturgaman's
reference resolution fails before its fetch does, so a perfectly good citation
comes back as:

    refused: 'Genesis 1:1' did not resolve. Try `meturgaman candidates ...`
      could not reach sefaria: [Errno 61] Connection refused

The headline blames the citation and the cause is on the second line. A model
that reads only the headline will tell a user their citation is not a
recognized reference, which is worse than saying nothing. Running this first
means the environment is a known fact rather than something inferred from an
error message that hides it.

Three hosts are tested, not one, because the CLI does not talk to a single
service and partial egress is a real state: Sefaria serves texts, links and
topics; hebcal.com serves the calendar family (`day`, `leyning`, `zmanim`,
`yahrzeit`); he.wikisource.org serves the consolidated Hebrew of Israeli
statutes. Any one can be reachable while another is not.

Every request sets a cache-defeating header and none of them goes through
meturgaman's cache, because a warm cache answering after the network is gone is
exactly how a probe comes to lie.

    python3 scripts/probe.py
"""

import pathlib
import sys
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

TIMEOUT = 8

# Each host is probed with the cheapest request that proves the service answers,
# rather than merely that DNS resolved and a socket opened.
HOSTS = [
    (
        "sefaria.org",
        "https://www.sefaria.org/api/ref/Genesis_1:1",
        "texts, refs, links, topics, calendars, daf",
    ),
    (
        "hebcal.com",
        "https://www.hebcal.com/converter?cfg=json&gy=2026&gm=8&gd=10&g2h=1",
        "day, leyning, zmanim, yahrzeit",
    ),
    (
        "he.wikisource.org",
        "https://he.wikisource.org/w/api.php?action=query&meta=siteinfo&format=json",
        "law hebrew, law amendments",
    ),
]


def reach(url: str) -> tuple[bool, str, float]:
    """Return whether the host answered, a short note, and elapsed seconds."""
    started = time.monotonic()
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "meturgaman-skill-probe",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read(400)
            elapsed = time.monotonic() - started
            ok = response.status == 200 and bool(body)
            return ok, f"HTTP {response.status}", elapsed
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}", time.monotonic() - started
    except Exception as exc:
        return False, type(exc).__name__, time.monotonic() - started


def main() -> int:
    print("meturgaman sandbox probe")
    print()

    version = sys.version_info
    print(f"  python              {version.major}.{version.minor}.{version.micro}")
    if version < (3, 11):
        print()
        print("  VERDICT  UNUSABLE. meturgaman needs Python 3.11 or newer.")
        print("           Do not run the bundled CLI. Use the web-fetch path in")
        print("           references/sefaria-fallback.md for everything.")
        return 1

    try:
        import meturgaman  # noqa: F401

        print("  bundled package     imports (no install needed)")
    except Exception as exc:
        print(f"  bundled package     FAILED: {type(exc).__name__}: {exc}")
        print()
        print("  VERDICT  UNUSABLE. Use the web-fetch path for everything.")
        return 1

    schemes = HERE / "meturgaman" / "data" / "schemes"
    found = len(list(schemes.glob("*.md"))) if schemes.is_dir() else 0
    print(f"  scheme tables       {found} (8 expected, plus a README)")

    print()
    results = {}
    for name, url, serves in HOSTS:
        ok, note, elapsed = reach(url)
        results[name] = ok
        mark = "reachable" if ok else "BLOCKED  "
        print(f"  {name:20}{mark}  {note:18} {elapsed:5.2f}s   {serves}")

    print()
    if all(results.values()):
        print("  VERDICT  FULL. Run everything through scripts/mtg.py.")
        print("           Fetched passages arrive with edition, source and licence.")
    elif not any(results.values()):
        print("  VERDICT  OFFLINE. No egress from this sandbox.")
        print("           Still works here: romanize, detect, reverse, register,")
        print("           schemes, law tiers, law statutes, law sources.")
        print("           For anything that fetches a text, do NOT run the CLI.")
        print("           Use Claude's own web fetch with the URL templates in")
        print("           references/sefaria-fallback.md, and carry the edition")
        print("           and licence across by hand.")
        print("           Any 'did not resolve' refusal in this state is the")
        print("           missing network, never a verdict on the citation.")
    else:
        print("  VERDICT  PARTIAL. Use the CLI only for the reachable hosts above.")
        print("           For a blocked host, use the web-fetch path in")
        print("           references/sefaria-fallback.md. Say in the answer which")
        print("           path produced which passage.")

    print()
    print("  Whichever path is used, say so once in the answer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
