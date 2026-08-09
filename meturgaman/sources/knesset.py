"""Read the Knesset's own open data: which laws exist, and what each one is.

Why this is a separate module from ``israel``
---------------------------------------------
``israel`` is about English: which rendering of a statute a page may print, and
on whose authority. This is about Hebrew and about identity: which instrument
the Knesset actually enacted, under what official name, when it was published,
and whether it is still in force. The two answer different questions and fail in
different ways, so they are kept apart, one module per service, the way
``sefaria`` and ``hebcal`` are.

**Nothing here yields English.** Israel publishes its legislation as structured
open data and publishes no translation of it. That is worth stating rather than
leaving a reader to discover: a well-documented Hebrew API is not a substitute
for the authorized translation, and reaching for it as one is the mistake this
docstring exists to prevent.

What is verified to work, measured 2026-08-09
----------------------------------------------
The service is live, keyless, and returns JSON with ``$format=json``. Its
metadata document lists 38 entity sets, and the names are ``KNS_``-prefixed:
``KNS_IsraelLaw``, ``KNS_Law``, ``KNS_Bill``, ``KNS_Status`` and so on. A note
naming them ``Knesset_Bill`` or ``Knesset_Status`` is describing something else;
those return 404.

- **``KNS_IsraelLaw`` works and is the useful one.** Filtering on the name
  finds a statute and returns its official name, its publication date, its
  validity, its Knesset, and an ``IsraelLawID``. Searching for `חוק החוזים`
  returns the General Part (2000292), the Remedies Law (2000293), and both
  Standard Contracts Laws.
- **``KNS_IsraelLawBinding`` is populated, and empty for these statutes.** The
  entity exists and returns rows in general, and filtering it on either
  contracts statute returns nothing. So it does not answer "what amended this
  law", and the amendment stamps in the consolidated text on Hebrew Wikisource
  remain the working source for that. See ``israel.amended_sections``.
- **``KNS_DocumentIsraelLaw`` is empty outright.** Zero rows unfiltered, so it
  is not a route to the gazette PDFs. Those are reached directly from the ס״ח
  citation on ``fs.knesset.gov.il``.

Recording what is empty matters as much as recording what works. An entity that
exists, accepts a filter and returns nothing looks exactly like a correct query
for a law with no amendments, and the two are not the same fact.

Standard library only, through ``meturgaman.net``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from meturgaman.net import RateLimit, get_json

__all__ = [
    "ODATA",
    "CKAN",
    "IsraelLaw",
    "odata",
    "find_laws",
    "law_bindings",
    "ckan_search",
    "ckan_package",
]

ODATA = "https://knesset.gov.il/Odata/ParliamentInfo.svc"
CKAN = "https://data.gov.il/api/3/action"

#: The service publishes no rate limit. This is ordinary courtesy toward a
#: public body's server, and it costs nothing on the query sizes used here.
_LIMIT = RateLimit(5, 1.0, name="knesset-odata")


@dataclass(frozen=True)
class IsraelLaw:
    """One statute as the Knesset's own register names it.

    ``name`` is the official Hebrew name including its Hebrew-year suffix, which
    is the string to quote when citing the instrument, and which differs in
    punctuation from how Wikisource writes it. ``israel_law_id`` is the key every
    other entity in the register joins on.
    """

    israel_law_id: int
    name: str
    published: str = ""
    latest_publication: str = ""
    validity: str = ""
    knesset: int | None = None
    is_basic_law: bool = False

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "IsraelLaw":
        return cls(
            israel_law_id=row["IsraelLawID"],
            name=row.get("Name") or "",
            published=(row.get("PublicationDate") or "")[:10],
            latest_publication=(row.get("LatestPublicationDate") or "")[:10],
            validity=row.get("LawValidityDesc") or "",
            knesset=row.get("KnessetNum"),
            is_basic_law=bool(row.get("IsBasicLaw")),
        )


def odata(entity: str, **query: Any) -> list[dict[str, Any]]:
    """Query one entity set and return its rows.

    ``$format=json`` is supplied so a caller never has to remember it; without
    it the service answers in Atom XML and a JSON parse fails with a message
    about the wrong thing entirely.
    """
    query.setdefault("$format", "json")
    fetched = get_json(
        f"{ODATA}/{entity}",
        query,
        limiter=_LIMIT,
        service="knesset-odata",
        attribution="Knesset open data (knesset.gov.il).",
    )
    payload = fetched.payload
    if not isinstance(payload, dict) or "value" not in payload:
        raise LookupError(
            f"{entity} did not answer with an OData payload; the entity set may "
            f"not exist. The register uses KNS_ prefixes, so KNS_Bill rather "
            f"than Knesset_Bill."
        )
    return payload["value"]


def _escape(value: str) -> str:
    """OData quotes strings with single quotes and doubles an internal one."""
    return value.replace("'", "''")


def find_laws(name: str, *, limit: int = 20) -> list[IsraelLaw]:
    """Find statutes whose official name contains a phrase.

    The phrase is matched against the register's own Hebrew name, so a search
    has to use the Knesset's spelling rather than Wikisource's. They differ in
    the quotation marks around the Hebrew year, which is exactly the kind of
    difference that turns a real search into an empty one, so match on a
    distinctive fragment rather than on a whole title.

    >>> find_laws("")
    Traceback (most recent call last):
        ...
    ValueError: a search needs a phrase to look for
    """
    if not name.strip():
        raise ValueError("a search needs a phrase to look for")
    rows = odata(
        "KNS_IsraelLaw",
        **{
            "$filter": f"substringof('{_escape(name)}',Name)",
            "$top": str(limit),
        },
    )
    return [IsraelLaw.from_row(row) for row in rows]


def law_bindings(israel_law_id: int) -> list[dict[str, Any]]:
    """The register's binding rows for one statute, which are often none.

    An empty list means the register holds no binding for this law, which is
    NOT the same as the law having no amendments. Both contracts statutes this
    project works on return nothing here while carrying amendments the
    consolidated text records plainly. Use ``israel.amended_sections`` for
    amendment history, and treat this as supplementary.
    """
    return odata(
        "KNS_IsraelLawBinding",
        **{"$filter": f"IsraelLawID eq {int(israel_law_id)}", "$top": "100"},
    )


def ckan_search(query: str, *, rows: int = 10) -> list[dict[str, Any]]:
    """Search data.gov.il, which is an ordinary CKAN instance.

    Useful for finding which body publishes what. Searching it for English
    translations of legislation returns nothing, and that absence is a finding
    rather than a failed query.
    """
    fetched = get_json(
        f"{CKAN}/package_search",
        {"q": query, "rows": rows},
        limiter=_LIMIT,
        service="data.gov.il",
        attribution="data.gov.il, the Israeli open data portal.",
    )
    return fetched.payload.get("result", {}).get("results", [])


def ckan_package(identifier: str) -> dict[str, Any]:
    """One CKAN package with its resources, so a dataset's actual files are visible."""
    fetched = get_json(
        f"{CKAN}/package_show",
        {"id": identifier},
        limiter=_LIMIT,
        service="data.gov.il",
        attribution="data.gov.il, the Israeli open data portal.",
    )
    return fetched.payload.get("result", {})
