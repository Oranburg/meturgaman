"""The Hebrew writing system, as characters rather than as opinions.

Why this module exists
----------------------
Every other module here needs to answer the same small questions. Is this
character a letter or a point? Does this letter carry a dagesh? Is this vowel a
hataf? Nothing in those answers depends on which romanization standard is in
force, so none of it belongs in a scheme file and none of it belongs in the
engine.

Keeping it here has a second benefit. When the engine gets a case wrong, the
first question is always whether it misread the characters or misapplied the
rules. Those are separate files, so that is a quick question to settle.

Normalization
-------------
Hebrew text arrives from Sefaria, from PDFs, and from the user's own files, and
those three disagree about composition. `pdftotext` in particular emits
precomposed Latin diacritics decomposed, which is how a search for `ḥ` U+1E25
once returned nothing on a page plainly full of it.

Every entry point into this package runs text through `normalize` first. Hebrew
points do not precompose with their letters in NFC, so the sequence
letter-then-point survives normalization unchanged, which is what the clustering
code below expects.
"""

from __future__ import annotations

import unicodedata

__all__ = [
    "ALEF", "BET", "GIMEL", "DALET", "HE", "VAV", "ZAYIN", "HET", "TET", "YOD",
    "KAF", "FINAL_KAF", "LAMED", "MEM", "FINAL_MEM", "NUN", "FINAL_NUN",
    "SAMEKH", "AYIN", "PE", "FINAL_PE", "TSADI", "FINAL_TSADI", "QOF", "RESH",
    "SHIN", "TAV",
    "LETTERS", "FINAL_FORMS", "FINAL_TO_BASE", "BASE_TO_FINAL",
    "YIDDISH_DOUBLE_VAV", "YIDDISH_VAV_YOD", "YIDDISH_DOUBLE_YOD",
    "YIDDISH_LIGATURES", "LIGATURE_EXPANSIONS",
    "BEGADKEFAT", "GUTTURALS", "MATRES",
    "DAGESH", "RAFE", "SHIN_DOT", "SIN_DOT", "METEG", "MAQAF",
    "GERESH", "GERSHAYIM",
    "SHEVA", "HATAF_SEGOL", "HATAF_PATAH", "HATAF_QAMATS", "HIREQ", "TSERE",
    "SEGOL", "PATAH", "QAMATS", "HOLAM", "HOLAM_HASER_FOR_VAV", "QUBUTS",
    "QAMATS_QATAN",
    "VOWEL_POINTS", "HATAF_VOWELS", "SHORT_VOWELS", "LONG_VOWELS",
    "VOWEL_NAMES", "LETTER_NAMES",
    "CANTILLATION", "DOTTED_CIRCLE",
    "normalize", "strip_points", "strip_cantillation", "strip_vowels",
    "is_letter", "is_final", "is_point", "is_vowel", "is_cantillation",
    "base_letter", "consonantal_skeleton", "has_hebrew", "is_hebrew_word",
]


# ---------------------------------------------------------------------------
# Letters
# ---------------------------------------------------------------------------

ALEF = "א"
BET = "ב"
GIMEL = "ג"
DALET = "ד"
HE = "ה"
VAV = "ו"
ZAYIN = "ז"
HET = "ח"
TET = "ט"
YOD = "י"
FINAL_KAF = "ך"
KAF = "כ"
LAMED = "ל"
FINAL_MEM = "ם"
MEM = "מ"
FINAL_NUN = "ן"
NUN = "נ"
SAMEKH = "ס"
AYIN = "ע"
FINAL_PE = "ף"
PE = "פ"
FINAL_TSADI = "ץ"
TSADI = "צ"
QOF = "ק"
RESH = "ר"
SHIN = "ש"
TAV = "ת"

#: The twenty-two letters, in alphabetical order.
LETTERS = (
    ALEF, BET, GIMEL, DALET, HE, VAV, ZAYIN, HET, TET, YOD, KAF, LAMED,
    MEM, NUN, SAMEKH, AYIN, PE, TSADI, QOF, RESH, SHIN, TAV,
)

#: The five letters that take a distinct shape at the end of a word.
FINAL_FORMS = (FINAL_KAF, FINAL_MEM, FINAL_NUN, FINAL_PE, FINAL_TSADI)

# Three ligatures Unicode encodes for Yiddish. Yiddish writes several vowels and
# diphthongs with doubled letters, and these are the single-codepoint spellings.
# The same sounds are also written as two separate letters, and a file gives no
# clue which its author used, so both spellings have to be recognized.
YIDDISH_DOUBLE_VAV = "װ"   # U+05F0, tsvey vovn
YIDDISH_VAV_YOD = "ױ"      # U+05F1, vov yud
YIDDISH_DOUBLE_YOD = "ײ"   # U+05F2, tsvey yudn

