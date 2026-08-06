"""Check every committed table against the document it claims to come from.

This is the test that matters most in this repository, and it exists because of
a specific failure. An earlier version put a set of spirant characters into the
SBL scheme. The characters appear nowhere in the SBL Handbook. They came from a
summary of the source rather than from the source, they looked entirely
plausible, and they were caught only when someone opened the PDF.

So: re-extract each source, and insist that every character each table claims to
have copied is actually in the document. A value that is not there has to be
listed below with a reason, which turns "I invented this" and "the source draws
this rather than encoding it" into two visibly different things.

The tests skip rather than fail when the sources are absent, since `sources/pdf/`
is gitignored and a fresh clone has none until `python -m tools.fetch_sources`
has run. On a machine where the sources are present, they run.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import unicodedata
from functools import lru_cache
from pathlib import Path

import pytest

from meturgaman.scheme import Scheme, all_schemes

REPO = Path(__file__).resolve().parent.parent
PDF_DIR = REPO / "sources" / "pdf"
HTML_DIR = REPO / "sources" / "html"

SCHEMES = sorted(all_schemes().items())

# ---------------------------------------------------------------------------
# Values that are in the document but not in its extracted text, with why
# ---------------------------------------------------------------------------
#
# Every entry here is a claim that can be checked by eye against the page. None
# of them is "the source does not have this"; each is "the source has this in a
# form extraction cannot see."

_NOT_EXTRACTABLE: dict[str, dict[str, str]] = {
    "encyclopaedia-judaica-scientific": {
        "ḏ": "drawn rule under the d, not a combining character; visible at 900 dpi",
        "ṯ": "drawn rule under the t, likewise",
        "ə": (
            "the text stream holds U+04D9 CYRILLIC SMALL LETTER SCHWA for this "
            "glyph, almost certainly a font substitution; the scheme file uses "
            "the Latin U+0259 and says so"
        ),
    },
}

# Every entry above was checked by re-extracting the document. An earlier
# version of this list carried seventeen more, and every one of them named a
# character that is present in the extracted text. Because the test consults
# this list before it consults the document, each of those entries silently
# switched off a real check, which is worse than having no test: it was a
# written record that a character had been verified when nothing had verified
# it. Two of them were covering actual errors, `ǧ` where the source prints `ğ`
# and a schwa whose codepoint differs.
#
# So the rule for this list is now: an entry is a claim that the character is on
# the page and that extraction cannot see it, and a test below checks that the
# claim is not merely unfalsifiable.

@lru_cache(maxsize=8)
def _extracted(filename: str) -> str:
    """The text of a source document, NFC-normalized.

    Normalization is not optional. `pdftotext` emits precomposed diacritics
    decomposed, so a search for `ḥ` U+1E25 finds nothing in a document plainly
    full of it unless both sides are composed the same way.
    """
    if filename.endswith(".html"):
        path = HTML_DIR / filename
        if not path.exists():
            return ""
        raw = path.read_text(encoding="utf-8", errors="replace")
        return unicodedata.normalize("NFC", re.sub(r"<[^>]+>", " ", raw))

    path = PDF_DIR / filename
    if not path.exists() or not shutil.which("pdftotext"):
        return ""
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return unicodedata.normalize("NFC", result.stdout)


def _requires(scheme: Scheme) -> str:
    text = _extracted(scheme.source)
    if not text:
        pytest.skip(
            f"{scheme.source} is not present or cannot be extracted; run "
            f"`python -m tools.fetch_sources` first"
        )
    return text


@pytest.mark.parametrize("name,scheme", SCHEMES, ids=[n for n, _ in SCHEMES])
def test_every_value_appears_in_its_source(name: str, scheme: Scheme):
    """No table may contain a character its document does not."""
    text = _requires(scheme)
    allowed = _NOT_EXTRACTABLE.get(name, {})

    unexplained: list[str] = []
    for value in sorted(scheme.romanizations()):
        if not value or value in allowed:
            continue
        # A multi-character value is checked character by character: a digraph
        # such as `kh` may be printed across a line break.
        for character in value:
            if character.isascii() and not character.isalpha():
                continue
            if character in allowed:
                continue
            if character in text:
                continue
            if character.isascii():
                # Plain Latin letters are everywhere in an English document and
                # prove nothing either way.
                continue
            unexplained.append(f"{character!r} (U+{ord(character):04X}) from {value!r}")

    assert not unexplained, (
        f"{name} claims characters its source does not contain, and they are not "
        f"listed in _NOT_EXTRACTABLE with a reason:\n  "
        + "\n  ".join(dict.fromkeys(unexplained))
    )


@pytest.mark.parametrize("name,scheme", SCHEMES, ids=[n for n, _ in SCHEMES])
def test_the_exceptions_list_is_not_a_dumping_ground(name: str, scheme: Scheme):
    """Every listed exception must still be a value the scheme actually uses.

    Without this, a character deleted from a table leaves its excuse behind, and
    the next person to add that character finds it pre-approved.
    """
    allowed = _NOT_EXTRACTABLE.get(name, {})
    used = set()
    for value in scheme.romanizations():
        used.update(value)
        used.add(value)
    stale = [value for value in allowed if value not in used]
    assert not stale, (
        f"{name} lists exceptions for characters it no longer uses: {stale}. "
        f"Delete them, or the excuse outlives the evidence."
    )


def test_the_invented_spirant_set_is_not_in_sbl():
    """A direct guard against the specific fabrication this project had.

    `ḇ ḡ ḏ ḵ p̄ ṯ` were added to the SBL schemes once. The SBL Handbook prints no
    spirant characters at all; §5.1.1.1 lists the six letters bare and note 4
    says to show spirantization by underlining rather than by a character. Those
    characters are correct in Encyclopaedia Judaica's scientific column and wrong
    in SBL, and the difference is which document is open.
    """
    invented = {"ḇ", "ḡ", "ḏ", "ḵ", "p̄", "ṯ"}
    for name in ("sbl-general", "sbl-academic"):
        scheme = all_schemes()[name]
        found = invented & scheme.romanizations()
        assert not found, (
            f"{name} contains {found}, which appears nowhere in the SBL Handbook"
        )


def test_encyclopaedia_judaica_has_five_spirants_and_no_pe():
    """The count that separates the real set from the invented one.

    EJ's scientific column prints spirants for bet, gimel, dalet, kaf and tav.
    It prints none for pe. Five, not six. The invented set had six.
    """
    scheme = all_schemes()["encyclopaedia-judaica-scientific"]
    values = scheme.romanizations()
    assert "ḡ" in values, "EJ scientific should carry the gimel spirant"
    assert "ḏ" in values, "EJ scientific should carry the dalet spirant"
    assert "ṯ" in values, "EJ scientific should carry the tav spirant"
    assert "p̄" not in values, "EJ prints no pe spirant"


def test_yivo_tav_is_the_ashkenazi_s():
    """The row that makes YIVO the Ashkenazi table.

    `תּ` with a dagesh is t and bare `ת` is s. That is what gives Shabbos rather
    than Shabbat, and it is the single most load-bearing row for the use Seth
    has for this scheme.
    """
    from meturgaman import hebrew

    yivo = all_schemes()["yivo"]
    assert yivo.consonant(hebrew.TAV) == "s"
    assert yivo.consonant(hebrew.TAV, dagesh=True) == "t"


def test_ala_lc_keeps_three_distinct_s_sounds():
    """Samekh, sin and the Yiddish tav must not collapse.

    ALA-LC is built to be reversible, and it needs `s`, `ś` and `s̀` to stay
    apart to manage it. Reading the Yiddish tav's combining grave as an
    extraction artifact would have collapsed the third into the first.
    """
    from meturgaman import hebrew

    yiddish = all_schemes()["ala-lc-yiddish"]
    samekh = yiddish.consonant(hebrew.SAMEKH)
    sin = yiddish.sin
    tav = yiddish.consonant(hebrew.TAV)
    assert len({samekh, sin, tav}) == 3, (
        f"expected three distinct s values, got {samekh!r}, {sin!r}, {tav!r}"
    )
    assert tav == "s̀", f"Yiddish tav should be s plus U+0300, got {tav!r}"


@pytest.mark.parametrize("name,scheme", SCHEMES, ids=[n for n, _ in SCHEMES])
def test_every_exception_is_actually_unextractable(name: str, scheme: Scheme):
    """An excuse must name a character the extraction genuinely cannot see.

    Without this, the exceptions list becomes a way to make the fidelity test
    pass. Seventeen of its entries once named characters that were sitting in
    the extracted text, and each one switched off a check that would otherwise
    have run.
    """
    allowed = _NOT_EXTRACTABLE.get(name, {})
    if not allowed:
        return
    text = _requires(scheme)
    false_excuses = [
        character for character in allowed if character in text
    ]
    assert not false_excuses, (
        f"{name} excuses {false_excuses} as unextractable, but they are in the "
        f"extracted text. Either the excuse is wrong or the value is."
    )
