"""Tests for modern Israeli legislation.

Every test here names the real document that produced it, in the house style:
a defect is reproduced against the source that exhibited it, so that the reason
a test exists survives the person who wrote it.

The fixture is a real retrieval. `tests/fixtures/remedies-1970.web-copy.txt` is
`pdftotext -layout` over a PDF served from a Chinese Ministry of Commerce mirror
of Israeli legislation, fetched 2026-08-09. It carries an HTML-to-PDF
converter's evaluation watermark on every page, names no translator, and prints
each section's marginal heading *after* the section body rather than beside it.
That combination is exactly why the parser reports marginal headings as
candidates instead of attaching them, and why the source sits at tier
`unattributed` rather than `authorized`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from meturgaman.sources import israel

FIXTURES = Path(__file__).parent / "fixtures"
WEB_COPY = FIXTURES / "remedies-1970.web-copy.txt"


# ---------------------------------------------------------------------------
# The authority ladder
# ---------------------------------------------------------------------------


def test_the_ladder_ranks_authorized_above_every_unofficial_tier():
    """L.S.I. outranks a web copy. This is the whole point of the module."""
    assert israel.authority_rank("authorized") < israel.authority_rank("commercial")
    assert israel.authority_rank("commercial") < israel.authority_rank("unattributed")
    assert israel.authority_rank("unattributed") < israel.authority_rank("assistant")


def test_enacted_outranks_authorized():
    """The CISG's English is authentic text under its own Art. 101.

    An authorized translation is a translation. Authentic treaty text is the
    law, so it cannot sit below one.
    """
    assert israel.authority_rank("enacted") < israel.authority_rank("authorized")


def test_an_unknown_tier_ranks_last_rather_than_raising():
    """A typo must not silently become a high tier."""
    assert israel.authority_rank("offical") == len(israel.AUTHORITY_LADDER)
    assert israel.authority_rank("") == len(israel.AUTHORITY_LADDER)


def test_only_enacted_and_authorized_print_as_law():
    assert israel.PRINTABLE_AS_LAW == {"enacted", "authorized"}
    for tier in ("government", "commercial", "scholarly", "unattributed", "assistant"):
        assert tier not in israel.PRINTABLE_AS_LAW


# ---------------------------------------------------------------------------
# The registries
# ---------------------------------------------------------------------------


def test_every_registered_statute_carries_a_gazette_citation():
    """A statute without its Reshumot citation cannot be checked in print."""
    for slug, law in israel.STATUTES.items():
        assert law.gazette, f"{slug} has no gazette citation"
        assert law.wikisource, f"{slug} has no Hebrew source page"


def test_the_three_course_statutes_carry_their_lsi_citations():
    """The citations the acquisition request names, so a librarian can be handed one."""
    assert israel.statute("sale-1968").lsi == "22 L.S.I. 107"
    assert israel.statute("remedies-1970").lsi == "25 L.S.I. 11"
    assert israel.statute("contracts-general-1973").lsi == "27 L.S.I. 117"


def test_a_statute_after_the_series_stopped_has_no_lsi_row():
    """The 1999 international sale law postdates the L.S.I. series.

    Offering an L.S.I. row for it would send someone to a volume that does not
    exist. The registry answers the question instead.
    """
    assert israel.statute("int-sale-1999").lsi == ""
    keys = [source.key for source in israel.sources_for("int-sale-1999")]
    assert "lsi" not in keys
    assert "lsi" in [s.key for s in israel.sources_for("remedies-1970")]


def test_sources_come_back_best_tier_first():
    rows = israel.sources_for("remedies-1970")
    ranks = [israel.authority_rank(row.authority) for row in rows]
    assert ranks == sorted(ranks)
    assert rows[0].key == "lsi"


def test_every_source_names_a_tier_the_ladder_knows():
    for source in israel.TRANSLATION_SOURCES:
        assert source.authority in israel.AUTHORITY_LADDER, source.key
        assert source.reachable in {"open", "subscription", "print", "manual"}


def test_the_lsi_row_warns_about_as_enacted_text():
    """The trap that motivated the whole acquisition: L.S.I. is not consolidated.

    Setting a 1970 translation beside Hebrew amended in 2024 prints two laws
    and calls one a translation of the other.
    """
    lsi = next(s for s in israel.TRANSLATION_SOURCES if s.key == "lsi")
    assert "ENACTED" in lsi.caveat.upper()


def test_an_unknown_slug_is_refused_with_the_known_ones():
    """A plain LookupError, deliberately, and not the KeyError a dict would raise.

    The CLI re-raises a bare KeyError as an internal fault, so raising one here
    turned a mistyped slug into a traceback and buried the list of real slugs
    that the message goes to the trouble of assembling.
    """
    with pytest.raises(LookupError) as caught:
        israel.statute("sale-law")
    assert type(caught.value) is LookupError
    assert "sale-1968" in str(caught.value)


# ---------------------------------------------------------------------------
# Parsing a delivered English text
# ---------------------------------------------------------------------------


def test_the_web_copy_parses_to_all_twenty_five_sections():
    """The Remedies Law has 25 sections; the Hebrew file in K holds 25."""
    sections = israel.parse_english(WEB_COPY.read_text(encoding="utf-8"))
    assert [s.number for s in sections] == [str(n) for n in range(1, 26)]


def test_section_three_keeps_its_four_numbered_exceptions():
    """Section 3 is the section the course turns on, so it gets its own test."""
    sections = {s.number: s for s in israel.parse_english(WEB_COPY.read_text("utf-8"))}
    text = sections["3"].text
    for opener in ("(1)", "(2)", "(3)", "(4)"):
        assert opener in text, f"{opener} was lost from section 3"
    assert "unless" in text.lower()


def test_the_converter_watermark_is_dropped_and_the_law_is_not():
    """`pd4ml evaluation copy` is furniture beyond argument. Nothing else goes."""
    raw = WEB_COPY.read_text(encoding="utf-8")
    assert "pd4ml" in raw
    joined = "\n".join(s.text for s in israel.parse_english(raw))
    assert "pd4ml" not in joined
    assert "Ottoman Code of Civil Procedure" in joined


def test_a_marginal_heading_is_reported_and_never_merged_into_the_text():
    """The heading follows its body in this copy, which is how columns flatten.

    Attaching it to the section it happens to trail would be a guess, and a
    guess that is undetectable downstream. So it is reported separately.
    """
    sections = {s.number: s for s in israel.parse_english(WEB_COPY.read_text("utf-8"))}
    assert sections["1"].marginal == "Definitions"
    assert "Definitions" not in sections["1"].text


def test_paragraph_breaks_survive_and_line_wrapping_does_not():
    sections = {s.number: s for s in israel.parse_english(WEB_COPY.read_text("utf-8"))}
    definitions = sections["1"].text
    assert "\n\n" in definitions
    assert "\n " not in definitions


def test_a_section_opening_after_a_page_break_is_still_found():
    """The defect the fixture caught, held as its own test.

    `pdftotext` writes a form feed at each page boundary, and the first section
    on a page then begins with that byte rather than at a margin. Sections 6, 9,
    12 and 23 of the Remedies retrieval vanished this way: four of twenty-five,
    with no error raised and nothing in the output to show a gap.
    """
    sections = israel.parse_english("1. First.\n\f 2. After a page break.\n")
    assert [s.number for s in sections] == ["1", "2"]
    assert "\f" not in sections[1].text


def test_a_lettered_section_number_parses():
    """Israeli statutes number amendments in as 12A, 12B, and so on."""
    sections = israel.parse_english("12. Plain.\n\n12A. Added later.\n\n13. Next.\n")
    assert [s.number for s in sections] == ["12", "12A", "13"]


def test_a_text_with_no_recognizable_sections_returns_nothing_rather_than_one_blob():
    """Silence beats a single section holding the whole file under a wrong number."""
    assert israel.parse_english("A paragraph with no numbering at all.\n") == []


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------


def test_alignment_pairs_the_whole_statute():
    sections = israel.parse_english(WEB_COPY.read_text(encoding="utf-8"))
    result = israel.align([str(n) for n in range(1, 26)], sections)
    assert result.ok, result.report()
    assert result.matched[:4] == ["1", "2", "3", "4"]


def test_alignment_is_symmetric_so_a_partial_hebrew_list_reports_the_rest():
    """Asking about four sections of a twenty-five section statute is not an error.

    It is a partial question, and the report says which side the surplus is on
    so the caller can tell "I asked narrowly" from "the English is short."
    """
    sections = israel.parse_english(WEB_COPY.read_text(encoding="utf-8"))
    result = israel.align(["1", "2", "3", "4"], sections)
    assert result.matched == ["1", "2", "3", "4"]
    assert result.hebrew_only == []
    assert len(result.english_only) == 21


def test_a_missing_english_counterpart_fails_the_alignment_loudly():
    """The defect this exists to prevent, stated as a test.

    A bilingual build that pairs by position rather than by number shifts every
    later row when one row is short, and prints Hebrew beside the wrong English
    with nothing on the page to show it.
    """
    result = israel.align(["1", "2", "3"], israel.parse_english("1. One.\n\n3. Three.\n"))
    assert not result.ok
    assert result.hebrew_only == ["2"]
    assert "HEBREW WITH NO ENGLISH" in result.report()


def test_english_with_no_hebrew_is_reported_too():
    result = israel.align(["1"], israel.parse_english("1. One.\n\n2. Two.\n"))
    assert result.english_only == ["2"]


def test_section_numbers_are_matched_however_they_are_written():
    """`§ 3`, `3.`, `03` and `סעיף 3` all name section 3."""
    sections = israel.parse_english("3. The text.\n")
    for spelling in ("3", "3.", "03", "§ 3", "§3", "סעיף 3", " 3 "):
        assert israel.align([spelling], sections).ok, spelling


def test_alignment_orders_english_only_numerically_not_as_strings():
    result = israel.align([], israel.parse_english("2. Two.\n\n10. Ten.\n"))
    assert result.english_only == ["2", "10"]


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------


def test_two_witnesses_that_agree_are_confirmed():
    text = "1. The injured party is entitled to enforcement.\n"
    verdicts = israel.reconcile({
        "a": ("authorized", israel.parse_english(text)),
        "b": ("scholarly", israel.parse_english(text)),
    })
    assert [v.status for v in verdicts] == ["confirmed"]
    assert verdicts[0].best_authority == "authorized"
    assert verdicts[0].printable_as_law


def test_witnesses_differing_only_in_typography_still_confirm():
    """Curly quotes and an em dash are apparatus, not a variant reading."""
    verdicts = israel.reconcile({
        "a": ("authorized", israel.parse_english('1. The “injured party” — a person.\n')),
        "b": ("scholarly", israel.parse_english('1. The "injured party" - a person.\n')),
    })
    assert verdicts[0].status == "confirmed"


def test_witnesses_differing_in_the_words_are_disputed_and_both_are_kept():
    """`aggrieved party` and `injured party` are a real difference, not a typo.

    A translator's word choice can change what a common-law reader thinks the
    section does, so the module reports the disagreement and keeps both texts
    rather than preferring one silently.
    """
    verdicts = israel.reconcile({
        "a": ("authorized", israel.parse_english("1. The aggrieved party may enforce.\n")),
        "b": ("unattributed", israel.parse_english("1. The injured party may enforce.\n")),
    })
    assert verdicts[0].status == "disputed"
    assert set(verdicts[0].witnesses) == {"a", "b"}


def test_a_single_witness_is_marked_single_rather_than_confirmed():
    verdicts = israel.reconcile({
        "a": ("unattributed", israel.parse_english("1. One.\n")),
    })
    assert verdicts[0].status == "single"
    assert not verdicts[0].printable_as_law


def test_the_web_copy_alone_is_never_printable_as_law():
    """The finding this module was built around, held as a test.

    A complete, plausible, fluent English text of the whole statute exists on
    the open web. It is still not the authorized translation, and nothing about
    reading it can make it one.
    """
    verdicts = israel.reconcile({
        "mofcom": ("unattributed", israel.parse_english(WEB_COPY.read_text("utf-8"))),
    })
    assert verdicts
    assert not any(v.printable_as_law for v in verdicts)


def test_verdicts_come_back_in_section_order_not_string_order():
    verdicts = israel.reconcile({
        "a": ("scholarly", israel.parse_english("2. Two.\n\n10. Ten.\n")),
    })
    assert [v.number for v in verdicts] == ["2", "10"]


# ---------------------------------------------------------------------------
# The skeleton
# ---------------------------------------------------------------------------


def test_the_skeleton_ignores_case_spacing_and_dash_shape():
    assert israel.skeleton("The  Injured\nParty") == israel.skeleton("the injured party")
    assert israel.skeleton("a—b") == israel.skeleton("a-b")


def test_the_skeleton_does_not_ignore_a_different_word():
    assert israel.skeleton("aggrieved party") != israel.skeleton("injured party")


# ---------------------------------------------------------------------------
# The shape a delivery is actually asked to arrive in
# ---------------------------------------------------------------------------

DELIVERY = """§ 9. Time of delivery