#: The Yiddish ligatures. Kept apart from LETTERS so that a check for "does this
#: scheme define all twenty-two letters" does not start demanding these of a
#: Hebrew scheme that has no business defining them.
YIDDISH_LIGATURES = (YIDDISH_DOUBLE_VAV, YIDDISH_VAV_YOD, YIDDISH_DOUBLE_YOD)

#: What each ligature is written as when spelled out in separate letters.
LIGATURE_EXPANSIONS = {
    YIDDISH_DOUBLE_VAV: VAV + VAV,
    YIDDISH_VAV_YOD: VAV + YOD,
    YIDDISH_DOUBLE_YOD: YOD + YOD,
}

FINAL_TO_BASE = {
    FINAL_KAF: KAF,
    FINAL_MEM: MEM,
    FINAL_NUN: NUN,
    FINAL_PE: PE,
    FINAL_TSADI: TSADI,
}
BASE_TO_FINAL = {base: final for final, base in FINAL_TO_BASE.items()}

#: The six letters whose sound changes with a dagesh lene. Whether a given
#: scheme marks that change is the scheme's business, not this module's: SBL
#: academic prints none of the spirants, and SBL general prints three of them.
BEGADKEFAT = (BET, GIMEL, DALET, KAF, PE, TAV)

#: The gutturals plus resh. These do not take a dagesh forte, which is the fact
#: that drives compensatory lengthening and, downstream, several vowel rules.
GUTTURALS = (ALEF, HE, HET, AYIN, RESH)

#: The three letters that can stand as vowel letters rather than consonants.
#: Deciding which role a given occurrence plays is a classification problem,
#: handled in `romanize.rules`, not a lookup.
MATRES = (ALEF, HE, VAV, YOD)

LETTER_NAMES = {
    ALEF: "alef", BET: "bet", GIMEL: "gimel", DALET: "dalet", HE: "he",
    VAV: "vav", ZAYIN: "zayin", HET: "ḥet", TET: "tet", YOD: "yod",
    KAF: "kaf", LAMED: "lamed", MEM: "mem", NUN: "nun", SAMEKH: "samekh",
    AYIN: "ayin", PE: "pe", TSADI: "tsadi", QOF: "qof", RESH: "resh",
    SHIN: "shin", TAV: "tav",
    FINAL_KAF: "final kaf", FINAL_MEM: "final mem", FINAL_NUN: "final nun",
    FINAL_PE: "final pe", FINAL_TSADI: "final tsadi",
    YIDDISH_DOUBLE_VAV: "tsvey vovn", YIDDISH_VAV_YOD: "vov yud",
    YIDDISH_DOUBLE_YOD: "tsvey yudn",
}


# ---------------------------------------------------------------------------
# Marks that are not vowels
# ---------------------------------------------------------------------------

DAGESH = "ּ"          # also mapiq in he, and shuruq's dot in vav
RAFE = "ֿ"            # the explicit "no dagesh" mark, rare in modern texts
SHIN_DOT = "ׁ"
SIN_DOT = "ׂ"
METEG = "ֽ"           # secondary stress; matters for qamats classification
MAQAF = "־"           # the Hebrew hyphen joining words into one stress unit
GERESH = "׳"
GERSHAYIM = "״"

#: U+0591 through U+05AF, the te'amim. Meaningful for chanting and for syntax,
#: and noise for romanization, so the engine strips them and says that it did.
CANTILLATION = frozenset(chr(code) for code in range(0x0591, 0x05B0))

#: U+25CC, the placeholder a vowel point is drawn on when shown in isolation.
#: The scheme tables use it in their Sign column, so the loader strips it.
DOTTED_CIRCLE = "◌"


# ---------------------------------------------------------------------------
# Vowel points
# ---------------------------------------------------------------------------

SHEVA = "ְ"
HATAF_SEGOL = "ֱ"
HATAF_PATAH = "ֲ"
HATAF_QAMATS = "ֳ"
HIREQ = "ִ"
TSERE = "ֵ"
SEGOL = "ֶ"
PATAH = "ַ"
QAMATS = "ָ"
HOLAM = "ֹ"
HOLAM_HASER_FOR_VAV = "ֺ"
QUBUTS = "ֻ"

#: U+05C7. Unicode gives qamats qatan its own codepoint, but almost no text in
#: the wild uses it: Sefaria's editions write plain qamats U+05B8 and leave the
#: reader to tell gadol from qatan. That is why `romanize.rules` has to decide
#: the question rather than look it up, and why it flags when it cannot.
QAMATS_QATAN = "ׇ"

