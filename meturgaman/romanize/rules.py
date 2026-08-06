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
    "DAGESH_EUPHONIC",
    "SHEVA_NONE", "SHEVA_NA", "SHEVA_NACH", "SHEVA_UNKNOWN",
    "QAMATS_NONE", "QAMATS_GADOL", "QAMATS_QATAN", "QAMATS_UNKNOWN",
    "ROLE_CONSONANT", "ROLE_MATER", "ROLE_SILENT",
    "qamats_qatan_words", "sacred_names", "established_forms",
    "load_rule_table", "rules_directory",
]

DAGESH_NONE = "none"
DAGESH_LENE = "lene"
DAGESH_FORTE = "forte"
DAGESH_MAPIQ = "mapiq"
DAGESH_SHURUQ = "shuruq"
DAGESH_EUPHONIC = "euphonic"

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
    #: A furtive patah: written before its consonant rather than after it.
    furtive: bool = False
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

_RULE_TABLES: dict[str, dict[str, str]] = {}


def rules_directory() -> Path | None:
    """Where the scheme-independent rule files live, or None if not found."""
    here = Path(__file__).resolve()
    packaged = here.parent.parent / "data" / "rules"
    if packaged.is_dir() and any(packaged.glob("*.md")):
        return packaged
    for parent in here.parents:
        candidate = parent / "rules"
        if candidate.is_dir() and any(candidate.glob("*.md")):
            return candidate
        if (parent / ".git").exists():
            break
    return None


def load_rule_table(filename: str) -> dict[str, str]:
    """Read a two-column markdown table from `rules/`, keyed by Hebrew skeleton.

    The first column is Hebrew and the second is what to write. Both are read
    from the first markdown table in the file; anything after a third column is
    a note for a person and is ignored.

    These files are documents for the same reason the scheme files are. A word
    list buried in code is a word list nobody checks, and each of these
    overrides the tables in some way, so each one needs to be able to say why.
    """
    if filename in _RULE_TABLES:
        return _RULE_TABLES[filename]

    directory = rules_directory()
    table: dict[str, str] = {}
    if directory is None or not (directory / filename).exists():
        _RULE_TABLES[filename] = table
        return table

    for line in (directory / filename).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|-: "):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if cells[0].lower() in ("hebrew", "word", "form", "sign", "letter"):
            continue
        skeleton = hebrew.consonantal_skeleton(cells[0])
        written = cells[1].strip()
        if skeleton and written:
            table[skeleton] = written

    _RULE_TABLES[filename] = table
    return table


def sacred_names() -> dict[str, str]:
    """Names written as a fixed form rather than romanized. See rules/sacred-names.md."""
    return load_rule_table("sacred-names.md")


def established_forms() -> dict[str, str]:
    """Words with a settled English spelling. See rules/established-forms.md."""
    return load_rule_table("established-forms.md")


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
        elif previous is None:
            # A dagesh in the first letter of a word, in a letter that has no
            # lene form, is euphonic: it joins the word to the one before it
            # rather than doubling anything. SBL note 5 is explicit, giving
            # `מַה־שְּׁמ` as *mah-šĕmô* rather than *mah-ššĕmô*. Doubling it
            # produced `llemor` for `לֵּאמֹר`.
            analysis.dagesh_kind = DAGESH_EUPHONIC
        else:
            # Any other letter can only be doubled.
            analysis.dagesh_kind = DAGESH_FORTE


# ---------------------------------------------------------------------------
# Pass 2: matres lectionis
# ---------------------------------------------------------------------------