The seller shall deliver the thing sold at the time agreed.

§ 11. Non-conformity

(a) The seller has not performed his obligation if he delivered
    a thing of a different kind.
(b) A thing shall be regarded as conforming.
"""


def test_the_requested_delivery_shape_parses():
    """`§ 9. Time of delivery` is the format the acquisition request asks for.

    Requiring a bare `9.` would have refused the exact shape the person doing
    the library errand was told to produce.
    """
    sections = israel.parse_english(DELIVERY)
    assert [s.number for s in sections] == ["9", "11"]
    assert sections[0].marginal == "Time of delivery"
    assert sections[1].marginal == "Non-conformity"


def test_a_leading_heading_is_lifted_out_of_the_text_not_left_in_it():
    sections = israel.parse_english(DELIVERY)
    assert sections[0].text.startswith("The seller shall deliver")
    assert "Time of delivery" not in sections[0].text


def test_a_section_opening_with_subsection_lettering_keeps_its_first_line():
    """`1. (a) In this law -` has no heading, and losing its opening would be worse.

    A parenthesis is not a heading, so nothing is lifted, and the section keeps
    every word it arrived with.
    """
    sections = israel.parse_english("1. (a) In this law -\n\n\"Breach\" - an act.\n")
    assert sections[0].marginal == ""
    assert sections[0].text.startswith("(a) In this law")


def test_a_section_whose_whole_body_is_one_short_line_keeps_it():
    """Nothing is lifted when lifting it would leave the section empty."""
    sections = israel.parse_english("4. Conditions on enforcement\n")
    assert sections[0].text == "Conditions on enforcement"
    assert sections[0].marginal == ""


def test_the_section_sign_does_not_change_the_number():
    assert [s.number for s in israel.parse_english("§ 12A. Text here.\n")] == ["12A"]


# ---------------------------------------------------------------------------
# Two-column pages
# ---------------------------------------------------------------------------

TWO_COLUMN = FIXTURES / "remedies-1970.isr-l-rev.txt"

# `pdftotext -layout` over pages 135 to 139 of Israel Law Review vol. 8 (1973),
# HeinOnline, retrieved 2026-08-09. The journal sets the section's heading in a
# narrow left column beside the body, so the flattened text puts the heading and
# the body on the same line and no section opening begins at a margin.


def test_the_margin_column_is_measured_not_assumed():
    raw = TWO_COLUMN.read_text(encoding="utf-8")
    assert israel.detect_margin_column(raw) == 14


def test_a_single_column_page_is_not_mistaken_for_two():
    """The web copy is one column. Splitting it would cut every line in half."""
    assert israel.detect_margin_column(WEB_COPY.read_text(encoding="utf-8")) is None


def test_all_twenty_five_sections_parse_out_of_a_two_column_page():
    """None of them begins at a margin, so this fails entirely without the split."""
    sections = israel.parse_english(TWO_COLUMN.read_text(encoding="utf-8"))
    assert [s.number for s in sections] == [str(n) for n in range(1, 26)]


def test_a_marginal_heading_reaches_the_section_it_labels():
    sections = {s.number: s for s in israel.parse_english(TWO_COLUMN.read_text("utf-8"))}
    assert sections["3"].marginal == "Right of enforcement"
    assert sections["1"].marginal == "Definitions"


def test_a_heading_that_wrapped_across_the_narrow_column_is_rejoined():
    """The column is too narrow to hold a heading, so the heading breaks mid-word."""
    sections = {s.number: s for s in israel.parse_english(TWO_COLUMN.read_text("utf-8"))}
    assert sections["2"].marginal == "Remedies of injured party"
    assert sections["5"].marginal == "Enforcement in the case of transaction requiring registration"


def test_no_marginal_heading_leaks_into_the_statute_text():
    """A heading spliced into the body would be an editor's words printed as law."""
    sections = {s.number: s for s in israel.parse_english(TWO_COLUMN.read_text("utf-8"))}
    assert "Right of" not in sections["3"].text
    assert sections["3"].text.startswith("The injured party is entitled to enforcement")


