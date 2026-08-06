"""Break Hebrew text into letters with everything attached to each one.

Hebrew is written as a base letter followed by any number of combining marks: a
dagesh in the letter's body, a vowel beneath it, a shin dot above, a meteg, one
or more cantillation accents. Unicode stores those as separate codepoints in a
stream, and every rule downstream is about a letter *and its marks together*.

So the first pass turns

    ד ָ ּ ב                          (a stream of codepoints)

into

    Cluster(letter='ד', vowel=qamats, dagesh=True)

and nothing after this point looks at a bare codepoint again. Getting this wrong
is the quiet way to produce output that is almost right: a vowel attached to the
wrong letter still romanizes to a real-looking word.

This module decides nothing. It reports what is written. Whether a dagesh is
lene or forte, whether a sheva is vocal, whether a vav is a consonant, are all
questions for `rules.py`, which needs the whole word in hand to answer them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from meturgaman import hebrew

__all__ = ["Cluster", "Word", "Run", "segment", "cluster_word"]


@dataclass
class Cluster:
    """One Hebrew letter together with every mark written on it."""

    letter: str
    #: Position of this cluster within its word, counting from zero.
    index: int
    #: The characters this cluster was built from, in their original order.
    raw: str

    dagesh: bool = False
    rafe: bool = False
    shin_dot: bool = False
    sin_dot: bool = False
    geresh: bool = False
    #: Meteg marks secondary stress. It is the single most useful mark in the
    #: whole system for this tool, because it is what distinguishes a long
    #: qamats from a short one in the one configuration where they look alike.
    meteg: bool = False

    #: The vowel point written under this letter, or None. Sheva counts.
    vowel: str | None = None
    cantillation: tuple[str, ...] = ()

    @property
    def base(self) -> str:
        """The letter's non-final shape."""
        return hebrew.base_letter(self.letter)

    @property
    def is_final_form(self) -> bool:
        return hebrew.is_final(self.letter)

    @property
    def has_vowel(self) -> bool:
        """True for any vowel point including sheva."""
        return self.vowel is not None

    @property
    def has_full_vowel(self) -> bool:
        """True for a vowel that is not sheva. Sheva is not a syllable nucleus."""
        return self.vowel is not None and self.vowel != hebrew.SHEVA

    @property
    def is_sheva(self) -> bool:
        return self.vowel == hebrew.SHEVA

    @property
    def is_hataf(self) -> bool:
        return self.vowel in hebrew.HATAF_VOWELS

    @property
    def is_begadkefat(self) -> bool:
        return self.base in hebrew.BEGADKEFAT

    @property
    def is_guttural(self) -> bool:
        """The gutturals plus resh: the letters that refuse a dagesh forte."""
        return self.base in hebrew.GUTTURALS

    def __str__(self) -> str:  # pragma: no cover
        return self.raw


@dataclass
class Word:
    """A run of Hebrew letters, clustered."""

    clusters: list[Cluster]
    raw: str
    #: True when a maqaf followed this word, joining it to the next. A maqaf
    #: makes two words share one stress, which is what makes the qamats in
    #: `כָּל־` short, so the fact has to survive into classification.
    followed_by_maqaf: bool = False

    def __len__(self) -> int:
        return len(self.clusters)

    def __iter__(self):
        return iter(self.clusters)

    def __getitem__(self, index: int) -> Cluster:
        return self.clusters[index]

    @property
    def letters(self) -> str:
        return "".join(cluster.letter for cluster in self.clusters)

    @property
    def is_pointed(self) -> bool:
        """True when any letter carries a vowel.

        Unpointed text cannot be romanized by rule, only guessed at, so the
        engine refuses it rather than inventing vowels.
        """
        return any(cluster.has_vowel for cluster in self.clusters)

    @property
    def has_meteg(self) -> bool:
        return any(cluster.meteg for cluster in self.clusters)

    def syllable_count_estimate(self) -> int:
        """How many full vowels the word carries.

        An estimate, not an analysis: it counts vowel nuclei and ignores every
        subtlety about diphthongs and furtive patah. It is used only where a
        rough count is enough, such as deciding whether a word before a maqaf is
        a monosyllable.
        """
        return sum(1 for cluster in self.clusters if cluster.has_full_vowel)


