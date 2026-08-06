"""Structural guards on the scheme files.

These are the tests that would have caught the two worst faults this project has
had. Neither was subtle once looked for; both survived because nothing looked.

  * A scheme quietly stopped defining three letters, and the engine emitted the
    Hebrew characters straight into its Latin output: `רַב` came out as `raב`.
    `test_every_scheme_defines_every_letter` and `test_no_scheme_leaks_hebrew`
    are the two that make that impossible.

  * A spirant set that appears in no source was added to a scheme, deleted from
    it, and went on living in a second file that had copied it. Deriving every
    signature from the tables, and checking the tables against the PDFs, is what
    stops an invention outliving its deletion.
"""

from __future__ import annotations

import pytest

from meturgaman import hebrew
from meturgaman.romanize.engine import romanize
from meturgaman.scheme import Scheme, SchemeError, all_schemes, default_scheme, load_scheme

SCHEMES = sorted(all_schemes().items())
HEBREW_SCHEMES = [(name, s) for name, s in SCHEMES if s.script == "hebrew"]

#: Vowel points a scheme may legitimately omit without declaring a gap.
#: Holam-haser-for-vav is a rare spelling variant, and sheva is carried by the
#: `shva_na` rule rather than by a table row in some schemes.
_OPTIONAL_VOWELS = {hebrew.HOLAM_HASER_FOR_VAV}

_GAP_NAMES = {
    "hataf_qamats": hebrew.HATAF_QAMATS,
    "qamats_qatan": hebrew.QAMATS_QATAN,
    "sheva": hebrew.SHEVA,
    "holam": hebrew.HOLAM,
}


def test_at_least_the_eight_schemes_load():
    assert len(SCHEMES) >= 8, [name for name, _ in SCHEMES]


def test_exactly_one_default():
    defaults = [name for name, scheme in SCHEMES if scheme.is_default]
    assert defaults == ["sbl-general"]
    assert default_scheme().name == "sbl-general"


@pytest.mark.parametrize("name,scheme", SCHEMES, ids=[n for n, _ in SCHEMES])
def test_every_scheme_defines_every_letter(name: str, scheme: Scheme):
    """All twenty-two letters and all five final forms, in every scheme.

    Shin is exempt only when the scheme distinguishes it by dot, which is what
    every Hebrew scheme does and what YIVO deliberately does not.
    """
    missing = [
        hebrew.LETTER_NAMES[letter]
        for letter in hebrew.LETTERS
        if not scheme.defines(letter)
        and not (letter == hebrew.SHIN and (scheme.shin or scheme.sin))
    ]
    assert not missing, f"{name} defines no value for: {missing}"

    missing_finals = [
        hebrew.LETTER_NAMES[letter]
        for letter in hebrew.FINAL_FORMS
        if not scheme.defines(letter)
    ]
    assert not missing_finals, f"{name} defines no value for: {missing_finals}"


@pytest.mark.parametrize("name,scheme", HEBREW_SCHEMES, ids=[n for n, _ in HEBREW_SCHEMES])
def test_every_hebrew_scheme_covers_the_vowels(name: str, scheme: Scheme):
    """Every vowel point is either given a value or declared a gap in the source."""
    declared = {
        _GAP_NAMES[gap] for gap in scheme.rule("source_gaps") if gap in _GAP_NAMES
    }
    missing = [
        hebrew.VOWEL_NAMES[point]
        for point in hebrew.VOWEL_POINTS
        if point not in scheme.vowels
        and point not in declared
        and point not in _OPTIONAL_VOWELS
    ]
    assert not missing, (
        f"{name} has no value for {missing} and does not declare them in "
        f"`source_gaps`. Either the row was missed or the source really does "
        f"not print it, and the file should say which."
    )


@pytest.mark.parametrize("name,scheme", SCHEMES, ids=[n for n, _ in SCHEMES])
def test_no_scheme_emits_a_hebrew_character(name: str, scheme: Scheme):
    """A romanization value containing a Hebrew letter is a table entry gone wrong."""
    for value in scheme.romanizations():
        assert not hebrew.has_hebrew(value), (
            f"{name} romanizes something as {value!r}, which contains Hebrew"
        )


@pytest.mark.parametrize("name,scheme", HEBREW_SCHEMES, ids=[n for n, _ in HEBREW_SCHEMES])
def test_no_scheme_leaks_hebrew_into_its_output(name: str, scheme: Scheme):
    """The guard against `רַב` becoming `raב`.

    Runs a phrase using every letter of the alphabet through each scheme and
    insists nothing Hebrew survives into the Latin.
    """
    every_letter = " ".join(
        letter + hebrew.PATAH for letter in hebrew.LETTERS
    ) + " " + " ".join(hebrew.FINAL_FORMS)
    result = romanize(every_letter, scheme)
    assert not hebrew.has_hebrew(result.text), (
        f"{name} let Hebrew through into {result.text!r}"
    )


@pytest.mark.parametrize("name,scheme", SCHEMES, ids=[n for n, _ in SCHEMES])
def test_every_scheme_cites_a_source(name: str, scheme: Scheme):
    assert scheme.citation.strip(), f"{name} names no source"
    assert scheme.source.strip(), f"{name} names no source file"
    assert len(scheme.citation) > 20, (
        f"{name}'s citation is too short to identify a document: "
        f"{scheme.citation!r}"
    )


