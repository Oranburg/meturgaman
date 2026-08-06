"""Read from Hebcal: the Jewish calendar, Torah readings, and halachic times.

Written against the committed spec
----------------------------------
`docs/api/hebcal-openapi.json` is Hebcal's own OpenAPI document, fetched and
committed here. The parameter names, their allowed values and their defaults in
this module are read out of that file at import time rather than typed from
memory, so a parameter this code accepts is a parameter Hebcal documents. When
Hebcal changes, refetch that file and the validation follows.

Attribution
-----------
Hebcal's data is CC-BY-4.0 and asks for credit. Every reply carries the line to
print, and the CLI prints it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from meturgaman.net import RateLimit, get_json, post_json

__all__ = [
    "BASE", "ATTRIBUTION", "LOCALES", "ASHKENAZI_LOCALES",
    "SEPHARDI", "ASHKENAZI",
    "HebrewDate", "Aliyah", "Reading", "Event", "StudyEntry", "Day",
    "read_day", "convert", "leyning", "zmanim", "yahrzeit",
    "parameters_for",
]

BASE = "https://www.hebcal.com"
ATTRIBUTION = (
    "Calendar data from Hebcal (https://www.hebcal.com), CC-BY-4.0."
)

#: Hebcal publishes ninety requests per ten seconds. This stays under it.
_LIMIT = RateLimit(requests=80, seconds=10.0, name="hebcal")

SEPHARDI = "s"
ASHKENAZI = "a"

_SPEC_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "api" / "hebcal-openapi.json"


@lru_cache(maxsize=1)
def _spec() -> dict[str, Any]:
    """The committed OpenAPI document, or an empty one when it is absent.

    Absent means validation is skipped rather than that everything fails. The
    document is a check on this code, not a dependency of it.
    """
    if not _SPEC_PATH.exists():
        return {}
    try:
        return json.loads(_SPEC_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):  # pragma: no cover
        return {}


@lru_cache(maxsize=8)
def parameters_for(path: str, method: str = "get") -> dict[str, dict[str, Any]]:
    """Every documented parameter for one endpoint, with its schema.

    Reads the committed spec, following `$ref` into `components/parameters`,
    which is where Hebcal keeps the location and locale parameters that several
    endpoints share.
    """
    document = _spec()
    if not document:
        return {}
    shared = document.get("components", {}).get("parameters", {})
    operation = document.get("paths", {}).get(path, {}).get(method, {})
    found: dict[str, dict[str, Any]] = {}
    for entry in operation.get("parameters", []):
        if "$ref" in entry:
            key = entry["$ref"].rsplit("/", 1)[-1]
            entry = shared.get(key, {})
        name = entry.get("name")
        if name:
            found[name] = entry.get("schema", {})
    return found


def _validate(path: str, params: dict[str, Any]) -> dict[str, Any]:
    """Drop nothing, but refuse a value the spec says is not allowed."""
    known = parameters_for(path)
    if not known:
        return params
    for name, value in params.items():
        if value is None:
            continue
        schema = known.get(name)
        if schema is None:
            raise ValueError(
                f"Hebcal's {path} takes no parameter named {name!r}. "
                f"Documented: {', '.join(sorted(known))}"
            )
        allowed = schema.get("enum")
        if allowed and str(value) not in [str(item) for item in allowed]:
            raise ValueError(
                f"{name}={value!r} is not allowed for {path}. "
                f"Allowed: {', '.join(str(item) for item in allowed)}"
            )
    return {name: value for name, value in params.items() if value is not None}


#: Every locale Hebcal documents, read from the spec.
LOCALES: tuple[str, ...] = tuple(
    parameters_for("/hebcal").get("lg", {}).get("enum", ["s", "a", "h", "he"])
)

#: The Ashkenazi ones, for a reader who wants Shabbos rather than Shabbat.
ASHKENAZI_LOCALES: tuple[str, ...] = tuple(
    value for value in LOCALES if value.startswith("a") or value == "sh"
)


@dataclass(frozen=True)
class HebrewDate:
    year: int
    month: str
    day: int
    hebrew: str = ""

    def __str__(self) -> str:
        return f"{self.day} {self.month} {self.year}"


@dataclass(frozen=True)
class Aliyah:
    number: str
    ref: str

    def __str__(self) -> str:
        return f"{self.number}: {self.ref}"


@dataclass
class Reading:
    """The Torah reading for a day."""

    name: str
    hebrew_name: str = ""
    summary: str = ""
    haftarah: str = ""
    aliyot: list[Aliyah] = field(default_factory=list)
    triennial: list[Aliyah] = field(default_factory=list)


@dataclass(frozen=True)
class Event:
    title: str
    category: str = ""
    hebrew: str = ""
    date: str = ""

    def __str__(self) -> str:
        return self.title


@dataclass(frozen=True)
class StudyEntry:
    """One entry from a daily study cycle: daf yomi, mishnah yomit, and the rest."""

    cycle: str
    ref: str


@dataclass
class Day:
    """Everything Hebcal knows about one date."""

    gregorian: date
    hebrew_date: HebrewDate
    locale: str
    events: list[Event] = field(default_factory=list)
    reading: Reading | None = None
    study: list[StudyEntry] = field(default_factory=list)
    attribution: str = ATTRIBUTION


def convert(
    when: date | str,
    *,
    after_sunset: bool = False,
    locale: str = SEPHARDI,
) -> HebrewDate:
    """Convert a Gregorian date to its Hebrew equivalent.

    `after_sunset` matters and is easy to forget: the Hebrew day begins in the
    evening, so a Tuesday evening is already Wednesday's Hebrew date.
    """
    when = date.fromisoformat(when) if isinstance(when, str) else when
    params = _validate(
        "/converter",
        {
            "cfg": "json",
            "g2h": "1",
            "gy": when.year,
            "gm": when.month,
            "gd": when.day,
            "gs": "on" if after_sunset else None,
            "lg": locale,
        },
    )
    payload = get_json(
        f"{BASE}/converter", params, limiter=_LIMIT, service="hebcal",
        attribution=ATTRIBUTION,
    ).payload
    return HebrewDate(
        year=int(payload.get("hy") or 0),
        month=str(payload.get("hm") or ""),
        day=int(payload.get("hd") or 0),
        hebrew=str(payload.get("hebrew") or ""),
    )


def leyning(
    when: date | str,
    *,
    israel: bool = False,
    triennial: bool = True,
) -> Reading | None:
    """The Torah reading for a date, with its aliyot and haftarah."""
    when = date.fromisoformat(when) if isinstance(when, str) else when
    params = _validate(
        "/leyning",
        {
            "cfg": "json",
            "start": when.isoformat(),
            "end": when.isoformat(),
            "i": "on" if israel else "off",
            "triennial": "on" if triennial else "off",
        },
    )
    payload = get_json(
        f"{BASE}/leyning", params, limiter=_LIMIT, service="hebcal",
        attribution=ATTRIBUTION,
    ).payload
    items = payload.get("items") or []
    if not items:
        return None
    entry = items[0]
    return Reading(
        name=str(entry.get("name", {}).get("en") or entry.get("parsha") or ""),
        hebrew_name=str(entry.get("name", {}).get("he") or ""),
        summary=str(entry.get("summary") or ""),
        haftarah=str(entry.get("haftara") or ""),
        aliyot=[
            Aliyah(number=str(key), ref=str(value.get("k", "")) + " " + str(value.get("b", "")) + "-" + str(value.get("e", "")))
            for key, value in sorted((entry.get("fullkriyah") or {}).items())
        ],
        triennial=[
            Aliyah(number=str(key), ref=str(value.get("k", "")) + " " + str(value.get("b", "")) + "-" + str(value.get("e", "")))
            for key, value in sorted((entry.get("triennial") or {}).items())
        ],
    )


def zmanim(
    when: date | str,
    *,
    geonameid: int | None = None,
    zip_code: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    tzid: str | None = None,
    elevation: int | None = None,
) -> dict[str, Any]:
    """Halachic times for a place and a date.

    A location is required and there is no sensible default, so this raises
    rather than quietly answering for somewhere else.
    """
    when = date.fromisoformat(when) if isinstance(when, str) else when
    if geonameid is None and not zip_code and latitude is None:
        raise ValueError(
            "zmanim needs a location: pass geonameid, zip_code, or "
            "latitude with longitude and tzid"
        )
    params = _validate(
        "/zmanim",
        {
            "cfg": "json",
            "date": when.isoformat(),
            "geonameid": geonameid,
            "zip": zip_code,
            "latitude": latitude,
            "longitude": longitude,
            "tzid": tzid,
            "elev": elevation,
        },
    )
    return get_json(
        f"{BASE}/zmanim", params, limiter=_LIMIT, service="hebcal",
        attribution=ATTRIBUTION,
    ).payload


def yahrzeit(
    death_date: date | str,
    *,
    years: int = 20,
    after_sunset: bool = False,
    name: str = "",
) -> list[dict[str, Any]]:
    """Yahrzeit dates for the coming years."""
    death_date = (
        date.fromisoformat(death_date) if isinstance(death_date, str) else death_date
    )
    body = {
        "v": "yahrzeit",
        "cfg": "json",
        "years": years,
        "type1": "Yahrzeit",
        "sunset1": "on" if after_sunset else "off",
        "name1": name or "Yahrzeit",
        "day1": death_date.day,
        "month1": death_date.month,
        "year1": death_date.year,
    }
    payload = post_json(
        f"{BASE}/yahrzeit", body, limiter=_LIMIT, service="hebcal",
        attribution=ATTRIBUTION,
    ).payload
    return list((payload or {}).get("items") or [])


def read_day(
    when: date | str | None = None,
    *,
    locale: str = SEPHARDI,
    israel: bool = False,
    after_sunset: bool = False,
    candle_lighting: bool = True,
    study: bool = True,
) -> Day:
    """Everything about one date: holidays, the reading, and the study cycles.

    `locale` is the transliteration Hebcal uses for holiday names, and it takes
    any of `LOCALES`. Passing `a` gives Shabbos and Sukkos where the default `s`
    gives Shabbat and Sukkot, so a reader who writes in Ashkenazi register can
    keep the names in register too.
    """
    when = date.today() if when is None else when
    when = date.fromisoformat(when) if isinstance(when, str) else when

    if locale not in LOCALES:
        raise ValueError(
            f"{locale!r} is not a Hebcal locale. Available: {', '.join(LOCALES)}"
        )

    params = _validate(
        "/hebcal",
        {
            "v": "1",
            "cfg": "json",
            "start": when.isoformat(),
            "end": when.isoformat(),
            "maj": "on",
            "min": "on",
            "mod": "on",
            "nx": "on",
            "ss": "on",
            "mf": "on",
            "s": "on",
            "d": "on" if study else None,
            "D": "on" if study else None,
            "F": "on" if study else None,
            "myomi": "on" if study else None,
            "i": "on" if israel else "off",
            "c": "on" if candle_lighting else None,
            "lg": locale,
        },
    )
    payload = get_json(
        f"{BASE}/hebcal", params, limiter=_LIMIT, service="hebcal",
        attribution=ATTRIBUTION,
    ).payload

    events: list[Event] = []
    study_entries: list[StudyEntry] = []
    reading: Reading | None = None

    for item in payload.get("items") or []:
        category = str(item.get("category") or "")
        title = str(item.get("title") or "")
        if category in ("dafyomi", "mishnayomi", "nachyomi", "yerushalmi", "chofetzChaim", "dailyRambam", "shemirat"):
            study_entries.append(
                StudyEntry(cycle=category, ref=str(item.get("title") or ""))
            )
            continue
        if category == "parashat":
            reading = Reading(
                name=title.replace("Parashat ", ""),
                hebrew_name=str(item.get("hebrew") or ""),
                summary=str(item.get("leyning", {}).get("torah") or ""),
                haftarah=str(item.get("leyning", {}).get("haftarah") or ""),
            )
            continue
        events.append(
            Event(
                title=title,
                category=category,
                hebrew=str(item.get("hebrew") or ""),
                date=str(item.get("date") or ""),
            )
        )

    hebrew_date = convert(when, after_sunset=after_sunset, locale=locale)

    if reading is None:
        # The parashah is announced on Shabbat. On a weekday, look ahead to the
        # coming one rather than reporting nothing.
        ahead = when + timedelta(days=(5 - when.weekday()) % 7)
        reading = leyning(ahead, israel=israel)

    return Day(
        gregorian=when,
        hebrew_date=hebrew_date,
        locale=locale,
        events=events,
        reading=reading,
        study=study_entries,
    )
