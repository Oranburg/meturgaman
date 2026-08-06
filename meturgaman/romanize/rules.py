"""Decide what each letter is doing, before anything is romanized.

Why this is a separate pass
---------------------------
Almost every hard question in Hebrew romanization is a classification question,
and almost none of them can be answered by looking at one letter:

  * A dagesh is either lene, which changes a consonant's sound, or forte, which
    doubles it. Same dot.
  * A sheva is either vocal, and written, or silent, and not. Same two dots.
  * A qamats is either long, giving `a`, or short, giving `o`. Same mark, and
    almost no text in the wild uses the separate Unicode codepoint for the short
    one.
  * A vav is either a consonant or half of a vowel. Same letter.

The previous version of this tool answered these inline, in the middle of
building the output string, with the answers scattered across a four-hundred-line
function. Four of them were wrong, and the wrongness was invisible because a
wrong answer still produces a plausible-looking word: `kal` instead of `kol` is
not obviously broken until you know the text.

So classification happens here, first, in the open, with every decision named and
every unresolved decision flagged. `engine.py` then does nothing but look values
up and join them.

The governing rule
------------------
**A classification this module cannot make raises a flag. It never picks a
default and stays quiet about it.** The reason is that the reader has no way to
audit a silent guess. The Library of Congress agrees, incidentally: its Hebraica
Cataloging Manual sends cataloguers to Alcalay's dictionary "primarily to
distinguish schwa naʻ from schwa nah, a matter which has significant impact on
romanization." If the standard's own manual says a dictionary is required, code
that answers from orthography alone should say when it is unsure.

Order of the passes
-------------------
1. Dagesh, which needs position and the letter before.
2. Matres lectionis, which needs the dagesh pass, since `וּ` is a vowel.
3. Qamats, which needs orthographic shape only.
4. Sheva, which needs the qamats pass, since a sheva after a short vowel is
   silent and a qamats is short exactly when the third pass says so.

Three and four are in that order to break what would otherwise be a cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from meturgaman import hebrew
from meturgaman.romanize.cluster import Cluster, Word

__all__ = [
    "Flag",
    "Analysis",
    "classify",
    "DAGESH_NONE", "DAGESH_LENE", "DAGESH_FORTE", "DAGESH_MAPIQ", "DAGESH_SHURUQ",
    "SHEVA_NONE", "SHEVA_NA", "SHEVA_NACH", "SHEVA_UNKNOWN",
    "QAMATS_NONE", "QAMATS_GADOL", "QAMATS_QATAN", "QAMATS_UNKNOWN",
    "ROLE_CONSONANT", "ROLE_MATER", "ROLE_SILENT",
    "qamats_qatan_words",
]

DAGESH_NONE = "none"
DAGESH_LENE = "lene"
DAGESH_FORTE = "forte"
DAGESH_MAPIQ = "mapiq"
DAGESH_SHURUQ = "shuruq"

SHEVA_NONE = "none"
SHEVA_NA = "na"
SHEVA_NACH = "nach"
SHEVA_UNKNOWN = "unknown"

QAMATS_NONE = "none"
QAMATS_GADOL = "gadol"
QAMATS_QATAN = "qatan"
QAMATS_UNKNOWN = "unknown"

ROLE_CONSONANT = "consonant"
ROLE_MATER = "mater"
ROLE_SILENT = "silent"


@dataclass(frozen=True)
class Flag:
    """One thing the reader should check, because this code could not settle it."""

    code: str
    message: str
    word: str = ""
    position: int = -1

    def __str__(self) -> str:
        where = f" ({self.word})" if self.word else ""
        return f"[{self.code}]{where} {self.message}"


@dataclass
class Analysis:
    """What one cluster turned out to be."""

    cluster: Cluster
    role: str = ROLE_CONSONANT
    dagesh_kind: str = DAGESH_NONE
    sheva_kind: str = SHEVA_NONE
    qamats_kind: str = QAMATS_NONE
    #: When this cluster is a mater, the full-vowel name the pair produces:
    #: one of tsere_male, hireq_male, holam_male, shuruq, patah_male, qamats_he.
    full_vowel: str = ""
    #: Set on the consonant that a following mater belongs to, so the resolver
    #: knows to take its vowel from the pair rather than from its own point.
    carries_full_vowel: str = ""
    flags: list[Flag] = field(default_factory=list)

    @property
    def doubled(self) -> bool:
        return self.dagesh_kind == DAGESH_FORTE

    @property
    def spirant(self) -> bool:
        """True when a begadkefat letter should take its soft value."""
        return self.cluster.is_begadkefat and self.dagesh_kind not in (
            DAGESH_LENE,
            DAGESH_FORTE,
        )


# ---------------------------------------------------------------------------
# The one lexical list in the project, and why it exists
# ---------------------------------------------------------------------------

_QAMATS_QATAN_WORDS: frozenset[str] | None = None


def qamats_qatan_words() -> frozenset[str]:
    """Consonantal skeletons whose qamats is short as a matter of the lexicon.

    Read from `rules/qamats-qatan.md`, which carries the reasoning and the
    grammar citation. Kept as a document for the same reason the romanization
    tables are documents: a word list buried in code is a word list nobody
    checks.

    This is emphatically not a glossary of transliterations. It answers exactly
    one classification question for a handful of words where the orthographic
    rule provably cannot, and it is checked by a test that keeps it short.
    """
    global _QAMATS_QATAN_WORDS
    if _QAMATS_QATAN_WORDS is not None:
        return _QAMATS_QATAN_WORDS

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "rules" / "qamats-qatan.md"
        if candidate.exists():
            words: set[str] = set()
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line.startswith("|") or line.startswith("|---"):
                    continue
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                if not cells or cells[0].lower() in ("word", "form"):
                    continue
                skeleton = hebrew.consonantal_skeleton(cells[0])
                if skeleton:
                    words.add(skeleton)
            _QAMATS_QATAN_WORDS = frozenset(words)
            return _QAMATS_QATAN_WORDS

    # Absent file means absent exceptions, not a crash. The rule below still
    # handles every word whose shape settles the question.
    _QAMATS_QATAN_WORDS = frozenset()
    return _QAMATS_QATAN_WORDS


# ---------------------------------------------------------------------------
# Pass 1: the dagesh
# ---------------------------------------------------------------------------

def _classify_dagesh(word: Word, analyses: list[Analysis]) -> None:
    for index, analysis in enumerate(analyses):
        cluster = analysis.cluster
        if not cluster.dagesh:
            continue

        # A dagesh in a final he is a mapiq: the he is a consonant rather than
        # the silent vowel letter it usually is at the end of a word.
        if cluster.base == hebrew.HE:
            analysis.dagesh_kind = (
                DAGESH_MAPIQ if index == len(analyses) - 1 else DAGESH_FORTE
            )
            continue

        # A vav with a dagesh and no vowel of its own is shuruq, the vowel `u`.
        # With a vowel of its own it is an ordinary consonant that happens to be
        # doubled, as in `חַוָּה`.
        if cluster.base == hebrew.VAV and not cluster.has_vowel:
            analysis.dagesh_kind = DAGESH_SHURUQ
            analysis.role = ROLE_MATER
            analysis.full_vowel = "shuruq"
            continue

        # The gutturals and resh do not take a dagesh forte at all, so a dot in
        # one of them can only be lene, and in practice only alef and he take
        # one.
        if cluster.is_guttural:
            analysis.dagesh_kind = DAGESH_LENE
            continue

        previous = analyses[index - 1] if index > 0 else None

        if cluster.is_begadkefat:
            # Lene at the start of a word, and after a consonant that closed the
            # previous syllable. Forte anywhere a vowel precedes it.
            if previous is None:
                analysis.dagesh_kind = DAGESH_LENE
            elif previous.cluster.has_full_vowel or previous.role == ROLE_MATER:
                analysis.dagesh_kind = DAGESH_FORTE
            else:
                analysis.dagesh_kind = DAGESH_LENE
        else:
            # Any other letter can only be doubled.
            analysis.dagesh_kind = DAGESH_FORTE


# ---------------------------------------------------------------------------
# Pass 2: matres lectionis
# ---------------------------------------------------------------------------

def _classify_matres(word: Word, analyses: list[Analysis]) -> None:
    """Decide which of alef, he, vav and yod are letters and which are vowels.

    The rule that does most of the work: a vowel letter takes its place only
    when the consonant before it has no vowel of its own. When the preceding
    consonant is already voweled, the letter is a consonant carrying a vowel.

    That single test is what separates `שָׁלוֹם` from `עֲוֹן`. In the first, the
    lamed has no vowel, so the vav with its holam supplies one and the word is
    `shalom`. In the second, the ayin already has a hataf patah, so the vav is a
    consonant and the word is `ʿavon` rather than `ʿaon`.
    """
    last = len(analyses) - 1

    for index, analysis in enumerate(analyses):
        cluster = analysis.cluster
        if analysis.role == ROLE_MATER:
            continue  # already settled by the shuruq case above
        previous = analyses[index - 1] if index > 0 else None

        if cluster.base == hebrew.ALEF:
            # Quiescent alef: no vowel of its own and not at the start.
            if not cluster.has_vowel and index > 0:
                analysis.role = ROLE_SILENT
            continue

        if cluster.base == hebrew.HE:
            # A final he with no vowel and no mapiq is the vowel letter that
            # spells out a preceding qamats or segol.
            if index == last and not cluster.has_vowel and not cluster.dagesh:
                analysis.role = ROLE_MATER
                if previous is not None and previous.cluster.vowel == hebrew.QAMATS:
                    analysis.full_vowel = "qamats_he"
                    previous.carries_full_vowel = "qamats_he"
            continue

        if cluster.base == hebrew.VAV:
            if cluster.has_vowel and cluster.vowel in (
                hebrew.HOLAM,
                hebrew.HOLAM_HASER_FOR_VAV,
            ):
                # Holam written on a vav. A mater only when the letter before it
                # is waiting for a vowel.
                if previous is not None and not previous.cluster.has_full_vowel:
                    analysis.role = ROLE_MATER
                    analysis.full_vowel = "holam_male"
                    previous.carries_full_vowel = "holam_male"
            elif not cluster.has_vowel and previous is not None:
                if previous.cluster.vowel == hebrew.HOLAM:
                    analysis.role = ROLE_MATER
                    analysis.full_vowel = "holam_male"
                    previous.carries_full_vowel = "holam_male"
            continue

        if cluster.base == hebrew.YOD:
            # A yod with a dagesh is always a doubled consonant, never a vowel
            # letter. Missing this is what turned `חִיּוּבָא` into `ḥiuva`.
            if cluster.dagesh or cluster.has_vowel:
                continue
            if previous is None:
                continue
            preceding = previous.cluster.vowel
            named = {
                hebrew.HIREQ: "hireq_male",
                hebrew.TSERE: "tsere_male",
                hebrew.SEGOL: "tsere_male",
                hebrew.PATAH: "patah_male",
            }.get(preceding or "")
            if named:
                analysis.role = ROLE_MATER
                analysis.full_vowel = named
                previous.carries_full_vowel = named


# ---------------------------------------------------------------------------
# Pass 3: qamats gadol against qamats qatan
# ---------------------------------------------------------------------------

def _classify_qamats(word: Word, analyses: list[Analysis]) -> None:
    """Decide, for each qamats, whether it is `a` or `o`.

    In order of authority:

    1. U+05C7, the codepoint that means qamats qatan outright. Almost no text
       uses it, but when it is there it is decisive.
    2. A meteg on the qamats. Meteg marks the syllable as accented or open, so
       the qamats is long. This is the mark that separates `שָֽׁמְרָה` shamrah
       from `חָכְמָה` ḥokhmah, which are otherwise written alike.
    3. A hataf qamats on the next letter, which only ever follows a short o.
    4. A maqaf after a one-syllable word, which strips the word of its own
       stress and shortens the vowel. This is the `כָּל־` case.
    5. The lexical list, for the handful of words the shape cannot settle.
    6. A following consonant carrying a sheva, with more word after it: a closed
       unaccented syllable, so short. **This one raises a flag**, because rule 2
       is what would have overridden it and its absence is only evidence when
       the text marks meteg at all.

    Anything else is long.
    """
    lexical = qamats_qatan_words()
    skeleton = hebrew.consonantal_skeleton(word.letters)
    last = len(analyses) - 1

    for index, analysis in enumerate(analyses):
        cluster = analysis.cluster

        if cluster.vowel == hebrew.QAMATS_QATAN:
            analysis.qamats_kind = QAMATS_QATAN
            continue
        if cluster.vowel != hebrew.QAMATS:
            continue

        if cluster.meteg:
            analysis.qamats_kind = QAMATS_GADOL
            continue

        following = analyses[index + 1] if index < last else None

        if following is not None and following.cluster.vowel == hebrew.HATAF_QAMATS:
            analysis.qamats_kind = QAMATS_QATAN
            continue

        if word.followed_by_maqaf and word.syllable_count_estimate() <= 1:
            analysis.qamats_kind = QAMATS_QATAN
            continue

        if skeleton in lexical:
            analysis.qamats_kind = QAMATS_QATAN
            continue

        # A closed unaccented syllable: this letter, then a consonant carrying a
        # sheva, then more word. Short, unless a meteg said otherwise, and the
        # meteg may simply be absent from the edition.
        if (
            following is not None
            and following.cluster.is_sheva
            and index + 1 < last
        ):
            analysis.qamats_kind = QAMATS_QATAN
            analysis.flags.append(
                Flag(
                    code="qamats-qatan-assumed",
                    message=(
                        "qamats before a silent sheva read as short (o). A meteg "
                        "on the qamats would make it long (a); this edition has "
                        "none here."
                    ),
                    word=word.raw,
                    position=index,
                )
            )
            continue

        analysis.qamats_kind = QAMATS_GADOL


# ---------------------------------------------------------------------------
# Pass 4: sheva na against sheva nach
# ---------------------------------------------------------------------------

_LONG_VOWELS = frozenset(
    {hebrew.TSERE, hebrew.HOLAM, hebrew.HOLAM_HASER_FOR_VAV}
)


def _classify_sheva(word: Word, analyses: list[Analysis]) -> None:
    """Decide, for each sheva, whether it is pronounced.

    Vocal at the start of a word, under a doubled letter, as the second of two
    in a row, and after a long vowel. Silent at the end of a word, as the first
    of two in a row, and after a short vowel.

    Where none of those apply the answer is genuinely open, and a flag is raised
    rather than a coin tossed.
    """
    last = len(analyses) - 1

    for index, analysis in enumerate(analyses):
        cluster = analysis.cluster
        if not cluster.is_sheva:
            continue

        if index == 0:
            analysis.sheva_kind = SHEVA_NA
            continue

        if index == last:
            analysis.sheva_kind = SHEVA_NACH
            continue

        previous = analyses[index - 1]
        following = analyses[index + 1]

        if previous.cluster.is_sheva:
            analysis.sheva_kind = SHEVA_NA  # second of a pair
            continue
        if following.cluster.is_sheva and index + 1 == last:
            analysis.sheva_kind = SHEVA_NACH  # first of a pair at a word's end
            continue

        if analysis.dagesh_kind == DAGESH_FORTE:
            analysis.sheva_kind = SHEVA_NA
            continue

        preceding_vowel = previous.cluster.vowel
        if previous.role == ROLE_MATER or previous.carries_full_vowel:
            analysis.sheva_kind = SHEVA_NA
            continue
        if preceding_vowel in _LONG_VOWELS:
            analysis.sheva_kind = SHEVA_NA
            continue
        if preceding_vowel == hebrew.QAMATS:
            # Long qamats leaves an open syllable and a vocal sheva; short
            # qamats closes it and silences the sheva. Pass three already
            # decided which.
            analysis.sheva_kind = (
                SHEVA_NACH if previous.qamats_kind == QAMATS_QATAN else SHEVA_NA
            )
            continue
        if preceding_vowel in (
            hebrew.PATAH,
            hebrew.SEGOL,
            hebrew.HIREQ,
            hebrew.QUBUTS,
            hebrew.QAMATS_QATAN,
        ):
            analysis.sheva_kind = SHEVA_NACH
            continue
        if previous.cluster.is_hataf:
            analysis.sheva_kind = SHEVA_NA
            continue

        analysis.sheva_kind = SHEVA_UNKNOWN
        analysis.flags.append(
            Flag(
                code="sheva-undecided",
                message=(
                    "cannot tell whether this sheva is vocal; the letter before "
                    "it carries no vowel this rule set recognizes"
                ),
                word=word.raw,
                position=index,
            )
        )


# ---------------------------------------------------------------------------
# The public entry point
# ---------------------------------------------------------------------------

def classify(word: Word) -> list[Analysis]:
    """Run every pass over one word and return an Analysis per cluster."""
    analyses = [Analysis(cluster=cluster) for cluster in word]
    if not analyses:
        return analyses

    _classify_dagesh(word, analyses)
    _classify_matres(word, analyses)
    _classify_qamats(word, analyses)
    _classify_sheva(word, analyses)
    return analyses
