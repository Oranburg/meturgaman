"""The romanization engine, tested against known words.

The first four tests are the four defects the previous engine shipped. They are
named individually rather than folded into a table so that a regression says
which one came back.
"""

from __future__ import annotations

import pytest

from meturgaman import hebrew
from meturgaman.romanize import detect, register, reverse
from meturgaman.romanize.cluster import cluster_word, segment
from meturgaman.romanize.engine import romanize
from meturgaman.romanize.rules import classify, qamats_qatan_words
from meturgaman.scheme import all_schemes


# ---------------------------------------------------------------------------
# The four that were wrong
# ---------------------------------------------------------------------------

def test_qamats_qatan_in_kol():
    """`כָּל` is kol, not kal.

    The old engine returned `kal` and raised no flag, which is the worse half:
    the conventions file promised a flag on exactly this case and none fired.
    """
    result = romanize("כָּל")
    assert result.text == "kol"


def test_qamats_qatan_before_a_silent_sheva():
    """`חָכְמָה` is ḥokhmah, not ḥakhemah.

    Two faults at once in the old engine: it read the qamats as long and the
    sheva as vocal. They are linked, and getting the qamats right is what makes
    the sheva silent.

    It is decided here by the lexical list rather than by a rule, and no flag
    fires, because the word is known. See the test below for why that is the
    right division of labour.
    """
    result = romanize("חָכְמָה")
    assert result.text == "ḥokhmah"


def test_the_same_shape_stays_long_when_the_word_is_not_in_the_list():
    """The shape `חָכְמָה` has is not enough to decide, and the engine says so.

    An earlier version read every qamats before a sheva as short. Tested against
    1,934 words of running text it fired fifteen times and was wrong fifteen
    times, giving *hoytah* for `הָיְתָה` and *levovkha* for `לְבָבְךָ`. Long is now
    the answer and a flag marks the shape.
    """
    for word, expected in (("הָיְתָה", "haytah"), ("שָׁרְצוּ", "sharetsu")):
        result = romanize(word)
        assert result.text == expected, f"{word}: {result.text}"

    flagged = romanize("שָׁרְצוּ")
    assert any(
        flag.code in ("qamats-may-be-short", "sheva-after-qamats")
        for flag in flagged.flags
    ), "the shape is ambiguous and nothing said so"


def test_meteg_makes_the_qamats_long():
    """A meteg marks the syllable as open or accented, so the qamats is long."""
    result = romanize("שָֽׁמְרָה")
    assert result.text.startswith("sha"), result.text


# ---------------------------------------------------------------------------
# Ported from the predecessor engine's last night of fixes, found by testing
# it against a hand-built glossary. Most were already right here by design;
# they are pinned so a regression says which one came back.
# ---------------------------------------------------------------------------

def test_sheva_before_a_dagesh_is_silent():
    """`מְתוּרְגְּמָן` is meturgeman, not *meturegeman*.

    The sheva under the resh follows a shuruq, and the long-vowel rule read it
    as vocal. The dagesh on the following gimel is the evidence against that:
    a forte closes the syllable it doubles out of, and a begadkefat keeps its
    lene only after a closed syllable, since a vocal sheva would have
    spirantised it. Either way the syllable is the closed *tur*.

    This is the class of defect the finite-domain guards cannot reach: table
    coverage is complete and every cell is right, and the error is in how
    context selects among them.
    """
    assert romanize("מְתוּרְגְּמָן").text == "meturgeman"
    # The diphthong and suffix rules that precede the new one still hold.
    assert romanize("וַיְדַבֵּר").text == "vaydabber"


def test_a_root_letter_is_not_mistaken_for_a_prefixed_article():
    """`לָאו` is lav and `כָּחוּשׁ` is kaḥush: both letters belong to the root.

    The article's vowel on ב, ל, or כ marks a contraction only when the next
    consonant carries the dagesh the contraction produces.
    """
    assert romanize("לָאו").text == "lav"
    assert romanize("כָּחוּשׁ").text == "kaḥush"
    assert romanize("הַמֶּלֶךְ").text == "ha-melekh"


def test_a_vav_is_a_mater_only_when_the_previous_consonant_needs_a_vowel():
    """`שָׁלוֹם` is shalom but `עֲוֹן` is ‘avon.

    Both are vav-plus-holam. In the first the lamed carries no vowel, so the
    vav supplies one. In the second the ayin already has its hataf-patach, so
    the vav is consonantal and the holam is its own vowel.
    """
    assert romanize("שָׁלוֹם").text == "shalom"
    assert romanize("עֲוֹן").text == "‘avon"


def test_a_yod_with_a_dagesh_is_consonantal_and_doubles():
    """`חִיּוּבָא` is ḥiyyuva, not *ḥiuva*: the dagesh says the yod is a consonant."""
    assert romanize("חִיּוּבָא").text == "ḥiyyuva"
    assert romanize("בַּיִת").text == "bayit"


def test_maqaf_becomes_a_hyphen():
    """SBL §5.1.1.4 note 9. The old engine emitted a space."""
    result = romanize("כָּל־הָאָרֶץ")
    assert "-" in result.text
    assert result.text == "kol-ha-’arets"