@dataclass
class Run:
    """A stretch of the input that is all one kind of thing."""

    kind: str  # 'hebrew' | 'other'
    text: str
    word: Word | None = None
    #: Separator that followed this run in the source: a space, a maqaf, or "".
    trailing: str = ""
    flags: list[str] = field(default_factory=list)


def cluster_word(text: str) -> Word:
    """Turn one run of Hebrew into a Word.

    Combining marks bind to the letter that precedes them. A mark appearing
    before any letter has nothing to attach to; rather than dropping it, which
    would silently change the text, it is kept in `raw` so the round trip still
    reproduces the input.
    """
    text = hebrew.normalize(text)
    clusters: list[Cluster] = []
    orphan_marks: list[str] = []

    for character in text:
        if hebrew.is_letter(character):
            clusters.append(
                Cluster(
                    letter=character,
                    index=len(clusters),
                    raw="".join(orphan_marks) + character,
                )
            )
            orphan_marks.clear()
            continue

        if not clusters:
            orphan_marks.append(character)
            continue

        current = clusters[-1]
        current.raw += character

        if character == hebrew.DAGESH:
            current.dagesh = True
        elif character == hebrew.RAFE:
            current.rafe = True
        elif character == hebrew.SHIN_DOT:
            current.shin_dot = True
        elif character == hebrew.SIN_DOT:
            current.sin_dot = True
        elif character == hebrew.METEG:
            current.meteg = True
        elif character in (hebrew.GERESH, hebrew.GERSHAYIM):
            current.geresh = True
        elif hebrew.is_cantillation(character):
            current.cantillation = current.cantillation + (character,)
        elif hebrew.is_vowel(character):
            # Two vowels on one letter should not happen. When it does, the
            # text is damaged, and keeping the first is as good a choice as any
            # so long as the second is not silently discarded from `raw`.
            if current.vowel is None:
                current.vowel = character
        # Anything else, such as a stray control character, stays in `raw` and
        # is otherwise ignored.

    return Word(clusters=clusters, raw=text)


def segment(text: str) -> list[Run]:
    """Split mixed text into Hebrew runs and everything else.

    A file is rarely all Hebrew. It is a sentence of English with a phrase of
    Hebrew in it, or a citation, or a heading. Everything that is not Hebrew
    passes through untouched, which is both correct and the only way the tool
    can be pointed at a real document.

    The maqaf is treated as a separator rather than as part of a word, because
    it joins two words into one stress unit and each side needs clustering on
    its own. That it was there is recorded on the run it followed.
    """
    text = hebrew.normalize(text)
    runs: list[Run] = []
    buffer: list[str] = []
    mode: str | None = None

    def flush() -> None:
        if not buffer:
            return
        content = "".join(buffer)
        if mode == "hebrew":
            runs.append(Run(kind="hebrew", text=content, word=cluster_word(content)))
        else:
            runs.append(Run(kind="other", text=content))
        buffer.clear()

    for character in text:
        if character == hebrew.MAQAF:
            flush()
            mode = None
            if runs and runs[-1].kind == "hebrew" and runs[-1].word is not None:
                runs[-1].word.followed_by_maqaf = True
                runs[-1].trailing = hebrew.MAQAF
            else:
                runs.append(Run(kind="other", text=hebrew.MAQAF))
            continue

        kind = "hebrew" if (hebrew.is_letter(character) or hebrew.is_point(character)) else "other"
        # A combining mark with no Hebrew letter open belongs to whatever run is
        # already being built rather than starting a Hebrew one.
        if kind == "hebrew" and mode != "hebrew" and not hebrew.is_letter(character):
            kind = "other"
        if mode is not None and kind != mode:
            flush()
        mode = kind
        buffer.append(character)

    flush()
    return runs
