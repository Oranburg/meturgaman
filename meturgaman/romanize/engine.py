"""Turn classified Hebrew into Latin letters under a named scheme.

This module holds no romanization table and makes no linguistic decision. Every
value comes from a scheme file in `schemes/`; every decision was already made by
`rules.py`. What is left is lookup and joining, and keeping it that thin is the
point: when output is wrong, the fault is in a table or in a classification, and
those are separate files with separate tests.

The passes here, in order: resolve each cluster to a string, apply doubling,
handle prefixes, join words, and turn the maqaf into whatever the scheme says a
maqaf becomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from meturgaman import hebrew
from meturgaman.romanize import rules
from meturgaman.romanize.cluster import Run, Word, segment
from meturgaman.romanize.rules import (
    DAGESH_FORTE,
    DAGESH_LENE,
    DAGESH_MAPIQ,
    QAMATS_QATAN,
    ROLE_MATER,
    ROLE_SILENT,
    SHEVA_NA,
    Analysis,
    Flag,
)
from meturgaman.scheme import Scheme, SchemeError, default_scheme, scheme_named

__all__ = ["Romanization", "romanize", "romanize_word"]

#: Front-matter keys that name a full vowel, so the resolver can look one up by
#: the name `rules.py` assigned it.
_FULL_VOWEL_KEYS = (
    "tsere_male",
    "hireq_male",
    "holam_male",
    "shuruq",
    "patah_male",
    "segol_male",
    "qamats_he",
)

#: The letters that can begin a word as a prefix rather than as part of it.
_PREFIX_LETTERS = (
    hebrew.BET,
    hebrew.KAF,
    hebrew.LAMED,
    hebrew.VAV,
    hebrew.MEM,
    hebrew.SHIN,
    hebrew.HE,
)


@dataclass
class Romanization:
    """The result of romanizing a stretch of text."""

    text: str
    scheme: str
    flags: list[Flag] = field(default_factory=list)

    def __str__(self) -> str:
        return self.text

    @property
    def is_clean(self) -> bool:
        """True when nothing needed a reader's judgement."""
        return not self.flags

    def report(self) -> str:
        """The text, and under it every flag, for a person to read."""
        if not self.flags:
            return self.text
        lines = [self.text, ""]
        lines.extend(f"  {flag}" for flag in self.flags)
        return "\n".join(lines)


def _resolve_scheme(scheme: Scheme | str | None) -> Scheme:
    if scheme is None:
        return default_scheme()
    if isinstance(scheme, str):
        return scheme_named(scheme)
    return scheme


# ---------------------------------------------------------------------------
# Consonants
# ---------------------------------------------------------------------------

def _consonant_value(
    analysis: Analysis, scheme: Scheme, word: Word, flags: list[Flag]
) -> str:
    """The Latin form of one consonant, before doubling."""
    cluster = analysis.cluster
    letter = cluster.letter

    if cluster.geresh and cluster.base in scheme.geresh:
        return scheme.geresh[cluster.base]

    if cluster.rafe and cluster.base in scheme.rafe:
        return scheme.rafe[cluster.base]

    if cluster.base == hebrew.SHIN:
        if cluster.shin_dot:
            return scheme.shin or scheme.consonant(letter)
        if cluster.sin_dot:
            return scheme.sin or scheme.consonant(letter)
        # A bare shin with no dot. YIVO writes shin this way on purpose and its
        # table says so; every Hebrew scheme dots both, and an undotted shin in
        # Hebrew is genuinely ambiguous.
        if scheme.shin:
            flags.append(
                Flag(
                    code="shin-undotted",
                    message=(
                        "shin carries no dot, so shin and sin cannot be told "
                        f"apart; read as shin ({scheme.shin})"
                    ),
                    word=word.raw,
                    position=cluster.index,
                )
            )
            return scheme.shin
        return scheme.consonant(letter)

    hard = analysis.dagesh_kind in (DAGESH_LENE, DAGESH_FORTE, DAGESH_MAPIQ)
    return scheme.consonant(letter, dagesh=hard)