def test_yod_with_dagesh_is_a_doubled_consonant():
    """`חִיּוּבָא` is ḥiyyuva. The old engine skipped the yod entirely."""
    assert romanize("חִיּוּבָא").text == "ḥiyyuva"


def test_vav_after_a_voweled_consonant_is_a_consonant():
    """`עֲוֹן` is ʿavon, not ʿaon.

    The ayin already carries a hataf patah, so the vav cannot be a vowel letter
    for it and must be a consonant carrying the holam.
    """
    assert romanize("עֲוֹן", "sbl-academic").text == "ʿăwōn"
    assert romanize("עֲוֹן").text == "‘avon"


def test_prefix_detection_does_not_split_ordinary_words():
    """The old engine produced `ka-ḥush` and `la-v`.

    Both are ordinary words whose first letter merely looks like a prefix.
    """
    assert romanize("כָּחוּשׁ").text == "kaḥush"
    assert romanize("לָאו").text == "lav"


# ---------------------------------------------------------------------------
# The golden corpus
# ---------------------------------------------------------------------------

GOLDEN = [
    ("רַב", "rav"),
    ("נֶפֶשׁ", "nefesh"),
    ("שָׁלוֹם", "shalom"),
    ("תּוֹרָה", "torah"),
    ("שַׁבָּת", "shabbat"),
    ("מִצְוָה", "mitsvah"),
    ("צֶדֶק", "tsedeq"),
    ("מֶלֶךְ", "melekh"),
    ("כַּלָּה", "kallah"),
    ("שְׁמַע", "shema‘"),
    ("בְּרֵאשִׁית", "bereshit"),
    ("הַמֶּלֶךְ", "ha-melekh"),
    ("חָכְמָה", "ḥokhmah"),
    ("כָּל", "kol"),
]


@pytest.mark.parametrize("source,expected", GOLDEN, ids=[word for word, _ in GOLDEN])
def test_golden_corpus_under_the_default_scheme(source: str, expected: str):
    assert romanize(source).text == expected


def test_the_article_does_not_double_in_sbl_general():
    """SBL general note 2: `ha-melekh`, not `ha-mmelekh`."""
    assert romanize("הַמֶּלֶךְ").text == "ha-melekh"
    # BGN does double, and joins the article rather than hyphenating it,
    # capitalizing what follows. Whether the article's own h is capitalized
    # depends on the word being a proper noun, which the engine has no way to
    # know, so it leaves that to the writer.
    assert romanize("הַמֶּלֶךְ", "bgn-pcgn").text == "haMmelekh"


def test_final_he_keeps_its_h_in_schemes_with_no_rule_for_the_pair():
    """`תּוֹרָה` is torah everywhere, by two different routes.

    SBL states a value for qamats plus final he and uses it. ALA-LC and BGN
    state none, so the qamats is written as a vowel and the he as a consonant.
    Both arrive at the same place, and an earlier version arrived at `tora`.
    """
    for name in ("sbl-general", "ala-lc", "bgn-pcgn", "encyclopaedia-judaica-general"):
        assert romanize("תּוֹרָה", name).text == "torah", name
    assert romanize("תּוֹרָה", "sbl-academic").text == "tôrâ"


# ---------------------------------------------------------------------------
# Every scheme, on every letter
# ---------------------------------------------------------------------------

HEBREW_SCHEMES = sorted(
    name for name, scheme in all_schemes().items() if scheme.script == "hebrew"
)


@pytest.mark.parametrize("name", HEBREW_SCHEMES)
def test_no_scheme_raises_on_ordinary_text(name: str):
    """Every Hebrew scheme handles a real verse without an exception."""
    verse = "בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם וְאֵת הָאָרֶץ"
    result = romanize(verse, name)
    assert result.text.strip()
    assert not hebrew.has_hebrew(result.text)


@pytest.mark.parametrize("name", HEBREW_SCHEMES)
def test_each_scheme_is_recognizable_from_its_own_output(name: str):
    """Romanize under a scheme, then work out which scheme it was.

    Every signature is derived from the tables, so this also proves the
    signatures have not drifted from what the schemes actually emit.
    """
    phrase = "שַׁבָּת שָׁלוֹם וְחָכְמָה תּוֹרָה צֶדֶק קֹדֶשׁ"
    latin = romanize(phrase, name).text
    guesses = detect.detect(latin)
    assert guesses, f"nothing distinctive in {name}'s output: {latin!r}"
    assert guesses[0].scheme == name, (
        f"{name} produced {latin!r}, which was read as {guesses[0].scheme}"
    )


def test_no_scheme_is_undetectable():
    assert detect.undetectable() == []


# ---------------------------------------------------------------------------
# Reverse
# ---------------------------------------------------------------------------

def test_reverse_recovers_the_consonantal_skeleton():
    """Latin back to Hebrew letters, on the skeleton only."""
    candidate = reverse.reverse("shalom", "sbl-general")[0]
    assert candidate.letters == "שׁלם", "the last letter must take its final form"
    assert candidate.is_certain