@pytest.mark.parametrize("name,scheme", SCHEMES, ids=[n for n, _ in SCHEMES])
def test_every_scheme_records_how_it_was_built(name: str, scheme: Scheme):
    """The provenance section is what says the table was read rather than recalled.

    The old assertion looked for the literal string "two-channel" in the first
     400 characters, which tested a phrasing convention rather than substance.
    What actually matters: the file names its source document, and it carries
    a section recording how the values were extracted and checked.
    """
    assert scheme.citation.strip(), f"{name} carries no citation"
    assert scheme.source.strip(), f"{name} names no source file"
    # The provenance record is the comment the generator leaves at the top:
    # it must say the table came from reading the document, and it must point
    # at the manifest where the document's URL and hash live.
    head = scheme.text[:600]
    assert head.lstrip().startswith("<!--"), (
        f"{name} has no provenance comment saying how its table was extracted"
    )
    assert "sources/manifest.md" in head, (
        f"{name}'s provenance comment does not point at the manifest"
    )


@pytest.mark.parametrize("name,scheme", SCHEMES, ids=[n for n, _ in SCHEMES])
def test_round_trip_through_the_file(name: str, scheme: Scheme, tmp_path):
    """Load, write back out, load again, and get the same tables.

    Guards the loader against drifting from the format the files are written in.
    """
    copy = tmp_path / f"{name}.md"
    copy.write_text(scheme.text, encoding="utf-8")
    reloaded = load_scheme(copy)
    assert reloaded.plain == scheme.plain
    assert reloaded.dagesh == scheme.dagesh
    assert reloaded.vowels == scheme.vowels
    assert reloaded.sequences == scheme.sequences
    assert reloaded.rafe == scheme.rafe
    assert reloaded.geresh == scheme.geresh
    assert reloaded.shin == scheme.shin
    assert reloaded.sin == scheme.sin
    assert reloaded.rules == scheme.rules


def test_loader_refuses_an_unknown_rule_key(tmp_path):
    """A misspelled rule is an error, not something silently ignored."""
    path = tmp_path / "broken.md"
    path.write_text(
        "---\nname: broken\ncitation: \"a citation long enough to pass\"\n"
        "source: nowhere.pdf\ndubles: true\n---\n\n"
        "## Consonants\n\n| Letter | Name | Romanization |\n|---|---|---|\n| א | alef | ’ |\n",
        encoding="utf-8",
    )
    with pytest.raises(SchemeError, match="dubles"):
        load_scheme(path)


def test_loader_refuses_a_name_that_does_not_match_its_file(tmp_path):
    path = tmp_path / "actual-name.md"
    path.write_text(
        "---\nname: different-name\ncitation: \"a citation long enough\"\n"
        "source: nowhere.pdf\n---\n\n"
        "## Consonants\n\n| Letter | Name | Romanization |\n|---|---|---|\n| א | alef | ’ |\n",
        encoding="utf-8",
    )
    with pytest.raises(SchemeError, match="name"):
        load_scheme(path)


def test_alef_and_ayin_are_mirrored_where_a_scheme_writes_both():
    """The two marks must not be the same character.

    Alef and ayin are opposite-facing marks in every standard that writes them.
    A scheme that gives both the same character has lost a distinction, and this
    is a question that was got wrong once already.
    """
    for name, scheme in HEBREW_SCHEMES:
        alef = scheme.plain.get(hebrew.ALEF, "")
        ayin = scheme.plain.get(hebrew.AYIN, "")
        if alef and ayin:
            assert alef != ayin, (
                f"{name} writes alef and ayin identically as {alef!r}"
            )


def test_the_three_mirrored_pairs_are_kept_apart():
    """Each scheme uses one pair, and the pairs are genuinely different characters.

    Three different mirrored pairs are in play across these standards, and they
    look nearly alike at reading size:

        ʾ U+02BE / ʿ U+02BF   half rings, SBL academic
        ʼ U+02BC / ʻ U+02BB   modifier apostrophe and turned comma, ALA-LC
        ’ U+2019 / ‘ U+2018   typographic quotes, SBL general and BGN
    """
    pairs = {
        "sbl-academic": ("ʾ", "ʿ"),
        "ala-lc": ("ʼ", "ʻ"),
        "sbl-general": ("’", "‘"),
        "bgn-pcgn": ("’", "‘"),
    }
    for name, (alef, ayin) in pairs.items():
        scheme = all_schemes()[name]
        assert scheme.plain[hebrew.ALEF] == alef, (
            f"{name} alef is {scheme.plain[hebrew.ALEF]!r} (U+"
            f"{ord(scheme.plain[hebrew.ALEF]):04X}), expected U+{ord(alef):04X}"
        )
        assert scheme.plain[hebrew.AYIN] == ayin, (
            f"{name} ayin is {scheme.plain[hebrew.AYIN]!r} (U+"
            f"{ord(scheme.plain[hebrew.AYIN]):04X}), expected U+{ord(ayin):04X}"
        )