def _double(value: str, scheme: Scheme) -> str:
    """Write a dagesh forte, if this scheme writes one and this digraph allows it."""
    if not value or not scheme.doubles:
        return value
    if value in scheme.never_double:
        return value
    # Doubling a digraph means doubling its last letter would be unreadable and
    # doubling the whole thing produces `shsh`. Schemes that hit this name the
    # digraph in `never_double`; anything else doubles whole.
    return value + value


# ---------------------------------------------------------------------------
# Vowels
# ---------------------------------------------------------------------------

def _vowel_value(
    analysis: Analysis, scheme: Scheme, word: Word, flags: list[Flag]
) -> str:
    """The Latin form of whatever vowel this cluster carries."""
    cluster = analysis.cluster

    # A full vowel is written once, on whichever of the pair the caller asks
    # about: `carries_full_vowel` on the consonant, `full_vowel` on the vowel
    # letter that spells it out.
    key = analysis.carries_full_vowel or (
        analysis.full_vowel if analysis.role == ROLE_MATER else ""
    )
    if key in _FULL_VOWEL_KEYS:
        value = str(scheme.rule(key))
        if value:
            return value
        # An empty full-vowel rule means the scheme gives the pair no special
        # form, so the vowel and the letter are written separately as usual.

    if cluster.vowel is None:
        return ""

    if cluster.is_sheva:
        return scheme.shva_na if analysis.sheva_kind == SHEVA_NA else ""

    point = cluster.vowel
    if point == hebrew.QAMATS and analysis.qamats_kind == QAMATS_QATAN:
        point = hebrew.QAMATS_QATAN
    if point == hebrew.HOLAM_HASER_FOR_VAV:
        # U+05BA is a spelling variant of holam that no published table prints a
        # row for, and Sefaria's Masoretic edition uses it routinely. Reading it
        # as the holam it is beats raising on the Thirteen Attributes.
        point = hebrew.HOLAM

    gaps = {
        "hataf_qamats": hebrew.HATAF_QAMATS,
        "qamats_qatan": hebrew.QAMATS_QATAN,
        "sheva": hebrew.SHEVA,
    }
    declared = {gaps[name] for name in scheme.rule("source_gaps") if name in gaps}

    if point not in scheme.vowels:
        if point == hebrew.QAMATS_QATAN and hebrew.QAMATS in scheme.vowels:
            # The scheme prints one qamats row and no short one, which means it
            # does not draw the distinction. Its qamats value stands, and the
            # reader is told the distinction was lost rather than left to
            # assume it was kept.
            if point in declared:
                flags.append(
                    Flag(
                        code="distinction-not-in-scheme",
                        message=(
                            f"this qamats is short, but {scheme.name} prints no "
                            f"separate short-qamats row, so it is written the "
                            f"same as a long one"
                        ),
                        word=word.raw,
                        position=cluster.index,
                    )
                )
            return scheme.vowels[hebrew.QAMATS]
        if point in declared:
            flags.append(
                Flag(
                    code="source-gap",
                    message=(
                        f"{scheme.name} prints no row for "
                        f"{hebrew.VOWEL_NAMES.get(point, point)}, so this vowel is "
                        f"left unwritten rather than borrowed from another scheme"
                    ),
                    word=word.raw,
                    position=cluster.index,
                )
            )
            return ""
        if point == hebrew.QAMATS_QATAN and hebrew.QAMATS in scheme.vowels:
            # No separate short-qamats row and no declared gap: the scheme does
            # not distinguish them, so its qamats value stands.
            return scheme.vowels[hebrew.QAMATS]
        raise SchemeError(
            f"scheme {scheme.name!r} defines no romanization for "
            f"{hebrew.VOWEL_NAMES.get(point, point)}"
        )
    return scheme.vowels[point]