def _assign_carrier(previous: Analysis, name: str) -> None:
    """Record that a consonant's vowel is spelled out by the letter after it.

    Refuses to hang the vowel on a letter that will not be written. A quiescent
    alef is dropped from the output, so making it the carrier loses the vowel
    with it: `לָאוֹר` came out *lar*, an entire syllable gone and no flag raised.
    When the previous letter is silent, the vowel letter keeps the vowel and
    writes it itself.
    """
    if previous.role == ROLE_SILENT:
        return
    previous.carries_full_vowel = name


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
                    _assign_carrier(previous, "qamats_he")
            continue

        if cluster.base == hebrew.VAV:
            if cluster.has_vowel and cluster.vowel in (
                hebrew.HOLAM,
                hebrew.HOLAM_HASER_FOR_VAV,
            ):
                # Holam written on a vav. A mater only when the letter before it
                # carries no vowel of any kind and is therefore waiting for one.
                #
                # The test is `has_vowel`, not `has_full_vowel`. A consonant with
                # a sheva already has a vowel, reduced but present, and closes
                # its syllable, so the vav after it is a consonant. Asking for a
                # full vowel made `מִצְוֹת` into *mitsot* instead of *mitsvot*.
                if previous is not None and not previous.cluster.has_vowel:
                    analysis.role = ROLE_MATER
                    analysis.full_vowel = "holam_male"
                    _assign_carrier(previous, "holam_male")
            elif not cluster.has_vowel and previous is not None:
                if previous.cluster.vowel == hebrew.HOLAM:
                    analysis.role = ROLE_MATER
                    analysis.full_vowel = "holam_male"
                    _assign_carrier(previous, "holam_male")
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
                # A segol followed by a yod is its own sequence. It used to be
                # mapped to `tsere_male`, which meant SBL general's documented
                # `ei` deviation, stated for tsere yod only, leaked onto it and
                # gave `yadeikha` for `יָדֶיךָ` instead of `yadekha`.
                hebrew.SEGOL: "segol_male",
                hebrew.PATAH: "patah_male",
            }.get(preceding or "")
            if named:
                analysis.role = ROLE_MATER
                analysis.full_vowel = named
                _assign_carrier(previous, named)


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

        # A qamats before a consonant carrying a sheva. This shape is where a
        # short qamats lives, and it is tempting to read it as one. Do not.
        #
        # An earlier version did, on the theory that a missing meteg was
        # evidence of a short vowel. Tested against 1,934 words of Genesis,
        # Psalms, Deuteronomy, Exodus and Leviticus, it fired fifteen times and
        # was wrong fifteen times: `הָיְתָה` came out *hoytah* for *haytah*,
        # `לָיְלָה` *loylah* for *laylah*, `לְבָבְךָ` *levovkha* for *levavkha*.
        #
        # The reasoning was wrong at its root. Masoretic editions print meteg on
        # some long qamats and not others, so its absence is not evidence of
        # anything. And the damage compounded, because the sheva pass reads
        # `qamats_kind` and silences the sheva, so one bad call corrupted the
        # vowel and the syllable together.
        #
        # Long is the commoner reading by a wide margin, so long is the answer,
        # and the flag says the shape is one a reader should check.
        if (
            following is not None
            and following.cluster.is_sheva
            and index + 1 < last
        ):
            analysis.qamats_kind = QAMATS_GADOL
            analysis.flags.append(
                Flag(
                    code="qamats-may-be-short",
                    message=(
                        "read long (a), which is the commoner reading of this "
                        "shape. A few words take a short qamats (o) here and are "
                        "listed in rules/qamats-qatan.md; check the word if it "
                        "matters"
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

        # A yod or vav carrying a sheva after a vowel is the second half of a
        # diphthong, not a syllable of its own: `הָיְתָה` is *haytah* and
        # `לָיְלָה` is *laylah*. Treating the sheva as vocal gave *hayetah* and
        # *layelah*, inserting a syllable the word does not have.
        if (
            cluster.base in (hebrew.YOD, hebrew.VAV)
            and preceding_vowel is not None
            and preceding_vowel != hebrew.SHEVA
        ):
            analysis.sheva_kind = SHEVA_NACH
            continue

        # The second person singular suffix `ךָ` closes the syllable before it,
        # so the sheva on that syllable's last consonant is silent: `לְבָבְךָ` is
        # *levavkha*, not *levavekha*.
        if (
            following.cluster.letter == hebrew.FINAL_KAF
            and following.cluster.vowel == hebrew.QAMATS
            and index + 1 == last
        ):
            analysis.sheva_kind = SHEVA_NACH
            continue

        if previous.role == ROLE_MATER or previous.carries_full_vowel:
            analysis.sheva_kind = SHEVA_NA
            continue
        if preceding_vowel in _LONG_VOWELS:
            analysis.sheva_kind = SHEVA_NA
            continue
        if preceding_vowel == hebrew.QAMATS:
            # Long qamats generally leaves an open syllable and a vocal sheva;
            # short qamats closes it and silences the sheva. Pass three decided
            # which.
            #
            # "Generally" is doing real work in that sentence. `שָׁרְצוּ` is
            # *sharetsu* with a vocal sheva and `לְבָבְךָ` is *levavkha* with a
            # silent one, and the two are written alike. Which it is depends on
            # the word's pattern, which is the case the Library of Congress
            # sends its cataloguers to a dictionary for. Vocal is the commoner
            # reading and is what is written; the flag says to check.
            if previous.qamats_kind == QAMATS_QATAN:
                analysis.sheva_kind = SHEVA_NACH
            else:
                analysis.sheva_kind = SHEVA_NA
                analysis.flags.append(
                    Flag(
                        code="sheva-after-qamats",
                        message=(
                            "read as vocal, which is the commoner reading after a "
                            "long qamats. Some words take a silent sheva here and "
                            "the spelling does not say which; check if it matters"
                        ),
                        word=word.raw,
                        position=index,
                    )
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

def _classify_furtive_patah(word: Word, analyses: list[Analysis]) -> None:
    """Find the patah that is pronounced before its own consonant.

    A patah under a word-final ḥet, ayin, or he with a mapiq is spoken ahead of
    that letter rather than after it: `כֹּחַ` is *koaḥ* and `רוּחַ` is *ruaḥ*.

    Getting this wrong is not a cosmetic slip. Writing the vowel after the
    consonant gives *koḥa*, which is a different word, and in a scheme that marks
    ayin it produces *koʿaḥ*, inventing a consonant that is not in the text.

    The condition is narrow on purpose: only at the end of a word, only under
    those three letters, and only when a vowel already precedes, since a furtive
    patah is by definition an extra glide into a syllable that already has a
    nucleus.
    """
    if len(analyses) < 2:
        return
    last = analyses[-1]
    cluster = last.cluster

    if cluster.vowel != hebrew.PATAH:
        return
    if cluster.base not in (hebrew.HET, hebrew.AYIN, hebrew.HE):
        return
    if cluster.base == hebrew.HE and not cluster.dagesh:
        # A bare final he is a vowel letter, not a consonant, so there is no
        # furtive patah. Only a mapiq he takes one.
        return

    for earlier in analyses[:-1]:
        # A vowel letter counts as a nucleus just as a point does: `רוּחַ` has its
        # vowel in the shuruq, and the patah under the ḥet is furtive all the
        # same.
        if (
            earlier.cluster.has_full_vowel
            or earlier.carries_full_vowel
            or earlier.role == ROLE_MATER
        ):
            last.furtive = True
            return


def classify(word: Word) -> list[Analysis]:
    """Run every pass over one word and return an Analysis per cluster."""
    analyses = [Analysis(cluster=cluster) for cluster in word]
    if not analyses:
        return analyses

    _classify_dagesh(word, analyses)
    _classify_matres(word, analyses)
    _classify_qamats(word, analyses)
    _classify_sheva(word, analyses)
    _classify_furtive_patah(word, analyses)
    return analyses
