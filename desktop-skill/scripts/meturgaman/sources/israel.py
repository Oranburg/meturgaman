"""Read modern Israeli legislation, in Hebrew and in English translation.

Why this module exists
----------------------
Meturgaman was built for the classical library, where Sefaria holds the text and
names the edition. Modern Israeli statutes are the same problem wearing different
clothes: a Hebrew text that governs, a set of English translations of unequal
standing, and a reader who cannot tell them apart from the page. The rule that
governs the rest of the tool governs here without amendment.

    Never supply a text from memory. Fetch it, and name what you fetched.

Extended, because translation adds a second way to be wrong:

    Never supply a translation from memory, and never produce one silently.
    A translation carries the authority of whoever made it, and that authority
    has to travel with the words.

The authority ladder
--------------------
This is the part that is knowledge rather than code, and it is the reason the
module exists rather than a scraper. English renderings of Israeli law are not
interchangeable. In descending order of what a scholarly page may assert:

``enacted``
    The English is itself law, or is authentic treaty text. The CISG's English
    is authentic under its own Article 101; Israel's Schedule enacting it is
    Hebrew, so the two sit side by side and neither is a translation of the
    other. Print it as the text.

``authorized``
    *Laws of the State of Israel* (L.S.I.), the Ministry of Justice's own
    English, published by the Government Printing Office, volumes 1 to 45,
    covering 1948 to about 1989. **Authorized and not binding**: the Hebrew
    governs, and the volumes say so. This is what a footnote means by an
    official English text, and it is the tier this project's Israeli statutes
    need. Cite by volume and page: 25 L.S.I. 11.

``government``
    English published by an Israeli government body with no translator named:
    a ministry's own PDF, the Knesset's English pages. Real, and weaker than
    L.S.I. because nothing states who made it or that anyone reviewed it.

``commercial``
    A named commercial publisher. A.G. Publications (Arye Greenfield) has
    translated a large part of the corpus for decades; Nevo and Halachot carry
    English alongside their Hebrew. Unofficial, attributable, and citable when
    the translator is named on the page.

``scholarly``
    A translation printed in a law review, a treatise, or an encyclopaedia
    entry, with the translator named. A witness to what a section says.

``unattributed``
    A copy on the open web with no translator and no publisher. It may well be
    a faithful reproduction of an authorized text, and there is no way to tell
    from the copy. **A lead, not a source.** Use it to search with, to check a
    section number against, to decide whether a trip to the library is worth
    making. Do not print it as the law.

``assistant``
    Produced by a language model, here or anywhere. Marked as such on its own
    face, every time, without exception. **Never printed as the law**, and
    never allowed to fill a hole quietly. A hole that stays a hole is a good
    outcome; a hole filled with plausible English is the failure this whole
    module exists to prevent.

What this module does and does not do
-------------------------------------
It does not translate. It locates, fetches, parses, aligns and reconciles, and
every artifact it produces carries the tier of what it came from.

Two structural lessons are borrowed from LawOS, which solved the same problems
for American case law:

- **Two retrievals are two witnesses.** Where they disagree, report the
  disagreement rather than choosing. ``reconcile`` classifies every section as
  confirmed by two independent sources, held by one only, or disputed.
- **Pair on the key, never on position.** A bilingual layout built by walking
  two lists in parallel slips every later row the moment one row is short, and
  the slip is invisible. ``align`` joins on the section number and reports what
  has no counterpart.

Standard library only. Everything that leaves the machine goes through
``meturgaman.net``.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from meturgaman.net import RateLimit, get_bytes, get_json

__all__ = [
    "AUTHORITY_LADDER",
    "PRINTABLE_AS_LAW",
    "Statute",
    "TranslationSource",
    "EnglishSection",
    "Alignment",
    "SectionVerdict",
    "STATUTES",
    "TRANSLATION_SOURCES",
    "LOCATORS",
    "authority_rank",
    "statute",
    "sources_for",
    "fetch_hebrew",
    "fetch_gazette",
    "amended_sections",
    "parse_english",
    "align",
    "reconcile",
    "skeleton",
    "strip_running_heads",
]


#: The tiers, best first. Position in this tuple is the rank.
AUTHORITY_LADDER: tuple[str, ...] = (
    "enacted",
    "authorized",
    "government",
    "commercial",
    "scholarly",
    "unattributed",
    "assistant",
)

#: The tiers a page may print as the law itself, with a citation and no further
#: hedge. Everything below these prints only with its translator named in the
#: apparatus, and ``assistant`` does not print as law at all.
PRINTABLE_AS_LAW: frozenset[str] = frozenset({"enacted", "authorized"})

#: Wikisource is polite about volume but says nothing binding; this keeps a
#: burst of section fetches from looking like a crawler.
_WIKI_LIMIT = RateLimit(10, 1.0, name="wikisource")

_HEBREW = re.compile(r"[֐-׿]")


def authority_rank(tier: str) -> int:
    """Rank a tier, lower being better. An unknown tier ranks below every known one.

    >>> authority_rank("authorized") < authority_rank("unattributed")
    True
    >>> authority_rank("nonsense") == len(AUTHORITY_LADDER)
    True
    """
    try:
        return AUTHORITY_LADDER.index(tier)
    except ValueError:
        return len(AUTHORITY_LADDER)


# ---------------------------------------------------------------------------
# The registries
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Statute:
    """One Israeli statute, named the several ways the sources name it.

    ``lsi`` is the citation into *Laws of the State of Israel* where one exists.
    It is the single most useful field in this record, because it is what a
    librarian needs and what a footnote prints, and because a statute enacted
    after the series stopped has none, which is itself the answer to why the
    English cannot be authorized.
    """

    slug: str
    hebrew: str
    english: str
    year: int
    #: The Reshumot citation of the enacting instrument, as the statute prints it.
    gazette: str
    #: he.wikisource.org page title, for the consolidated current Hebrew.
    wikisource: str
    #: e.g. "25 L.S.I. 11". Empty when the series does not reach this statute.
    lsi: str = ""
    #: URLs of the enacting and amending gazette PDFs on the Knesset file server.
    gazette_urls: tuple[str, ...] = ()
    #: Amending instruments the consolidated text records, so a stale English
    #: column can be checked against them rather than assumed current.
    amendments: tuple[str, ...] = ()
    notes: str = ""


#: The statutes this project works on. Extend it; do not invent entries. Every
#: field here was read off an acquired source, not recalled.
STATUTES: dict[str, Statute] = {
    "sale-1968": Statute(
        slug="sale-1968",
        hebrew="חוק המכר, תשכ״ח–1968",
        english="Sale Law, 5728-1968",
        year=1968,
        gazette="ס״ח תשכ״ח, 98",
        wikisource="חוק_המכר",
        lsi="22 L.S.I. 107",
        amendments=("תיקון תשל״א (1971)", "פסיקת ריבית והצמדה תיקון מס׳ 9 (תשפ״ד)"),
        notes="Section 1 defines sale as conveyance against a price, which is how "
        "to confirm you are looking at the right statute in a volume.",
    ),
    "remedies-1970": Statute(
        slug="remedies-1970",
        hebrew="חוק החוזים (תרופות בשל הפרת חוזה), תשל״א–1970",
        english="Contracts (Remedies for Breach of Contract) Law, 5731-1970",
        year=1970,
        gazette="ס״ח תשל״א, 16",
        wikisource="חוק_החוזים_(תרופות_בשל_הפרת_חוזה)",
        lsi="25 L.S.I. 11",
        gazette_urls=(
            "https://fs.knesset.gov.il/7/law/7_lsr_211750.pdf",
            "https://fs.knesset.gov.il/25/law/25_lsr_3568695.pdf",
        ),
        amendments=("פסיקת ריבית והצמדה תיקון מס׳ 9 (תשפ״ד)",),
        notes="Section 3 is the entitlement to enforcement with four exceptions. "
        "It is the section a comparative course turns on, because the common law "
        "starts from damages and this starts from enforcement.",
    ),
    "contracts-general-1973": Statute(
        slug="contracts-general-1973",
        hebrew="חוק החוזים (חלק כללי), תשל״ג–1973",
        english="Contracts (General Part) Law, 5733-1973",
        year=1973,
        gazette="ס״ח תשל״ג, 118",
        wikisource="חוק_החוזים_(חלק_כללי)",
        lsi="27 L.S.I. 117",
        amendments=("תיקון מס׳ 2", "תיקון מס׳ 3"),
        notes="Sections 1 to 8 are formation, and no consideration requirement "
        "appears anywhere in them. That absence is the comparative point.",
    ),
    "int-sale-1999": Statute(
        slug="int-sale-1999",
        hebrew="חוק המכר (מכר טובין בין־לאומי), תש״ס–1999",
        english="Sale (International Sale of Goods) Law, 5760-1999",
        year=1999,
        gazette="ס״ח תש״ס, 6",
        wikisource="חוק_המכר_(מכר_טובין_בין-לאומי)",
        lsi="",
        notes="Enacts the CISG as a Schedule. The L.S.I. series stopped around "
        "1989, so there is no authorized English; but the Convention's own "
        "English is authentic text, tier `enacted`, which is stronger than any "
        "translation. Israel's Schedule covers Arts. 1-88 and 96.",
    ),
}


@dataclass(frozen=True)
class TranslationSource:
    """One place an English text of Israeli legislation can be had.

    ``reachable`` records what this machine can actually do, which is not the
    same question as whether the source exists. A subscription database is real
    and unreachable from a script; saying so is more useful than failing at it.
    """

    key: str
    name: str
    publisher: str
    #: One of AUTHORITY_LADDER.
    authority: str
    #: "open" | "subscription" | "print" | "manual"
    reachable: str
    url: str = ""
    coverage: str = ""
    #: What to actually do, in a sentence a person can follow.
    how: str = ""
    caveat: str = ""


TRANSLATION_SOURCES: tuple[TranslationSource, ...] = (
    TranslationSource(
        key="lsi",
        name="Laws of the State of Israel (L.S.I.)",
        publisher="Ministry of Justice / Government Printing Office, Jerusalem",
        authority="authorized",
        reachable="subscription",
        url="https://heinonline.org/",
        coverage="Volumes 1-45, roughly 1948 to 1989/90, plus a separate Penal Law "
        "volume (1977). Most laws and amendments, not all.",
        how="HeinOnline, Foreign and International Law collection. A university "
        "law-library subscription reaches it; a script does not. A print volume "
        "in a law library is equally good and sometimes faster.",
        caveat="Prints the statute AS ENACTED. Every amendment after the volume's "
        "year is absent, so a section may translate text that has since changed. "
        "Check the section against the amending instruments before setting it "
        "beside consolidated Hebrew.",
    ),
    TranslationSource(
        key="moj",
        name="Ministry of Justice English translations",
        publisher="State of Israel, Ministry of Justice",
        authority="government",
        reachable="manual",
        url="https://www.justice.gov.il/",
        coverage="Selected laws, with a long lag behind enactment.",
        how="Browse the ministry's site directly. gov.il refuses scripted "
        "requests from outside Israel, so this is a browser job.",
        caveat="Nothing states who translated a given file or whether it was "
        "reviewed, which is what separates this tier from L.S.I.",
    ),
    TranslationSource(
        key="knesset-en",
        name="Knesset English pages",
        publisher="The Knesset",
        authority="government",
        reachable="manual",
        url="https://main.knesset.gov.il/EN/",
        coverage="Basic Laws and constitutional material, well; ordinary "
        "legislation, barely.",
        how="Browse. Useful for Basic Laws and for nothing in private law.",
    ),
    TranslationSource(
        key="ag-publications",
        name="A.G. Publications (Arye Greenfield)",
        publisher="A.G. Publications, Haifa",
        authority="commercial",
        reachable="print",
        coverage="A large share of the corpus, in periodically updated "
        "consolidations, which is the thing L.S.I. is not.",
        how="Purchase, or find in a law library. Its consolidations are the best "
        "answer to the as-enacted problem when currency matters more than "
        "official standing.",
        caveat="Unofficial. Cite the translator.",
    ),
    TranslationSource(
        key="nevo",
        name="Nevo",
        publisher="Nevo Publishing",
        authority="commercial",
        reachable="subscription",
        url="https://www.nevo.co.il/",
        coverage="The working database of Israeli practice; some English.",
        how="Israeli institutional subscription. Refuses requests from this "
        "machine outright (HTTP 403).",
    ),
    TranslationSource(
        key="scholarly",
        name="A translation printed in scholarship",
        publisher="various",
        authority="scholarly",
        reachable="open",
        coverage="Sections that matter to an argument somebody published.",
        how="Israel Law Review, the International Encyclopaedia of Laws country "
        "monographs, treatises. Search the section number with a phrase from the "
        "Hebrew heading.",
        caveat="A witness that a section says something like that. It is not the "
        "text, and a piece that paraphrases while looking like a quotation is the "
        "commonest way a wrong sentence gets into a footnote.",
    ),
    TranslationSource(
        key="web-copy",
        name="An unattributed copy on the open web",
        publisher="unnamed",
        authority="unattributed",
        reachable="open",
        coverage="Scattered, and much of it a decades-old rekeying of something.",
        how="Fetch it, hash it, keep it as a lead. It is good for confirming a "
        "section number, a chapter division, or that a trip to the library will "
        "find what you expect.",
        caveat="Never print it as the law. Where two unattributed copies agree "
        "word for word they are usually one copy twice, not two witnesses.",
    ),
)


#: Where to FIND an Israeli law and its amendment history, as distinct from
#: where to find an English text of it. These answer "which instrument, which
#: gazette page, amended when", and they answer it in Hebrew. None of them
#: yields English, which is worth stating plainly: the Israeli state publishes
#: its legislation as structured open data and publishes no translation of it.
LOCATORS: tuple[TranslationSource, ...] = (
    TranslationSource(
        key="knesset-odata",
        name="Knesset parliamentary OData service",
        publisher="The Knesset",
        authority="government",
        reachable="open",
        url="https://knesset.gov.il/Odata/ParliamentInfo.svc/",
        coverage="Every law from the Mandate period onward, with its type, its "
        "Knesset, its bills and its amendments, as queryable entities: KNS_Law, "
        "KNS_LawBinding, KNS_Bill and their relations.",
        how="Plain OData over HTTPS, no key. `KNS_Law()?$top=2&$format=json` "
        "returns JSON. Listed on Israel's open-data portal at data.gov.il as "
        "the accessible parliamentary database.",
        caveat="Hebrew only, and metadata rather than enacted text. It is the "
        "fast way to establish WHICH instrument amended a statute and when, "
        "which is the input the drift check needs. It supplies no English.",
    ),
    TranslationSource(
        key="data-gov-il",
        name="data.gov.il, the Israeli open data portal",
        publisher="State of Israel",
        authority="government",
        reachable="open",
        url="https://data.gov.il/api/3/action/package_search",
        coverage="A CKAN catalogue. The legislation-bearing packages are `548` "
        "(the laws as enacted) and `odata` (the parliamentary service above). "
        "Most other hits are a single ministry's own list.",
        how="CKAN API, no key: `package_search?q=...` then `package_show?id=...` "
        "for a package's resources.",
        caveat="A catalogue of Hebrew datasets. Searching it for English "
        "translations returns nothing, which is itself the finding.",
    ),
)


def statute(slug: str) -> Statute:
    """Look up a statute, refusing rather than guessing at a near miss.

    The refusal is a plain `LookupError` rather than the `KeyError` a dict
    lookup would raise, and the difference is visible to a user. The CLI treats
    a bare `KeyError` as an internal fault and lets it print a traceback, on the
    ground that an internal fault should not be dressed up as the user's
    mistake. A mistyped slug is the user's mistake, and it deserves the list of
    real ones instead.
    """
    try:
        return STATUTES[slug]
    except KeyError:
        known = ", ".join(sorted(STATUTES))
        raise LookupError(
            f"no statute {slug!r} in the registry; known: {known}"
        ) from None


def sources_for(slug: str) -> list[TranslationSource]:
    """Every translation source worth trying for one statute, best tier first.

    A statute the L.S.I. series does not reach does not get an L.S.I. row, which
    is how the registry answers "why is there no official English" without
    anybody having to remember that the series stopped in 1989.
    """
    law = statute(slug)
    rows = [
        source
        for source in TRANSLATION_SOURCES
        if not (source.key == "lsi" and not law.lsi)
    ]
    return sorted(rows, key=lambda s: (authority_rank(s.authority), s.key))


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------


@dataclass
class HebrewText:
    """A consolidated Hebrew text, with the revision that produced it."""

    page: str
    wikitext: str
    revision_id: int
    revision_timestamp: str
    url: str
    licence: str = "CC BY-SA 4.0 (Hebrew Wikisource)"
    authority: str = "unofficial working text"

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.wikitext.encode("utf-8")).hexdigest()


def fetch_hebrew(slug_or_page: str, *, use_cache: bool = True) -> HebrewText:
    """Fetch the consolidated Hebrew of a statute from he.wikisource.

    The revision id and its timestamp come back with the text, because a wiki
    page is a moving target and a citation to one without a revision is a
    citation to whatever it says today. This is a *witness*, not the enacted
    text: the enacted text is the Reshumot gazette, and the two answer different
    questions. Wikisource answers "what does the law say now"; the gazette
    answers "what was enacted, and when".
    """
    page = STATUTES[slug_or_page].wikisource if slug_or_page in STATUTES else slug_or_page
    fetched = get_json(
        "https://he.wikisource.org/w/api.php",
        {
            "action": "query",
            "format": "json",
            "prop": "revisions",
            "rvprop": "content|ids|timestamp",
            "rvslots": "main",
            "formatversion": "2",
            "titles": page.replace("_", " "),
        },
        limiter=_WIKI_LIMIT,
        service="he.wikisource",
        attribution="Hebrew Wikisource, CC BY-SA 4.0.",
        use_cache=use_cache,
    )
    pages = fetched.payload.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        raise LookupError(f"he.wikisource has no page {page!r}")
    revision = pages[0]["revisions"][0]
    return HebrewText(
        page=pages[0]["title"],
        wikitext=revision["slots"]["main"]["content"],
        revision_id=revision["revid"],
        revision_timestamp=revision["timestamp"],
        url=f"https://he.wikisource.org/wiki/{page}",
    )


#: How the ספר החוקים הפתוח project opens a section, and how it records that the
#: section has been amended: `{{ח:סעיף|11|heading|תיקון: תשפ״ד}}`.
_SECTION_TEMPLATE = re.compile(r"\{\{ח:סעיף\|(?P<number>[^|}]+)\|(?P<heading>[^|}]*)(?P<rest>[^}]*)\}\}")
_AMENDED = re.compile(r"תיקון")


def amended_sections(wikitext: str) -> dict[str, str]:
    """Which sections have been amended since enactment, and by what.

    This is the answer to the question that decides whether an English text may
    be set beside the Hebrew. An authorized translation prints the law **as
    enacted**; a consolidated Hebrew text is current. Where the two describe the
    same section, the pair is honest. Where the section has been amended in
    between, the page would print two different laws and call one a translation
    of the other.

    The consolidated text already knows the answer and states it: the open
    statute-book project stamps each amended section with the instrument that
    amended it. Reading that beats reasoning about it, and beats the guess that
    an interest-and-linkage amendment "probably" touched only the damages
    provisions. On the Remedies Law it touched exactly one section, § 11, and
    the four sections a comparative course prints are untouched. That is a fact
    with a source rather than a likelihood.

    Returns a mapping of section number to the amendment note the source prints.
    A section absent from the mapping carries no amendment marker.
    """
    found: dict[str, str] = {}
    for match in _SECTION_TEMPLATE.finditer(wikitext):
        rest = match.group("rest")
        if _AMENDED.search(rest):
            found[match.group("number").strip()] = rest.strip("| ").strip()
    return found


def fetch_gazette(url: str) -> tuple[bytes, str]:
    """Fetch a Reshumot PDF and return it with its digest.

    The digest is the point. A gazette PDF is a scan with an OCR layer, so the
    bytes are the citable thing and the extracted text is not; recording the
    hash means a later session can prove it is holding the same file rather
    than hoping.
    """
    payload = get_bytes(url, service="fs.knesset.gov.il")
    return payload, hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Parsing a delivered English text
# ---------------------------------------------------------------------------

#: A section opens at the left margin with its number and a period: `3.`, `12A.`
#: An optional section sign is allowed in front, because a person transcribing
#: printed pages writes `§ 9.` and a printed volume does not. Requiring the bare
#: form would refuse the exact shape a delivery is asked to arrive in.
_SECTION_OPEN = re.compile(
    r"^[ \t]*(?:§[ \t]*)?(?P<number>\d{1,3}[A-Za-z]{0,2})\.[ \t]+(?=\S)", re.M
)

#: A marginal heading, printed in its own column and therefore landing on its
#: own line when the columns are flattened. Short, no terminal period, no
#: sentence punctuation, and not itself a numbered opening.
_MARGINAL = re.compile(r"^[ \t]*(?P<heading>[A-Z][A-Za-z’'()\- ]{2,48})[ \t]*$")

#: Below this, an indent is paragraph indentation rather than a column boundary.
_MIN_BODY_COLUMN = 8

#: A line that carries a marginal entry: text starting hard against the left
#: edge, then a run of spaces wide enough to be a column gutter rather than
#: sentence spacing, then the body. The marginal entry itself is a fragment of a
#: heading, so it holds no sentence punctuation and stays short.
_MARGIN_LINE = re.compile(r"^([^\s][^\s]{0,2}[A-Za-z0-9'’()\-.,/ ]{0,27}?)\s{3,}(?=\S)")

_NOISE = re.compile(
    r"^\s*(?:pd4ml[^\n]*|Chapter\s+[A-Z][a-z]+\s*[:：].*|Article\s+[A-Z][a-z]+\s*[:：].*)\s*$",
    re.M | re.I,
)


@dataclass
class EnglishSection:
    """One section of a delivered English text, as delivered.

    ``marginal`` holds a line that *looks* like the section's marginal heading
    without asserting that it is one. Israeli statutes typeset the number and
    the heading in separate columns, and every flattening of those columns
    puts the heading somewhere a naive read will misfile it. The gazette PDFs
    interleave them out of reading order in Hebrew, and an HTML-to-PDF copy of
    an English text drops the heading *after* the body it belongs to. Reporting
    the candidate and refusing to merge it is the only honest option, because
    silently attaching a heading to the wrong section is undetectable later.
    """

    number: str
    text: str
    marginal: str = ""
    #: Words rejoined across a typesetter's line-end hyphen, so a person can
    #: read down the list and catch the one that carried a real hyphen.
    rejoined: tuple[str, ...] = ()

    @property
    def sha256(self) -> str:
        return hashlib.sha256(skeleton(self.text).encode("utf-8")).hexdigest()


def _strip_noise(text: str) -> str:
    return _NOISE.sub("", text)


def strip_running_heads(text: str, dropped: list[str] | None = None) -> str:
    """Remove the running head a printed page repeats, and say what was removed.

    A journal prints its own name across the top of every page and the volume in
    the corner, and a scan carries both into the middle of whatever section
    spans the page break. `ISRAEL LAW REVIEW` landed inside Remedies § 5 that
    way, which is a publisher's furniture printed as a sentence of the statute.

    No journal is named here, because naming journals would only work for the
    journals somebody thought of. A running head is recognized by what makes it
    one: it is short, it is set in capitals, it carries no sentence, and it
    comes back on the facing page. Statutory prose does none of those things.

    Matching has to be loose, because the head is the part of a scan the OCR
    gets worst: the same line reads `[Is.LR. Vol. B.` on one page and
    `[Is.L.R. Vol. 8.` on the next. Two lines are the same head when their first
    eighteen letters agree, which survives a mangled volume number and a
    bracket read as a digit.

    What comes out is appended to ``dropped`` when a list is given, because
    material silently removed and material never detected look identical
    downstream.
    """
    lines = text.split("\n")
    keys = [_running_key(line) for line in lines]
    counts: dict[str, int] = {}
    for key in keys:
        if key:
            counts[key] = counts.get(key, 0) + 1

    kept: list[str] = []
    for line, key in zip(lines, keys):
        if key and counts[key] >= 2:
            if dropped is not None:
                dropped.append(line.strip())
            kept.append("")
        else:
            kept.append(line)
    return "\n".join(kept)


def _running_key(line: str) -> str:
    """A loose signature for a line that could be a running head, else empty.

    The guards do the work. A line long enough to be prose, or set mostly in
    lower case, or ending in a sentence's own punctuation, is not a head, and
    returning nothing for it means it is never counted and never dropped.
    """
    stripped = line.strip()
    # The ceiling is generous because a running head often carries the folio as
    # well, and `288  ISRAEL LAW REVIEW  [Is.L.R. Vol. 9.` is 90 characters. A
    # tighter limit let exactly that one line through, into the middle of a
    # section, while its three siblings were removed. The uppercase test below
    # is what actually separates a head from prose.
    if not 8 <= len(stripped) <= 100:
        return ""
    if stripped.endswith((";", ":", ",")):
        return ""
    letters = [character for character in stripped if character.isalpha()]
    if len(letters) < 8:
        return ""
    # Running heads are set in capitals or small capitals. Prose is not.
    if sum(1 for character in letters if character.isupper()) < len(letters) * 0.8:
        return ""
    # A page's first line cannot be the statute opening a section.
    if _SECTION_OPEN.match(stripped):
        return ""
    return "".join(letters[:18]).lower()


def detect_margin_column(text: str) -> int | None:
    """Find the column where the body begins, when a page is set in two columns.

    Israeli statutes print the section's heading in a narrow left column beside
    the body, and every flattening of that layout damages the text in a
    different way. `pdftotext -layout` is the honest one: it keeps the columns
    apart by padding with spaces, so the marginal heading sits at the left of
    the same line as the body text it labels. Read as prose, that produces

        Remedies of      2. Where a contract has been broken, the injured
        injured          party is entitled to claim its enforcement or to
        party.           rescind the contract...

    where a naive parser finds no section opening at all (the line does not
    begin with a number) and, worse, splices the heading's own words into the
    statute. The columns have to be separated before anything else happens.

    The boundary is measured rather than assumed. Indents cluster: the marginal
    column starts at zero and the body at a single column that every body line
    shares. The lowest indent at or beyond `_MIN_BODY_COLUMN` is that column.

    Returns None when the page is not two-column, and also when the boundary it
    measured would cut through a word, because a boundary that splits a word is
    the one case where separating the columns would itself lose text.

    >>> detect_margin_column("Definitions.  1. In this Law.\\n              Text here.\\n") is None
    True
    """
    lines = [line.rstrip() for line in text.split("\n") if line.strip()]
    if len(lines) < 6:
        return None

    widths = [match.end(1) for match in map(_MARGIN_LINE.match, lines) if match]
    indented = [
        line for line in lines if len(line) - len(line.lstrip()) >= _MIN_BODY_COLUMN
    ]

    # Two columns means a real population on each side, not a stray indent: some
    # lines carrying a marginal entry, and some carrying body text alone.
    if len(widths) < len(lines) * 0.08 or len(indented) < len(lines) * 0.2:
        return None
    return max(widths)


def split_columns(text: str, column: int) -> tuple[str, str]:
    """Cut a two-column page into its marginal column and its body.

    The cut is made per line, at the run of spaces that actually separates the
    columns, rather than at one fixed column for the whole page. A fixed column
    looks right until the numbering reaches double digits: a printer sets `1.`
    and `15.` to end at the same place, so the two-digit number begins four
    columns earlier and any single boundary that clears the marginal headings
    slices through it. The gap is where the columns really part, on every line.

    Only a line that begins at the very left carries a marginal entry. Body
    lines are indented past the marginal column by construction, so they are
    never searched for one, and a wide space inside a sentence cannot be
    mistaken for the boundary.

    Both halves come back. The marginal column is evidence about the headings
    and is kept for that, never merged into the body: a heading is the
    publisher's label for a section, and the statute is what the Knesset
    enacted, and the difference matters to a reader who quotes the page.
    """
    margins: list[str] = []
    bodies: list[str] = []
    for line in text.split("\n"):
        stripped = line.rstrip()
        match = _MARGIN_LINE.match(line)
        if match and match.end(1) <= column:
            margins.append(match.group(1).strip())
            bodies.append(line[match.end():])
        elif stripped and line[0] != " " and len(stripped) <= column:
            # A marginal entry with no body beside it, because the heading is
            # taller than the section's first lines. It matches no gap, having
            # nothing to its right, and without this branch it falls through to
            # the body and prints a fragment of a heading as the statute's own
            # words. `requires` did exactly that inside Remedies § 5.
            margins.append(stripped)
            bodies.append("")
        else:
            margins.append("")
            bodies.append(stripped)
    return "\n".join(margins), "\n".join(bodies)


def parse_english(
    text: str, *, furniture: list[str] | None = None
) -> list[EnglishSection]:
    """Split a delivered English statute into numbered sections.

    Nothing is normalized away that a reader would notice: subsection lettering,
    internal quotation marks and the dash conventions of the source all survive,
    because the delivered text is evidence and a tidied copy of evidence is a
    different document. Only conversion furniture is dropped, and only shapes
    that are furniture beyond argument: an HTML-to-PDF converter's watermark,
    and a running chapter or article banner repeated on every page.

    >>> sections = parse_english('1. First thing.\\n\\n2. Second thing.\\n')
    >>> [s.number for s in sections]
    ['1', '2']
    """
    # A form feed is a page boundary, and therefore a line boundary. Left in
    # place it prefixes the first section on each page, which no left-margin
    # pattern then matches: in the Remedies retrieval that hid sections 6, 9,
    # 12 and 23, four of twenty-five, with no error and no gap a reader of the
    # output could see. Every page break becomes a newline before anything
    # looks for a margin.
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n")
    cleaned = _strip_noise(cleaned)
    cleaned = strip_running_heads(cleaned, furniture)

    # Separate the columns before looking for anything, when there are two. The
    # marginal column is carried alongside and joined back to each section by
    # the line the section opens on, so a heading reaches the section it labels
    # rather than the one it happens to sit near.
    margin_by_line: dict[int, str] = {}
    column = detect_margin_column(cleaned)
    margin_lines: list[str] = []
    if column is not None:
        margin_text, cleaned = split_columns(cleaned, column)
        margin_lines = margin_text.split("\n")

    opens = list(_SECTION_OPEN.finditer(cleaned))

    if margin_lines:
        # A heading wraps down the lines of the section it labels, so each
        # heading is the run of marginal lines starting on the line its section
        # opens on. The run ends at a blank marginal line **or at the line the
        # next section opens on**, whichever comes first. Without that second
        # boundary, two sections whose headings touch merge into one: § 1 of the
        # Contracts (General Part) Law came back labelled `Mode of making
        # Contract Offer`, having swallowed § 2's heading whole.
        open_lines = {cleaned.count("\n", 0, match.start()) for match in opens}
        for index in sorted(open_lines):
            run: list[str] = []
            cursor = index
            while cursor < len(margin_lines) and margin_lines[cursor].strip():
                if cursor > index and cursor in open_lines:
                    break
                run.append(margin_lines[cursor].strip())
                cursor += 1
            if run:
                margin_by_line[index] = _join_marginal(run)
    sections: list[EnglishSection] = []
    for index, match in enumerate(opens):
        start = match.end()
        end = opens[index + 1].start() if index + 1 < len(opens) else len(cleaned)
        body = cleaned[start:end]

        marginals: list[str] = []
        leading_heading = ""
        lines = body.split("\n")

        # A heading can also lead. Somebody transcribing printed pages writes
        # `§ 9. Time of delivery` and then the section's text, which is the
        # shape a delivery is asked to arrive in. It is taken as a heading only
        # when it stands alone on the opening line, looks like a heading rather
        # than like prose, and the section has further text; so `1. (a) In this
        # law -` keeps its opening, because a parenthesis is not a heading and
        # losing the first line of a section is worse than reporting no heading
        # at all.
        if len(lines) > 1 and any(line.strip() for line in lines[1:]):
            leading = _MARGINAL.match(lines[0])
            if leading:
                leading_heading = leading.group("heading").strip()
                lines = lines[1:]

        while lines:
            while lines and not lines[-1].strip():
                lines.pop()
            if not lines:
                break
            candidate = _MARGINAL.match(lines[-1])
            if not candidate:
                break
            # Never empty a section to harvest a heading from it. A short
            # section whose whole body is one heading-shaped line (`4.
            # Conditions on enforcement`) would otherwise lose its only text and
            # leave a heading behind, which is text loss dressed as structure.
            if not any(line.strip() for line in lines[:-1]):
                break
            marginals.append(candidate.group("heading").strip())
            lines.pop()
        body = "\n".join(lines)

        opening_line = cleaned.count("\n", 0, match.start())
        body, rejoined = _dehyphenate(body)
        sections.append(
            EnglishSection(
                number=match.group("number"),
                text=_tidy(body),
                # Strongest evidence first: a heading in the marginal column of
                # the line the section opens on, then one on the number's own
                # line, then one that merely trails the body.
                marginal=margin_by_line.get(opening_line)
                or leading_heading
                or (marginals[-1] if marginals else ""),
                rejoined=tuple(rejoined),
            )
        )
    return sections


def _join_marginal(pieces: Sequence[str]) -> str:
    """Rejoin a marginal heading that wrapped across the lines of its column.

    The column is narrow, so a heading breaks mid-word and the typesetter
    hyphenates: `Compen-` / `sation` / `for` / `non-pecuniary` / `damage.` is
    one heading. A piece ending in a hyphen joins the next without a space, and
    every other join takes one.
    """
    out = ""
    for piece in pieces:
        if out.endswith("-"):
            out = out[:-1] + piece
        elif out:
            out += " " + piece
        else:
            out = piece
    return out.rstrip(".,").strip()


#: A word the typesetter broke across a line: `re-` at the end of one line and
#: `quires` at the start of the next. The continuation must be lower case, so a
#: hyphenated proper noun at a line end is left alone.
_SOFT_HYPHEN = re.compile(r"(?P<head>\w+)-[ \t]*\n(?:[ \t]*\n)*[ \t]*(?P<tail>[a-z]\w*)")


def _dehyphenate(body: str) -> tuple[str, list[str]]:
    """Rejoin words the typesetter broke at a line end, and say which ones.

    A printed page hyphenates to justify a line, and a reader of that page reads
    `requires`, not `re- quires`. Rejoining restores the word rather than
    altering it, which is why this is done at all.

    It cannot be done blind. A word that genuinely carries a hyphen, broken at
    exactly a line end, is indistinguishable from a soft hyphen by shape alone,
    and joining that one changes the statute's words. So every join is recorded
    and travels with the section: a list of a dozen rejoined words is something
    a person can read down in a few seconds, and a silent transformation of
    somebody's statute is not.
    """
    joined: list[str] = []

    def repair(match: re.Match[str]) -> str:
        word = match.group("head") + match.group("tail")
        joined.append(word)
        return word

    return _SOFT_HYPHEN.sub(repair, body), joined


def _tidy(body: str) -> str:
    """Collapse the line wrapping a converter imposed, keeping paragraph breaks."""
    paragraphs = [
        " ".join(part.split()) for part in re.split(r"\n[ \t]*\n", body) if part.strip()
    ]
    return "\n\n".join(paragraphs).strip()


# ---------------------------------------------------------------------------
# Aligning Hebrew against English
# ---------------------------------------------------------------------------


@dataclass
class Alignment:
    """The result of joining two texts on the section number.

    ``ok`` is false whenever anything failed to pair. A build that sets a
    bilingual page should treat that as fatal rather than as a warning: the
    fallback that prints one column and leaves the other empty is exactly how a
    single short row silently shifts every row after it.
    """

    matched: list[str] = field(default_factory=list)
    hebrew_only: list[str] = field(default_factory=list)
    english_only: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.hebrew_only and not self.english_only

    def report(self) -> str:
        lines = [f"paired {len(self.matched)} section(s) on the section number"]
        if self.hebrew_only:
            lines.append(
                f"HEBREW WITH NO ENGLISH ({len(self.hebrew_only)}): "
                + ", ".join(self.hebrew_only)
            )
        if self.english_only:
            lines.append(
                f"ENGLISH WITH NO HEBREW ({len(self.english_only)}): "
                + ", ".join(self.english_only)
            )
        if self.ok:
            lines.append("every section has a counterpart")
        return "\n".join(lines)


def _normalize_number(value: str) -> str:
    """`3`, `3.`, `03`, `§ 3`, `סעיף 3` all name the same section."""
    text = unicodedata.normalize("NFKC", str(value)).strip()
    text = re.sub(r"^(?:§|סעיף|section|sec\.?)\s*", "", text, flags=re.I)
    text = text.rstrip(".").strip()
    match = re.match(r"^0*(\d+)\s*([A-Za-zא-ת]{0,2})$", text)
    if match:
        return match.group(1) + match.group(2).upper()
    return text


def align(
    hebrew_numbers: Iterable[str], english: Sequence[EnglishSection]
) -> Alignment:
    """Join Hebrew section numbers to parsed English sections, on the number.

    >>> a = align(['1', '2'], parse_english('1. One.\\n\\n2. Two.\\n'))
    >>> a.ok
    True
    >>> align(['1', '2', '3'], parse_english('1. One.\\n')).hebrew_only
    ['2', '3']
    """
    he = [_normalize_number(number) for number in hebrew_numbers]
    en = {_normalize_number(section.number) for section in english}
    he_set = set(he)
    return Alignment(
        matched=[number for number in he if number in en],
        hebrew_only=[number for number in he if number not in en],
        english_only=sorted(en - he_set, key=_sort_key),
    )


def _sort_key(number: str) -> tuple[int, str]:
    match = re.match(r"^(\d+)(.*)$", number)
    return (int(match.group(1)), match.group(2)) if match else (10**6, number)


# ---------------------------------------------------------------------------
# Reconciling two English witnesses
# ---------------------------------------------------------------------------


def skeleton(text: str) -> str:
    """Reduce English prose to what two faithful copies must share.

    Case, whitespace, and the several dashes and quotation marks a rekeying
    swaps for one another are apparatus rather than substance; two copies that
    differ only there are the same text badly typed. Anything else that differs
    is a difference in the words, and this module reports it rather than
    resolving it.

    >>> skeleton('The “injured party” — a person.') == skeleton('the "injured party" - a person.')
    True
    """
    text = unicodedata.normalize("NFKC", text)
    for source, target in (
        ("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
        ("–", "-"), ("—", "-"), ("−", "-"), ("‐", "-"),
        (" ", " "),
    ):
        text = text.replace(source, target)
    return " ".join(text.lower().split())


@dataclass
class SectionVerdict:
    """What the witnesses to one section jointly establish.

    ``status`` is LawOS's vocabulary, because the problem is the same one:

    ``confirmed``
        Two or more independent witnesses give the same words. Independence is
        the load the caller carries: two mirrors of one file are one witness.
    ``single``
        One witness only. Usable, and the record says so.
    ``disputed``
        The witnesses differ in the words. Report the difference; do not pick.
        A translation dispute is often a real one, because two translators of
        `אכיפה` may write enforcement and specific performance and mean
        different things to a common-law reader.
    """

    number: str
    status: str
    best_authority: str
    witnesses: dict[str, str] = field(default_factory=dict)

    @property
    def printable_as_law(self) -> bool:
        return self.best_authority in PRINTABLE_AS_LAW


def reconcile(
    witnesses: dict[str, tuple[str, Sequence[EnglishSection]]]
) -> list[SectionVerdict]:
    """Compare several English witnesses section by section.

    ``witnesses`` maps a witness key to its authority tier and its parsed
    sections. The verdicts come back in section order, and each carries every
    witness's own words so a person can read the disagreement rather than being
    told about it.
    """
    by_number: dict[str, dict[str, str]] = {}
    tiers: dict[str, str] = {}
    for key, (authority, sections) in witnesses.items():
        tiers[key] = authority
        for section in sections:
            by_number.setdefault(_normalize_number(section.number), {})[key] = section.text

    verdicts: list[SectionVerdict] = []
    for number in sorted(by_number, key=_sort_key):
        texts = by_number[number]
        best = min(
            (tiers[key] for key in texts), key=authority_rank, default="assistant"
        )
        if len(texts) == 1:
            status = "single"
        elif len({skeleton(value) for value in texts.values()}) == 1:
            status = "confirmed"
        else:
            status = "disputed"
        verdicts.append(
            SectionVerdict(
                number=number, status=status, best_authority=best, witnesses=dict(texts)
            )
        )
    return verdicts