# ---------------------------------------------------------------------------
# Whole words
# ---------------------------------------------------------------------------

def _prefix_length(word: Word, analyses: list[Analysis]) -> int:
    """How many clusters at the front of this word are a prefix, if any.

    Deliberately conservative, and narrower than it first appears it could be.
    Hebrew's inseparable prefixes are single letters that are also ordinary root
    letters, so telling them apart in general needs a lexicon. Exactly two
    shapes can be identified from orthography alone:

      * **The definite article.** `הַ` followed by a consonant carrying a dagesh
        forte, or by a guttural, which refuses the dagesh and lengthens the
        article's vowel instead. `הַמֶּלֶךְ` and `הָאָרֶץ` both match.
      * **The conjunction.** A word-initial vav with a sheva or a shuruq.
        Hebrew roots almost never begin with vav, so this one is safe.

    Everything else is left joined, and the reason is worth recording because
    each looser rule was tried and each broke a real word:

      * A prefix letter with any vowel plus a following dagesh forte splits
        `שַׁבָּת` into `sha-bbat` and `כַּלָּה` into `ka-llah`.
      * A prefix letter carrying a sheva splits `שְׁמַע` into `she-ma` and
        `בְּכוֹר` into `be-khor`.
      * An earlier version was looser still and produced `ka-ḥush` for `כָּחוּשׁ`
        and `la-v` for `לָאו`.

    A word that is not split is still romanized correctly; it just runs
    together. A word split wrongly is wrong. Given the choice, this leaves them
    joined.
    """
    if len(analyses) < 2:
        return 0
    first = analyses[0].cluster
    following = analyses[1]

    if first.base == hebrew.HE and first.vowel in (
        hebrew.PATAH,
        hebrew.QAMATS,
        hebrew.SEGOL,
    ):
        if following.dagesh_kind == DAGESH_FORTE:
            return 1
        # A guttural refuses the dagesh and lengthens the article's vowel
        # instead, so `הָאָרֶץ` is the article with no dot to show it. Resh is
        # excluded even though it behaves like a guttural elsewhere, and a word
        # of only two letters is excluded outright: with both in, `הַר` split
        # into `ha-r`, leaving a bare consonant with no vowel, and `הָרִים`
        # became `ha-rim`.
        if (
            len(analyses) >= 3
            and following.cluster.base in (hebrew.ALEF, hebrew.HE, hebrew.HET, hebrew.AYIN)
        ):
            return 1

    if first.base == hebrew.VAV and (
        first.is_sheva or analyses[0].dagesh_kind == "shuruq"
    ):
        return 1

    return 0