def test_section_three_carries_its_four_exceptions_intact():
    """The section the course turns on, from the retrieval the course will print."""
    sections = {s.number: s for s in israel.parse_english(TWO_COLUMN.read_text("utf-8"))}
    text = sections["3"].text
    for opener in ("(1)", "(2)", "(3)", "(4)"):
        assert opener in text
    assert text.rstrip().endswith("is unjust.")


def test_words_broken_at_a_line_end_are_rejoined_and_every_join_is_recorded():
    """Rejoining restores the word a reader of the page reads.

    It cannot be done blind: a word that genuinely carries a hyphen, broken at
    exactly a line end, looks the same. So each join is reported, and on this
    retrieval all nineteen are ordinary soft hyphens.
    """
    sections = israel.parse_english(TWO_COLUMN.read_text(encoding="utf-8"))
    joined = {word for s in sections for word in s.rejoined}
    assert "requires" in joined
    assert "unreasonable" in joined
    text = "\n".join(s.text for s in sections)
    assert "re- quires" not in text and "re-\nquires" not in text


def test_a_hyphenated_word_before_a_capital_is_left_alone():
    """`Anglo-` then `American` at a line end is one word and stays hyphenated."""
    body, joined = israel._dehyphenate("the Anglo-\nAmerican rule")
    assert body == "the Anglo-\nAmerican rule"
    assert joined == []


