"""Load a romanization scheme from its markdown file in `schemes/`.

The point of this module
------------------------
The tables live in markdown, one file per scheme, and this reads them. No
romanization table is written in Python anywhere in this package. That is the
single most important structural fact about the project, and it is worth saying
why.

A table written in Python is a table nobody proofreads. It gets edited to make a
test pass, it drifts from the published standard it claims to implement, and the
drift is invisible because reading it requires reading code. The first version of
this project shipped a spirant set that appears nowhere in the SBL Handbook,
survived a rewrite because a second file had quietly copied it, and was caught
only when someone checked the tables against the PDF by hand.

So: the tables are documents. They carry their citation, they record every place
they depart from what the source prints and why, a test re-extracts each source
PDF and diffs it against them, and this module is the only thing that reads them.

The file format
---------------
An HTML comment recording how the file was built, then YAML front matter for
values that are single facts, then markdown for everything that is a grid.

    ---
    name: sbl-general
    citation: "SBL Handbook of Style, 2nd ed., §5.1.2"
    source: sbl-handbook.pdf
    doubles: true
    never_double: [ts, sh]
    ---

    ## Consonants

    | Letter | Name | Romanization |
    |---|---|---|
    | בּ | bet | b |
    | ב | vet | v |
    | כ ך | khaf | kh |

A letter cell may hold several forms separated by spaces, which is how a base
letter and its final shape share one row. Whether a form carries a dagesh is read
off the characters rather than declared, so `בּ` and `ב` on separate rows give the
scheme its dagesh and plain values without anything having to say so.

`schemes/README.md` is the reference for anyone adding a ninth scheme.

Failure
-------
Every failure here raises `SchemeError` naming the file and the line. Nothing
falls back to a default, because a scheme that silently half-loads produces
romanization that looks fine and is wrong, which is the failure this project
exists to prevent.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from meturgaman import hebrew
from meturgaman.hebrew import DAGESH, DOTTED_CIRCLE, SHIN_DOT, SIN_DOT, normalize

__all__ = [
    "Scheme",
    "SchemeError",
    "load_scheme",
    "all_schemes",
    "scheme_named",
    "default_scheme",
    "scheme_names",
    "schemes_directory",
]


class SchemeError(Exception):
    """A scheme file could not be read, or says something this code cannot honour."""


# ---------------------------------------------------------------------------
# The rule keys, their types, and their defaults
# ---------------------------------------------------------------------------
#
# Every key a scheme may set is listed here. An unlisted key is an error rather
# than something ignored, because the common way to break a scheme is to
# misspell a rule name and never find out it had no effect.
#
# Each entry is (type, default). A scheme that does not state a key gets the
# default, and `Scheme.explicit` records which keys were actually stated so the
# CLI can show the difference and a test can insist the committed schemes state
# everything that applies to them.

_RULE_KEYS: dict[str, tuple[type, Any]] = {
    # Which scheme is used when the caller names none.
    "default": (bool, False),
    # `hebrew` or `yiddish`. Yiddish is written with the same letters but they
    # carry vowels directly, so the vowel table means something different and
    # the engine takes a different path.
    "script": (str, "hebrew"),
    # Dagesh forte written by doubling the consonant.
    "doubles": (bool, True),
    # Digraphs that are never doubled even under dagesh forte, because doubling
    # them would produce a sequence no reader could parse back.
    "never_double": (list, []),
    # Whether the dagesh forte the definite article puts in the next consonant
    # is written. SBL general note 2 says it is not, giving `ha-melekh` rather
    # than `ha-mmelekh`.
    "article_doubles": (bool, True),
    # The inseparable prefixes: `ha-melekh` when true.
    "hyphenate_prefixes": (bool, False),
    # BGN/PCGN instead joins the prefix and capitalizes what follows.
    "join_and_capitalize_prefixes": (bool, False),
    # Whether a word-initial alef is written at all.
    "always_mark_alef": (bool, False),
    # How a vocal sheva is written. Empty string means it is not written.
    "shva_na": (str, "e"),
    # The full vowels: a vowel point plus its vowel letter. An empty value means
    # the scheme gives the combination no special form, so the vowel and the
    # letter are romanized separately in the ordinary way.
    "tsere_male": (str, "e"),
    "hireq_male": (str, "i"),
    "holam_male": (str, "o"),
    "shuruq": (str, "u"),
    # Patah followed by yod. Only ALA-LC prints a distinct value, `ai`.
    "patah_male": (str, ""),
    # Segol followed by yod. Distinct from tsere plus yod, because SBL general
    # deviates on the tsere sequence only.
    "segol_male": (str, "e"),
    # Word-final qamats followed by he: `ah` in SBL general, `â` in academic.
    "qamats_he": (str, ""),
    # Word-final qamats, yod, vav: the third masculine singular suffix, which
    # both SBL styles print as its own row rather than letter by letter.
    "suffix_3ms": (str, ""),
    # What the maqaf becomes. SBL §5.1.1.4 note 9 makes it a hyphen; a scheme
    # that prefers a space says so here rather than in code.
    "maqaf": (str, "-"),
    # Whether a word-final consonantal he is written.
    "mark_final_he": (bool, False),
    # Vowel points the source document does not print at all, named so that a
    # missing row is a declared fact rather than an oversight. The structural
    # test accepts a gap only when it is listed here, and the engine raises a
    # flag when it meets one rather than substituting a value from elsewhere.
    "source_gaps": (list, []),
}

_REQUIRED_KEYS = ("name", "citation", "source")


# ---------------------------------------------------------------------------
# The scheme itself
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Scheme:
    """One romanization standard, as its markdown file states it."""

    name: str
    citation: str
    source: str
    path: Path
    text: str

    #: Letter form to romanization, for forms carrying no dagesh.
    plain: dict[str, str] = field(default_factory=dict)
    #: Letter form to romanization, for forms carrying a dagesh.
    dagesh: dict[str, str] = field(default_factory=dict)
    #: Vowel point to romanization.
    vowels: dict[str, str] = field(default_factory=dict)
    #: Letter sequence to romanization, matched longest first. Yiddish needs
    #: this twice over: it carries most of its vowels in letters rather than in
    #: points (`אָ`, `וי`, `ײַ`), and it writes several consonants as clusters
    #: (`וו` for v, `דזש` for the j in judge).
    sequences: dict[str, str] = field(default_factory=dict)

    #: Letter plus geresh, for the sounds Hebrew borrows and has no letter for:
    #: `ג׳` for the j in George, `ז׳` for the s in measure, `צ׳` for ch.
    geresh: dict[str, str] = field(default_factory=dict)
    #: Letter plus rafe. Yiddish marks its spirants with an explicit rafe (`בֿ`
    #: veys, `פֿ` fey) where Hebrew marks them by the absence of a dagesh, so
    #: these cannot share a table with the plain forms.
    rafe: dict[str, str] = field(default_factory=dict)

    shin: str = ""
    sin: str = ""

    rules: dict[str, Any] = field(default_factory=dict)
    #: The rule keys the file stated, as opposed to those it inherited.
    explicit: frozenset[str] = frozenset()

    # Rule accessors, so callers never index a dict of unknown shape.

    def rule(self, key: str) -> Any:
        if key not in _RULE_KEYS:
            raise SchemeError(f"{key!r} is not a rule any scheme defines")
        return self.rules.get(key, _RULE_KEYS[key][1])

    @property
    def is_default(self) -> bool:
        return bool(self.rule("default"))

    @property
    def script(self) -> str:
        return str(self.rule("script"))

    @property
    def doubles(self) -> bool:
        return bool(self.rule("doubles"))

    @property
    def never_double(self) -> tuple[str, ...]:
        return tuple(self.rule("never_double"))

    @property
    def hyphenate_prefixes(self) -> bool:
        return bool(self.rule("hyphenate_prefixes"))

    @property
    def join_and_capitalize_prefixes(self) -> bool:
        return bool(self.rule("join_and_capitalize_prefixes"))

    @property
    def always_mark_alef(self) -> bool:
        return bool(self.rule("always_mark_alef"))

    @property
    def shva_na(self) -> str:
        return str(self.rule("shva_na"))

    @property
    def maqaf(self) -> str:
        return str(self.rule("maqaf"))

    # Lookups.

    def consonant(self, letter: str, *, dagesh: bool = False) -> str:
        """The romanization of one letter, with or without a dagesh.

        The fallback from the dagesh table to the plain table is deliberate and
        is not a guess. A scheme that prints no separate spirant row for a letter
        is saying that the letter sounds the same either way. SBL academic prints
        no spirant rows at all, so every letter falls back; SBL general prints
        three, so three do not.

        Raises rather than returning the letter unchanged. Returning it unchanged
        is how Hebrew characters end up inside Latin output, which happened once
        and produced `raב` for `רַב`.
        """
        letter = normalize(letter)
        if dagesh and letter in self.dagesh:
            return self.dagesh[letter]
        if letter in self.plain:
            return self.plain[letter]
        if dagesh and letter in self.plain:
            return self.plain[letter]
        name = hebrew.LETTER_NAMES.get(letter, repr(letter))
        raise SchemeError(
            f"scheme {self.name!r} ({self.path.name}) defines no romanization "
            f"for {name}"
        )

    def defines(self, letter: str) -> bool:
        """Whether this scheme has any value for a letter, dagesh or not."""
        letter = normalize(letter)
        return letter in self.plain or letter in self.dagesh

    def vowel(self, point: str) -> str:
        """The romanization of one vowel point."""
        point = normalize(point)
        if point not in self.vowels:
            name = hebrew.VOWEL_NAMES.get(point, repr(point))
            raise SchemeError(
                f"scheme {self.name!r} ({self.path.name}) defines no romanization "
                f"for {name}"
            )
        return self.vowels[point]

    def romanizations(self) -> frozenset[str]:
        """Every Latin string this scheme can emit, for detection and for tests."""
        values: set[str] = set()
        values.update(self.plain.values())
        values.update(self.dagesh.values())
        values.update(self.vowels.values())
        values.update(self.sequences.values())
        values.update(self.geresh.values())
        values.update(self.rafe.values())
        values.update({self.shin, self.sin})
        for key in ("shva_na", "tsere_male", "hireq_male", "holam_male", "shuruq"):
            values.add(str(self.rule(key)))
        return frozenset(value for value in values if value)


# ---------------------------------------------------------------------------
# Front matter
# ---------------------------------------------------------------------------
#
# A deliberately small YAML subset: scalars, booleans, and flat inline lists.
# Bringing in PyYAML for this would add the project's only dependency in order
# to support nesting that no scheme file uses.

def _parse_scalar(raw: str, *, path: Path, line_number: int) -> Any:
    raw = raw.strip()
    if not raw:
        return ""
    if raw[0] in "\"'":
        quote = raw[0]
        if len(raw) < 2 or raw[-1] != quote:
            raise SchemeError(f"{path}:{line_number}: unbalanced quote in {raw!r}")
        return raw[1:-1]
    if raw in ("true", "false"):
        return raw == "true"
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        items = []
        for item in inner.split(","):
            item = item.strip()
            if item and item[0] in "\"'" and item[-1] == item[0]:
                item = item[1:-1]
            items.append(item)
        return items
    if raw.startswith("[") or raw.endswith("]"):
        raise SchemeError(f"{path}:{line_number}: unbalanced bracket in {raw!r}")
    return raw


def _parse_front_matter(lines: list[str], path: Path) -> tuple[dict[str, Any], int]:
    """Read the `---` delimited block. Returns the values and the line after it."""
    start = None
    in_comment = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if in_comment:
            # The provenance header spans several lines; skip to its close.
            if "-->" in stripped:
                in_comment = False
            continue
        if not stripped:
            continue
        if stripped.startswith("<!--"):
            if "-->" not in stripped:
                in_comment = True
            continue
        if stripped == "---":
            start = index
            break
        # Anything else before the front matter means the file is not a scheme.
        raise SchemeError(
            f"{path}:{index + 1}: expected the front matter to open with '---', "
            f"found {stripped[:40]!r}"
        )
    if start is None:
        raise SchemeError(f"{path}: no front matter found")

    values: dict[str, Any] = {}
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            return values, index + 1
        if not line.strip():
            continue
        if ":" not in line:
            raise SchemeError(
                f"{path}:{index + 1}: front matter line has no colon: {line.strip()[:60]!r}"
            )
        key, _, raw = line.partition(":")
        key = key.strip()
        if key in values:
            raise SchemeError(f"{path}:{index + 1}: {key!r} is set twice")
        if key not in _RULE_KEYS and key not in _REQUIRED_KEYS:
            known = ", ".join(sorted(set(_RULE_KEYS) | set(_REQUIRED_KEYS)))
            raise SchemeError(
                f"{path}:{index + 1}: {key!r} is not a key any scheme defines.\n"
                f"  known keys: {known}"
            )
        value = _parse_scalar(raw, path=path, line_number=index + 1)
        if key in _RULE_KEYS:
            expected, _ = _RULE_KEYS[key]
            if expected is bool and not isinstance(value, bool):
                raise SchemeError(
                    f"{path}:{index + 1}: {key!r} takes true or false, found {value!r}"
                )
            if expected is list and not isinstance(value, list):
                raise SchemeError(
                    f"{path}:{index + 1}: {key!r} takes a list like [a, b], found {value!r}"
                )
            if expected is str and not isinstance(value, str):
                raise SchemeError(
                    f"{path}:{index + 1}: {key!r} takes a string, found {value!r}"
                )
        values[key] = value

    raise SchemeError(f"{path}: the front matter was opened but never closed")


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def _table_after(lines: list[str], heading: str, path: Path) -> list[tuple[list[str], int]]:
    """Every row of the first markdown table under a given `##` heading.

    Returns the cells of each body row with its 1-based line number, so an error
    can point at the row rather than at the file.
    """
    target = heading.strip().lower()
    index = None
    for position, line in enumerate(lines):
        if line.strip().lower().lstrip("#").strip() == target and line.strip().startswith("##"):
            index = position + 1
            break
    if index is None:
        return []

    rows: list[tuple[list[str], int]] = []
    seen_table = False
    for position in range(index, len(lines)):
        line = lines[position].strip()
        if line.startswith("##"):
            break
        if not line.startswith("|"):
            if seen_table and rows:
                break
            continue
        seen_table = True
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if all(set(cell) <= {"-", ":"} and cell for cell in cells):
            continue  # the |---|---| separator
        if cells and cells[0].lower() in ("letter", "sign", "form"):
            continue  # the header row
        rows.append((cells, position + 1))
    return rows


def _read_consonants(
    rows: list[tuple[list[str], int]], path: Path
) -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str], str, str]:
    """Split the consonant table into plain, dagesh, shin and sin.

    A form's dagesh and dot status is read off its characters. Nothing declares
    it, so a row cannot claim one thing and print another.
    """
    plain: dict[str, str] = {}
    dagesh: dict[str, str] = {}
    geresh: dict[str, str] = {}
    rafe: dict[str, str] = {}
    shin = ""
    sin = ""

    for cells, line_number in rows:
        if len(cells) < 3:
            raise SchemeError(
                f"{path}:{line_number}: a consonant row needs Letter, Name and "
                f"Romanization; found {len(cells)} cells"
            )
        forms_cell, _name, romanization = cells[0], cells[1], cells[2]
        romanization = normalize(romanization)
        # Backticks let a file show an empty value visibly rather than by
        # leaving whitespace that looks like an oversight.
        if romanization in ("``", "`` ", "—"):
            romanization = ""
        romanization = romanization.strip("`")

        forms = [normalize(form) for form in forms_cell.split() if form.strip()]
        if not forms:
            raise SchemeError(f"{path}:{line_number}: the Letter cell is empty")

        for form in forms:
            letters = [character for character in form if hebrew.is_letter(character)]
            if len(letters) != 1:
                raise SchemeError(
                    f"{path}:{line_number}: {form!r} is not one Hebrew letter "
                    f"with its points"
                )
            letter = letters[0]
            if hebrew.RAFE in form:
                if letter in rafe and rafe[letter] != romanization:
                    raise SchemeError(
                        f"{path}:{line_number}: {letter} with rafe is given two "
                        f"different values, {rafe[letter]!r} and {romanization!r}"
                    )
                rafe[letter] = romanization
            elif hebrew.GERESH in form:
                # A borrowed sound, written as a letter with a geresh after it.
                # Keyed on the bare letter so the caller does not have to
                # normalize the geresh character it happened to encounter.
                if letter in geresh and geresh[letter] != romanization:
                    raise SchemeError(
                        f"{path}:{line_number}: {letter} with geresh is given two "
                        f"different values, {geresh[letter]!r} and {romanization!r}"
                    )
                geresh[letter] = romanization
            elif SHIN_DOT in form:
                shin = romanization
            elif SIN_DOT in form:
                sin = romanization
            elif DAGESH in form:
                if letter in dagesh and dagesh[letter] != romanization:
                    raise SchemeError(
                        f"{path}:{line_number}: {letter} with dagesh is given two "
                        f"different values, {dagesh[letter]!r} and {romanization!r}"
                    )
                dagesh[letter] = romanization
            else:
                if letter in plain and plain[letter] != romanization:
                    raise SchemeError(
                        f"{path}:{line_number}: {letter} is given two different "
                        f"values, {plain[letter]!r} and {romanization!r}"
                    )
                plain[letter] = romanization

    return plain, dagesh, geresh, rafe, shin, sin


def _read_sequences(
    rows: list[tuple[list[str], int]], path: Path
) -> dict[str, str]:
    """The vowel-letters table, for Yiddish.

    Hebrew writes its vowels as points under consonants, so a Hebrew scheme maps
    one combining mark to one value. Yiddish writes most of its vowels as letters,
    sometimes with a point on top, so a Yiddish scheme maps whole sequences: `ו`
    and `או` both give `u`, `ײ` gives `ey`, `ײַ` with its pasekh gives `ay`.

    A Sign cell may list several sequences separated by commas when the source
    prints them as alternatives for one value.
    """
    letters: dict[str, str] = {}
    for cells, line_number in rows:
        if len(cells) < 3:
            raise SchemeError(
                f"{path}:{line_number}: a vowel-letter row needs Sign, Name and "
                f"Romanization"
            )
        sign_cell, _name, romanization = cells[0], cells[1], cells[2]
        romanization = normalize(romanization).strip("`")
        for sequence in sign_cell.split(","):
            sequence = normalize(sequence).replace(DOTTED_CIRCLE, "").strip().strip("`")
            if not sequence:
                continue
            if not any(hebrew.is_letter(character) for character in sequence):
                raise SchemeError(
                    f"{path}:{line_number}: {sequence!r} holds no Hebrew letter"
                )
            if sequence in letters and letters[sequence] != romanization:
                raise SchemeError(
                    f"{path}:{line_number}: {sequence!r} is given two different "
                    f"values, {letters[sequence]!r} and {romanization!r}"
                )
            letters[sequence] = romanization
    return letters


def _read_vowels(rows: list[tuple[list[str], int]], path: Path) -> dict[str, str]:
    """The vowel table, keyed by the bare combining mark."""
    vowels: dict[str, str] = {}
    for cells, line_number in rows:
        if len(cells) < 3:
            raise SchemeError(
                f"{path}:{line_number}: a vowel row needs Sign, Name and Romanization"
            )
        sign_cell, _name, romanization = cells[0], cells[1], cells[2]
        romanization = normalize(romanization).strip("`")
        # The Sign column draws each point on a dotted circle so it is visible.
        sign = normalize(sign_cell).replace(DOTTED_CIRCLE, "").strip()
        points = [character for character in sign if hebrew.is_vowel(character)]
        if len(points) != 1:
            raise SchemeError(
                f"{path}:{line_number}: {sign_cell!r} is not a single vowel point"
            )
        point = points[0]
        if point in vowels and vowels[point] != romanization:
            raise SchemeError(
                f"{path}:{line_number}: {hebrew.VOWEL_NAMES.get(point, point)} is "
                f"given two different values"
            )
        vowels[point] = romanization
    return vowels


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_scheme(path: Path | str) -> Scheme:
    """Read one scheme file. Raises SchemeError with a line number on any fault."""
    path = Path(path)
    if not path.exists():
        raise SchemeError(f"no scheme file at {path}")

    text = normalize(path.read_text(encoding="utf-8"))
    lines = text.splitlines()

    values, _body_start = _parse_front_matter(lines, path)
    for key in _REQUIRED_KEYS:
        if key not in values:
            raise SchemeError(f"{path}: front matter is missing {key!r}")

    consonant_rows = _table_after(lines, "Consonants", path)
    if not consonant_rows:
        raise SchemeError(f"{path}: no '## Consonants' table")
    plain, dagesh, geresh, rafe, shin, sin = _read_consonants(consonant_rows, path)

    vowel_rows = _table_after(lines, "Vowels", path)
    vowels = _read_vowels(vowel_rows, path) if vowel_rows else {}

    sequences: dict[str, str] = {}
    for heading in ("Vowel letters", "Letter combinations"):
        rows = _table_after(lines, heading, path)
        if rows:
            for key, value in _read_sequences(rows, path).items():
                if key in sequences and sequences[key] != value:
                    raise SchemeError(
                        f"{path}: {key!r} is given two different values across "
                        f"the sequence tables"
                    )
                sequences[key] = value

    rules = {key: value for key, value in values.items() if key in _RULE_KEYS}
    explicit = frozenset(rules)

    scheme = Scheme(
        name=str(values["name"]),
        citation=str(values["citation"]),
        source=str(values["source"]),
        path=path,
        text=text,
        plain=plain,
        dagesh=dagesh,
        vowels=vowels,
        sequences=sequences,
        geresh=geresh,
        rafe=rafe,
        shin=shin,
        sin=sin,
        rules=rules,
        explicit=explicit,
    )

    if scheme.name != path.stem:
        raise SchemeError(
            f"{path}: front matter says name {scheme.name!r} but the file is "
            f"called {path.stem!r}. They have to agree so a scheme can be found "
            f"by either one."
        )
    return scheme


def schemes_directory() -> Path:
    """Where the scheme files live.

    Checked in order: the METURGAMAN_SCHEMES environment variable, then a
    `schemes/` directory found by walking up from this file. Nothing is guessed;
    if neither works, the error names every path that was tried.
    """
    tried: list[Path] = []

    override = os.environ.get("METURGAMAN_SCHEMES")
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_dir():
            return candidate
        tried.append(candidate)

    here = Path(__file__).resolve()

    # Installed: the tables ship as package data under `meturgaman/data/`.
    packaged = here.parent / "data" / "schemes"
    tried.append(packaged)
    if packaged.is_dir() and any(packaged.glob("*.md")):
        return packaged

    # From a checkout: `schemes/` at the top of the repository, which is where
    # anyone debugging a table will look for it. The walk stops at the first
    # directory holding a `.git`, so it cannot wander into a world-writable
    # parent and load a table planted there.
    for parent in here.parents:
        candidate = parent / "schemes"
        tried.append(candidate)
        if candidate.is_dir() and any(candidate.glob("*.md")):
            return candidate
        if (parent / ".git").exists():
            break

    listing = "\n  ".join(str(path) for path in tried)
    raise SchemeError(
        "could not find the schemes directory. Tried:\n  "
        + listing
        + "\nSet METURGAMAN_SCHEMES to the directory holding the scheme files, "
        "or run from a checkout of the repository."
    )


_CACHE: dict[str, Scheme] | None = None


def all_schemes(*, reload: bool = False) -> dict[str, Scheme]:
    """Every scheme in `schemes/`, keyed by name.

    `schemes/README.md` documents the format rather than defining a scheme, so
    any file whose front matter is absent is skipped only when it is the README;
    every other unreadable file is an error.
    """
    global _CACHE
    if _CACHE is not None and not reload:
        return _CACHE

    directory = schemes_directory()
    loaded: dict[str, Scheme] = {}
    for path in sorted(directory.glob("*.md")):
        if path.stem.lower() == "readme":
            continue
        scheme = load_scheme(path)
        if scheme.name in loaded:
            raise SchemeError(
                f"two files both call themselves {scheme.name!r}: "
                f"{loaded[scheme.name].path} and {path}"
            )
        loaded[scheme.name] = scheme

    if not loaded:
        raise SchemeError(f"{directory} holds no scheme files")

    defaults = [scheme.name for scheme in loaded.values() if scheme.is_default]
    if len(defaults) > 1:
        raise SchemeError(f"more than one scheme claims to be the default: {defaults}")
    if not defaults:
        raise SchemeError(
            "no scheme sets `default: true`. One has to, so that a caller who "
            "names no scheme gets a stated choice rather than an arbitrary one."
        )

    _CACHE = loaded
    return loaded


def scheme_names() -> tuple[str, ...]:
    """The names of every available scheme, in alphabetical order."""
    return tuple(sorted(all_schemes()))


def scheme_named(name: str) -> Scheme:
    """One scheme by name. Raises with the full list when the name is unknown."""
    schemes = all_schemes()
    if name in schemes:
        return schemes[name]
    available = ", ".join(sorted(schemes))
    raise SchemeError(f"no scheme called {name!r}. Available: {available}")


def default_scheme() -> Scheme:
    """The scheme used when the caller names none."""
    for scheme in all_schemes().values():
        if scheme.is_default:
            return scheme
    raise SchemeError("no scheme sets `default: true`")  # pragma: no cover