def romanize_word(
    word: Word,
    scheme: Scheme,
    flags: list[Flag] | None = None,
    *,
    literal: bool = False,
    established: bool = False,
) -> str:
    """Romanize one clustered Hebrew word.

    `literal` turns off the sacred-name substitution, for work that needs the
    letters as letters. `established` substitutes the conventional English
    spelling where one exists rather than only naming it.
    """
    collected = flags if flags is not None else []

    if not len(word):
        return ""

    skeleton = hebrew.consonantal_skeleton(word.letters)

    # A sacred name is written as its fixed form rather than romanized. This is
    # the only place the tool overrides its own tables by default, and
    # `rules/sacred-names.md` says why.
    if not literal:
        fixed = rules.sacred_names().get(skeleton)
        if fixed:
            return fixed

    # A word English already knows how to spell. Named, not substituted, unless
    # asked. See `rules/established-forms.md`.
    conventional = rules.established_forms().get(skeleton)
    if conventional:
        if established:
            return conventional
        collected.append(
            Flag(
                code="established-form",
                message=f"English usually spells this {conventional}",
                word=word.raw,
            )
        )

    if scheme.script == "yiddish":
        # Pointed Hebrew put through a Yiddish table produces a consonant
        # skeleton and nothing else, because a Yiddish table has no rows for
        # Hebrew vowel points. That is worth saying rather than returning
        # `khkhmh` for `חָכְמָה` as though it were an answer.
        if any(
            cluster.has_vowel and cluster.base not in (hebrew.ALEF, hebrew.YOD)
            for cluster in word
        ):
            collected.append(
                Flag(
                    code="script-mismatch",
                    message=(
                        f"this word is pointed Hebrew and {scheme.name} is a "
                        f"Yiddish table, which has no rows for Hebrew vowel "
                        f"points; the vowels are lost. Use a Hebrew scheme, or "
                        f"see the scheme file for why no Ashkenazi Hebrew table "
                        f"exists"
                    ),
                    word=word.raw,
                )
            )
        return _romanize_yiddish(word, scheme, collected)

    if any(cluster.letter in hebrew.YIDDISH_LIGATURES for cluster in word):
        collected.append(
            Flag(
                code="script-mismatch",
                message=(
                    f"this word uses Yiddish ligatures and {scheme.name} is a "
                    f"Hebrew table; try --scheme yivo"
                ),
                word=word.raw,
            )
        )

    if not word.is_pointed:
        collected.append(
            Flag(
                code="unpointed",
                message=(
                    "no vowels are written, so the vowels cannot be recovered by "
                    "rule; consonants only"
                ),
                word=word.raw,
            )
        )

    analyses = rules.classify(word)
    for analysis in analyses:
        collected.extend(analysis.flags)

    # Where the word divides, if it does. Settled before anything is written,
    # because the definite article changes how the consonant after it is
    # treated and the resolver has to know that as it goes.
    prefix_clusters = _prefix_length(word, analyses)
    is_article = prefix_clusters == 1 and analyses[0].cluster.base == hebrew.HE

    # The third masculine singular suffix, which both SBL styles print as a row
    # of its own rather than letter by letter.
    suffix = str(scheme.rule("suffix_3ms"))
    trailing = ""
    body = analyses
    if suffix and len(analyses) >= 3:
        tail = analyses[-3:]
        if (
            tail[0].cluster.vowel == hebrew.QAMATS
            and tail[1].cluster.base == hebrew.YOD
            and not tail[1].cluster.has_vowel
            and tail[2].cluster.base == hebrew.VAV
            and not tail[2].cluster.has_vowel
        ):
            trailing = suffix
            body = analyses[:-2]  # keep the consonant; its qamats joins the suffix

    def render(analysis: Analysis, index: int, *, with_vowel: bool = True) -> str:
        cluster = analysis.cluster

        if analysis.role == ROLE_MATER:
            previous = body[index - 1] if index > 0 else None
            # A vowel letter whose scheme states no value for the pair is
            # written as the letter it is, and the vowel point it spells out is
            # written on the consonant in the ordinary way.
            #
            # Two cases in practice. ALA-LC and BGN print no row for a final he
            # after a qamats, so `תּוֹרָה` keeps its h and comes out `torah`. And
            # SBL prints no row for a patah followed by a yod, so `חַי` keeps its
            # yod and comes out `ḥay`. Without this the letter vanished and the
            # word came out `tora` and `ḥa`.
            key = analysis.full_vowel
            if not key or (key in _FULL_VOWEL_KEYS and not str(scheme.rule(key))):
                # Either the scheme states no value for the pair, or there is no
                # pair: an unpointed `תורה` has a final he spelling out nothing.
                # Writing the letter beats dropping it, which gave `tvr`.
                return scheme.consonant(cluster.letter)
            # A vowel letter writes the pair's vowel only when the consonant it
            # serves did not already write it.
            if previous is not None and previous.carries_full_vowel:
                return ""
            return _vowel_value(analysis, scheme, word, collected)

        if analysis.role == ROLE_SILENT:
            if cluster.base == hebrew.ALEF and scheme.always_mark_alef:
                return scheme.consonant(cluster.letter)
            return ""

        consonant = _consonant_value(analysis, scheme, word, collected)

        # Alef is written when medial and voweled, and not at the start of a
        # word. BGN/PCGN note 1 states this explicitly and the other schemes
        # follow the same practice; `always_mark_alef` overrides it.
        if (
            cluster.base == hebrew.ALEF
            and not scheme.always_mark_alef
            and index == 0
            and word.is_pointed
        ):
            # Word-initial alef is not written. Suppressed only in pointed text:
            # in unpointed text every letter is all the reader gets, and `אב`
            # came out as `v`.
            consonant = ""

        if analysis.dagesh_kind == DAGESH_FORTE:
            # The article's dagesh is not written in every scheme. SBL general
            # note 2 gives `ha-melekh` rather than `ha-mmelekh`.
            suppressed = (
                is_article
                and index == prefix_clusters
                and not bool(scheme.rule("article_doubles"))
            )
            if not suppressed:
                consonant = _double(consonant, scheme)

        if trailing and index == len(body) - 1:
            # The qamats on this consonant belongs to the suffix that follows.
            return consonant

        vowel = _vowel_value(analysis, scheme, word, collected) if with_vowel else ""

        if analysis.furtive:
            # A furtive patah is spoken before its own consonant, so it is
            # written before it: `koaḥ`, not `koḥa`.
            return vowel + consonant

        return consonant + vowel

    head = "".join(render(body[i], i) for i in range(min(prefix_clusters, len(body))))
    rest = "".join(render(body[i], i) for i in range(prefix_clusters, len(body)))
    rest += trailing

    if prefix_clusters and head and rest:
        if scheme.hyphenate_prefixes:
            return f"{head}-{rest}"
        if scheme.join_and_capitalize_prefixes:
            return head + rest[:1].upper() + rest[1:]
    return head + rest