def test_splitting_refuses_a_boundary_that_would_cut_a_word():
    """Losing text to separate columns would defeat the purpose of separating them."""
    crammed = "\n".join(["Definitions1. In this Law text here that runs on"] * 8)
    assert israel.detect_margin_column(crammed) is None


# ---------------------------------------------------------------------------
# Amendment drift
# ---------------------------------------------------------------------------

# The open statute-book project's section template, as it appears in the
# consolidated Hebrew of the Remedies Law (he.wikisource revision 2897342).
WIKITEXT = """
{{ח:סעיף|10|הזכות לפיצויים}}
{{ח:ת}} טקסט.

{{ח:סעיף|11|פיצויים ללא הוכחת נזק|תיקון: תשפ״ד}}
{{ח:ת}} טקסט.

{{ח:סעיף|12|הקטנת הנזק}}
{{ח:ת}} טקסט.
"""


def test_only_a_section_with_an_amendment_marker_is_reported_amended():
    """The Remedies Law's real state: one amended section out of twenty-five.

    The acquisition request guessed that the interest-and-linkage amendment
    "most likely" touched damages rather than formation, and said plainly that
    probably is not a rights basis. The source states the answer, so it is read
    rather than reasoned about.
    """
    amended = israel.amended_sections(WIKITEXT)
    assert set(amended) == {"11"}
    assert "תיקון" in amended["11"]