VOWEL_POINTS = (
    SHEVA, HATAF_SEGOL, HATAF_PATAH, HATAF_QAMATS, HIREQ, TSERE, SEGOL,
    PATAH, QAMATS, HOLAM, HOLAM_HASER_FOR_VAV, QUBUTS, QAMATS_QATAN,
)

#: The reduced vowels. Each is unambiguously vocal, which makes them the anchor
#: for deciding whether a neighbouring plain sheva is vocal too.
HATAF_VOWELS = (HATAF_SEGOL, HATAF_PATAH, HATAF_QAMATS)

SHORT_VOWELS = (PATAH, SEGOL, HIREQ, QUBUTS, QAMATS_QATAN)
LONG_VOWELS = (QAMATS, TSERE, HOLAM, HOLAM_HASER_FOR_VAV)

VOWEL_NAMES = {
    SHEVA: "sheva", HATAF_SEGOL: "hataf segol", HATAF_PATAH: "hataf patach",
    HATAF_QAMATS: "hataf qamats", HIREQ: "hireq", TSERE: "tsere",
    SEGOL: "segol", PATAH: "patach", QAMATS: "qamats", HOLAM: "holam",
    HOLAM_HASER_FOR_VAV: "holam haser for vav", QUBUTS: "qibbuts",
    QAMATS_QATAN: "qamats qatan",
}

_POINTS = frozenset(VOWEL_POINTS) | {DAGESH, RAFE, SHIN_DOT, SIN_DOT, METEG} | CANTILLATION
_LETTERS = frozenset(LETTERS) | frozenset(FINAL_FORMS) | frozenset(YIDDISH_LIGATURES)
_VOWELS = frozenset(VOWEL_POINTS)


# ---------------------------------------------------------------------------
# Predicates
# ---------------------------------------------------------------------------

def is_letter(character: str) -> bool:
    """True for the twenty-two letters and the five final forms."""
    return character in _LETTERS


def is_final(character: str) -> bool:
    """True for the five word-final letter shapes."""
    return character in FINAL_TO_BASE


def is_point(character: str) -> bool:
    """True for any combining mark: vowel, dagesh, dot, meteg, or cantillation."""
    return character in _POINTS


def is_vowel(character: str) -> bool:
    """True for a vowel point, sheva and the hatafs included."""
    return character in _VOWELS


def is_cantillation(character: str) -> bool:
    """True for a te'am, the accents in the U+0591 to U+05AF block."""
    return character in CANTILLATION


def base_letter(character: str) -> str:
    """The non-final shape of a letter. Every other character is returned as is."""
    return FINAL_TO_BASE.get(character, character)


def has_hebrew(text: str) -> bool:
    """True when the text contains at least one Hebrew letter."""
    return any(character in _LETTERS for character in text)


def is_hebrew_word(text: str) -> bool:
    """True when every non-point character is a Hebrew letter.

    Used to tell a Hebrew run from surrounding Latin so that mixed text is
    romanized in the Hebrew parts and left alone everywhere else.
    """
    letters = [character for character in text if not is_point(character)]
    return bool(letters) and all(character in _LETTERS for character in letters)


# ---------------------------------------------------------------------------
# Normalization and stripping
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Put text into NFC, the composition every other function here assumes.

    Hebrew points do not compose onto their letters, so a letter followed by its
    points survives this unchanged. What it does fix is Latin output and Latin
    input: `ḥ` arrives from some PDF extractors as `h` plus a combining dot, and
    comparing that against the precomposed character silently fails.
    """
    return unicodedata.normalize("NFC", text)


def strip_cantillation(text: str) -> str:
    """Remove the te'amim, keeping letters, vowels and dagesh."""
    return "".join(character for character in text if not is_cantillation(character))


def strip_vowels(text: str) -> str:
    """Remove vowel points, keeping letters, dagesh, the dots and cantillation.

    Distinct from `strip_points`: this leaves the shin dot in place, so shin and
    sin stay distinguishable in text that has otherwise been stripped bare.
    """
    return "".join(character for character in text if character not in _VOWELS)


def strip_points(text: str) -> str:
    """Remove every combining mark, leaving letters alone."""
    return "".join(character for character in text if not is_point(character))


def consonantal_skeleton(text: str) -> str:
    """The letters alone, final forms folded to their base shapes.

    This is the form on which two editions of a text are compared. Editions
    disagree constantly about vocalization and about cantillation, and those
    disagreements are apparatus rather than variant readings. A disagreement in
    the skeleton is a different matter and is worth a reader's attention.
    """
    return "".join(
        base_letter(character) for character in normalize(text) if is_letter(character)
    )