_YIDDISH_VOWEL_LETTERS = frozenset({hebrew.ALEF, hebrew.VAV, hebrew.AYIN, hebrew.YOD})


def _yiddish_yod(
    text: str, position: int, scheme: Scheme, emitted: list[str]
) -> str:
    """Whether a bare yod is the consonant `y` or the vowel `i`.

    Both Yiddish tables print the pair and leave the choice to position: YIVO
    gives "y; i" outright, and ALA-LC marks its yod "only if a consonant". The
    test is whether the yod opens a syllable. It does when a vowel letter
    follows it or when it stands at the start of a word; otherwise it is
    carrying the vowel itself.
    """
    following = ""
    index = position + 1
    while index < len(text) and hebrew.is_point(text[index]):
        index += 1
    if index < len(text):
        following = hebrew.base_letter(text[index])

    at_start = not any(piece for piece in emitted)
    if at_start or (following and following in _YIDDISH_VOWEL_LETTERS):
        return scheme.consonant(hebrew.YOD)
    return "i"


def _romanize_yiddish(word: Word, scheme: Scheme, flags: list[Flag]) -> str:
    """Romanize Yiddish, which carries vowels in letters rather than in points.

    Matched longest first over the raw text, so `דזש` beats `זש` beats `ש`, and
    the pasekh under a double yod is seen before the double yod itself.
    """
    text = hebrew.normalize(word.raw)
    keys = sorted(scheme.sequences, key=len, reverse=True)
    pieces: list[str] = []
    position = 0

    # Yiddish carries most of its vowels in letters, so unpointed Yiddish is
    # usually fine. Words from the Hebrew and Aramaic layer are the exception:
    # `שבת` is written the Hebrew way with the vowels left out, and no rule can
    # put them back. Such a word has no vowel letter anywhere in it.
    carriers = {hebrew.ALEF, hebrew.VAV, hebrew.YOD, hebrew.AYIN}
    if len(text) > 2 and not any(
        hebrew.base_letter(character) in carriers for character in text
    ):
        flags.append(
            Flag(
                code="unpointed",
                message=(
                    "this word carries no vowel letter, so it is probably from "
                    "the Hebrew and Aramaic layer, written without vowels; they "
                    "cannot be recovered by rule"
                ),
                word=word.raw,
            )
        )

    while position < len(text):
        for key in keys:
            if not text.startswith(key, position):
                continue
            # A sequence must not swallow a letter that carries a point the
            # sequence does not include. `ייִדיש` is yod plus yod-with-hireq,
            # and matching the bare `יי` would read it as `ey`.
            after = position + len(key)
            if after < len(text) and hebrew.is_point(text[after]):
                continue
            pieces.append(scheme.sequences[key])
            position = after
            break
        else:
            character = text[position]
            if hebrew.is_letter(character):
                # Gather this letter's own marks so a dagesh or rafe is seen.
                end = position + 1
                while end < len(text) and hebrew.is_point(text[end]):
                    end += 1
                form = text[position:end]
                base = hebrew.base_letter(character)
                if hebrew.RAFE in form and base in scheme.rafe:
                    pieces.append(scheme.rafe[base])
                elif base == hebrew.SHIN and hebrew.SIN_DOT in form and scheme.sin:
                    pieces.append(scheme.sin)
                elif base == hebrew.SHIN and hebrew.SHIN_DOT in form and scheme.shin:
                    pieces.append(scheme.shin)
                elif base == hebrew.SHIN and not scheme.defines(character):
                    # YIVO writes shin bare; ALA-LC's Yiddish column dots it.
                    # Text written under one convention and romanized under the
                    # other lands here.
                    pieces.append(scheme.shin or scheme.sin)
                elif base == hebrew.YOD and hebrew.HIREQ in form:
                    # A yud carrying a khirik is the vowel outright. YIVO's
                    # alphabet gives yud two values, "y; i", and the point is
                    # what says which. There is no khirik-yud row in the source
                    # and this file does not invent one.
                    pieces.append("i")
                elif base == hebrew.YOD and end == position + 1:
                    # Both Yiddish tables give yod two values, `y` and `i`, and
                    # leave the choice to position. A yod is the vowel when a
                    # consonant precedes it and a consonant or the word's end
                    # follows; it is the consonant when it opens a syllable.
                    pieces.append(
                        _yiddish_yod(text, position, scheme, pieces)
                    )
                else:
                    pieces.append(
                        scheme.consonant(character, dagesh=hebrew.DAGESH in form)
                    )
                position = end
            else:
                pieces.append(character)
                position += 1

    return "".join(pieces)


# ---------------------------------------------------------------------------
# The public entry point
# ---------------------------------------------------------------------------

def romanize(
    text: str,
    scheme: Scheme | str | None = None,
    *,
    literal: bool = False,
    established: bool = False,
) -> Romanization:
    """Romanize mixed text under a scheme, leaving everything non-Hebrew alone.

    >>> romanize("כָּל־הָאָרֶץ").text
    'kol-ha-’arets'
    """
    chosen = _resolve_scheme(scheme)
    flags: list[Flag] = []
    output: list[str] = []

    runs: list[Run] = segment(text)
    for run in runs:
        if run.kind != "hebrew" or run.word is None:
            # Sof pasuq, paseq and the rest are Hebrew punctuation, and passing
            # them through leaves Hebrew characters in Latin output.
            output.append(hebrew.strip_punctuation(run.text))
            continue
        output.append(
            romanize_word(
                run.word, chosen, flags, literal=literal, established=established
            )
        )
        if run.trailing == hebrew.MAQAF:
            # SBL §5.1.1.4 note 9 makes this a hyphen. A scheme that wants a
            # space says so in its front matter rather than in code here.
            output.append(chosen.maqaf)

    return Romanization(text="".join(output), scheme=chosen.name, flags=flags)