def test_a_statute_with_no_amendments_reports_none():
    assert israel.amended_sections("{{ח:סעיף|1|הגדרות}}\n{{ח:ת}} טקסט.\n") == {}


def test_an_empty_source_reports_none_rather_than_raising():
    assert israel.amended_sections("") == {}


# ---------------------------------------------------------------------------
# A second two-column retrieval, with its own defects
# ---------------------------------------------------------------------------

GENERAL_PART = FIXTURES / "contracts-general-1973.isr-l-rev.txt"

# `pdftotext -layout` over the Contracts (General Part) Law, 5733-1973 as
# printed at 9 Isr. L. Rev. 282-291 (1974), where it follows Gabriela Shalev's
# commentary at 274. HeinOnline, retrieved 2026-08-09. It defeats a fixed column
# boundary that the Remedies retrieval did not: its section numbers are set so
# that `15.` begins four columns to the left of `1.`, and any single boundary
# clearing the marginal headings slices a two-digit number in half.


def test_all_sixty_four_sections_parse():
    sections = israel.parse_english(GENERAL_PART.read_text(encoding="utf-8"))
    assert [s.number for s in sections] == [str(n) for n in range(1, 65)]


def test_a_two_digit_section_number_is_not_cut_by_the_column_boundary():
    """`Deceit       15.` sets its number left of where `1.` begins."""
    sections = {s.number: s for s in israel.parse_english(GENERAL_PART.read_text("utf-8"))}
    assert sections["15"].marginal == "Deceit"
    assert sections["15"].text.startswith("A person who has entered into a contract")