def test_reverse_reports_ambiguity_rather_than_choosing_quietly():
    """`t` could be tet or tav in SBL general, and the caller is told so."""
    candidate = reverse.reverse("torah", "sbl-general")[0]
    assert not candidate.is_certain
    assert any("ט" in note and "ת" in note for note in candidate.ambiguities)


def test_reverse_keeps_word_boundaries_and_finals_per_word():
    """A space is a boundary, not decoration to discard like an apostrophe.

    The old scan treated the space the same way as a diacritic apostrophe
    and ran the final-letter fix-up once for the whole reconstruction, so
    "shalom aleichem" came back as one run-on string, "שׁלמלהם", with only
    the very last letter of the whole phrase in its final form.
    """
    candidate = reverse.reverse("shalom aleichem", "sbl-general")[0]
    words = candidate.letters.split(" ")
    assert len(words) == 2, candidate.letters
    # Both words end in mem here, and both must take the final form: the
    # boundary is preserved and the fix-up runs on each word, not once for
    # the whole reconstruction.
    assert words[0][-1] == hebrew.FINAL_MEM
    assert words[1][-1] == hebrew.FINAL_MEM


def test_academic_is_more_reversible_than_general():
    """The point of the academic style is that it can be reversed."""
    academic = reverse.reverse("tôrâ", "sbl-academic")[0]
    general = reverse.reverse("torah", "sbl-general")[0]
    assert len(academic.ambiguities) <= len(general.ambiguities)


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

def test_ashkenazi_register_is_recognized():
    found = register.detect_register("Shabbos, Sukkos, and the halachah of mitzvos")
    assert found.register == register.ASHKENAZI
    assert found.is_confident


def test_sephardi_register_is_recognized():
    found = register.detect_register("Shabbat, Sukkot, and the halakhah of mitzvot")
    assert found.register == register.SEPHARDI
    assert found.is_confident


def test_the_guard_refuses_to_rewrite_ashkenazi_as_sephardi():
    """The specific edit that damaged a real file.

    A folder of notes using Shabbos nineteen times had `shaliach` rewritten as
    `shaliaḥ` throughout. That is not a correction.
    """
    text = "Shabbos and halachah and Sukkos and mitzvos and shaliach"
    with pytest.raises(register.RegisterConflict):
        register.preserve_guard(text, "sbl-general")


def test_the_guard_allows_a_scheme_that_stays_in_register():
    text = "Shabbos and halachah and Sukkos and mitzvos"
    register.preserve_guard(text, "yivo")
    register.preserve_guard(text, "ala-lc-yiddish")


def test_the_guard_can_be_overridden_deliberately():
    text = "Shabbos and halachah and Sukkos and mitzvos"
    register.preserve_guard(text, "sbl-general", force=True)


def test_the_guard_does_not_fire_on_neutral_text():
    register.preserve_guard("shalom", "sbl-general")


# ---------------------------------------------------------------------------
# Clustering and flags
# ---------------------------------------------------------------------------

def test_clustering_binds_marks_to_their_letter():
    word = cluster_word("בָּרָא")
    assert [c.letter for c in word] == ["ב", "ר", "א"]
    assert word[0].dagesh
    assert word[0].vowel == hebrew.QAMATS
    assert not word[2].has_vowel


def test_segmentation_leaves_non_hebrew_alone():
    runs = segment("The word שָׁלוֹם means peace.")
    kinds = [run.kind for run in runs]
    assert "hebrew" in kinds and "other" in kinds
    assert romanize("The word שָׁלוֹם means peace.").text == (
        "The word shalom means peace."
    )


def test_unpointed_text_is_flagged_rather_than_guessed_at():
    result = romanize("שלום")
    assert any(flag.code == "unpointed" for flag in result.flags)


def test_a_yiddish_scheme_on_pointed_hebrew_is_flagged():
    result = romanize("חָכְמָה", "yivo")
    assert any(flag.code == "script-mismatch" for flag in result.flags)


def test_the_qamats_qatan_list_stays_short():
    """A word list that grows is a glossary, and a glossary hides engine faults."""
    words = qamats_qatan_words()
    assert len(words) <= 12, (
        f"the qamats-qatan list has grown to {len(words)} entries. Each addition "
        f"should have been a rule."
    )
    assert hebrew.consonantal_skeleton("כָּל") in words


# ---------------------------------------------------------------------------
# Yiddish
# ---------------------------------------------------------------------------

def test_yivo_romanizes_yiddish():
    assert romanize("אַ גוטן טאָג", "yivo").text == "a gutn tog"
    assert romanize("ייִדיש", "yivo").text == "yidish"


def test_yivo_reads_rafe_as_the_spirant():
    """`בֿרוך` is vrukh: YIVO marks the spirant with a rafe, not by its absence."""
    assert romanize("בֿרוך", "yivo").text == "vrukh"


def test_a_loshn_koydesh_word_without_vowels_is_flagged():
    """`שבת` in a Yiddish text has no vowel letters and cannot be recovered."""
    result = romanize("שבת", "yivo")
    assert any(flag.code == "unpointed" for flag in result.flags)