def test_touching_headings_do_not_merge_into_one():
    """§ 1 came back labelled `Mode of making Contract Offer`, having eaten § 2's.

    A heading's run of marginal lines ends at the next section's opening line,
    not only at a blank one, because two short sections leave no blank between.
    """
    sections = {s.number: s for s in israel.parse_english(GENERAL_PART.read_text("utf-8"))}
    assert sections["1"].marginal == "Mode of making Contract"
    assert sections["2"].marginal == "Offer"


def test_the_formation_sections_the_course_prints_are_intact():
    """§§ 1 to 8 are formation, and no consideration requirement appears."""
    sections = {s.number: s for s in israel.parse_english(GENERAL_PART.read_text("utf-8"))}
    assert sections["1"].text.startswith("A contract is made by way of offer and acceptance")
    assert sections["2"].marginal == "Offer"
    assert sections["5"].marginal == "Acceptance"
    assert "consideration" not in " ".join(
        sections[str(n)].text.lower() for n in range(1, 9)
    )


def test_the_journals_running_head_is_removed_and_reported():
    """`ISRAEL LAW REVIEW` printed inside a section is furniture, not statute."""
    furniture: list[str] = []
    sections = israel.parse_english(
        GENERAL_PART.read_text(encoding="utf-8"), furniture=furniture
    )
    assert any("ISRAEL LAW REVIEW" in line for line in furniture)
    assert "ISRAEL LAW REVIEW" not in "\n".join(s.text for s in sections)


def test_good_faith_sections_carry_the_language_the_course_compares():
    sections = {s.number: s for s in israel.parse_english(GENERAL_PART.read_text("utf-8"))}
    assert "good faith" in sections["12"].text
    assert "good faith" in sections["39"].text


def test_the_locators_are_hebrew_only_and_say_so():
    """A locator finds the law. It is not a translation source, and must not read as one.

    Israel publishes its legislation as structured open data and publishes no
    translation of it, so a registry that listed the Knesset's OData service
    beside L.S.I. would imply an English text that does not exist.
    """
    assert israel.LOCATORS
    for row in israel.LOCATORS:
        assert row.authority in israel.AUTHORITY_LADDER
        assert "English" in row.caveat
        assert row.key not in {s.key for s in israel.TRANSLATION_SOURCES}
