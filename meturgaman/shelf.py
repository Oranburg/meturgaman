"""Write Sources-shelf records for LawOS from passages fetched live from Sefaria.

A shelf record is one markdown file per passage: front matter that LawOS's
`harvest.from_ancient_text` turns into an EndNote Ancient Text record, and a
body that quotes each edition with its licence. Every field comes from a fetch
made at build time, never from a remembered value.

The field mapping is the one ruled on 2026-09-13:

- `title` is the traditional locator. For the Zohar it is the daf, computed
  from the index's own `alt_structs.Daf`, because Sefaria's segmented ref names
  no traditional handle and `is_ref` on a daf form silently widens to the whole
  book.
- `sefaria_ref` is the retrieval key, copied exactly as Sefaria normalized it.
- `work` is the bare index title, never a composed "Corpus, Tractate".
- `author` is a name resolved through the topics API, never a slug, and blank
  where the index states `authors: []`.
- `year` is the edition's own first printing, per Chicago.
- An edition with no stated licence keeps its text and says so.

A manifest drives a build, so the list of passages and what joins them belongs
to the project that gathered them, not to this repository.
"""

from __future__ import annotations

import datetime
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from meturgaman.sources import sefaria

__all__ = ["Entry", "Manifest", "Record", "build", "build_all", "zohar_daf",
           "load_manifest", "slug"]

KIND_BY_CATEGORY = {
    "Tanakh": "Tanakh", "Talmud": "Talmud", "Mishnah": "Mishnah",
    "Midrash": "Midrash", "Halakhah": "Halakhah", "Kabbalah": "Kabbalah",
    "Second Temple": "Second Temple", "Chasidut": "Chasidut",
}
UNSTATED = {"", "unknown", "none", "unspecified"}
FLAG = "unknown, check the licence"


@dataclass
class Entry:
    ref: str
    echoes: str = ""
    labelled_translation: str = ""


@dataclass
class Manifest:
    entries: list[Entry]
    saga: str = ""
    project: str = ""
    labelled_by: str = ""


@dataclass
class Record:
    ref: str
    filename: str
    text: str
    log: list[str] = field(default_factory=list)


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()[:70]


def _quote(value: Any) -> str:
    value = " ".join(str(value).split())
    return '"' + value.replace('"', "'") + '"'


def load_manifest(path: str | Path) -> Manifest:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = [Entry(**row) if isinstance(row, dict) else Entry(ref=str(row))
               for row in data.get("entries") or []]
    if not entries:
        raise ValueError(f"{path} names no entries")
    return Manifest(entries=entries, saga=data.get("saga", ""),
                    project=data.get("project", ""),
                    labelled_by=data.get("labelled_by", ""))


def zohar_daf(ref: str, index: dict[str, Any]) -> tuple[str | None, str]:
    """The traditional daf for a segmented Zohar ref, or (None, why)."""
    found = re.match(r"Zohar, ([A-Za-z' ]+?) (\d+):(\d+)$", ref)
    if not found:
        return None, "not a single-segment Zohar ref"
    parashah, chapter, segment = found.group(1), int(found.group(2)), int(found.group(3))

    def english(node: dict[str, Any]) -> str:
        for title in node.get("titles") or []:
            if title.get("lang") == "en":
                return title.get("text", "")
        return node.get("title", "")

    nodes = ((index.get("alt_structs") or {}).get("Daf") or {}).get("nodes") or []
    for volume in nodes:
        for child in volume.get("nodes") or []:
            if english(child) != parashah:
                continue
            start = re.match(r"(\d+)([ab])$", child.get("startingAddress") or "")
            if not start:
                return None, "the daf node states no startingAddress"
            base, side = int(start.group(1)), start.group(2)
            for position, span in enumerate(child.get("refs") or []):
                pairs = re.findall(r"(\d+):(\d+)", span)
                if not pairs:
                    continue
                low = (int(pairs[0][0]), int(pairs[0][1]))
                if len(pairs) >= 2:
                    high = (int(pairs[1][0]), int(pairs[1][1]))
                else:
                    tail = re.search(r"-(\d+)$", span)
                    high = (low[0], int(tail.group(1))) if tail else low
                if low <= (chapter, segment) <= high:
                    offset = position + (1 if side == "b" else 0)
                    roman = {"Volume I": "I", "Volume II": "II",
                             "Volume III": "III"}.get(english(volume), english(volume))
                    return f"Zohar {roman}:{base + offset // 2}{'b' if offset % 2 else 'a'}", ""
    return None, "no daf node covers this segment"


def _raw(path: str) -> dict[str, Any]:
    payload = sefaria._get(path).payload
    return payload if isinstance(payload, dict) else {}


def _author(slug_: str, raw: Callable[[str], dict]) -> tuple[str, str]:
    topic = raw(f"/topics/{slug_}")
    name = ((topic.get("primaryTitle") or {}).get("en") or "").strip()
    props = topic.get("properties") or {}
    born = (props.get("birthYear") or {}).get("value")
    died = (props.get("deathYear") or {}).get("value")
    return name, (f"{born}-{died}" if born and died else f"{born}-" if born else "")


def build(entry: Entry, manifest: Manifest, *, today: str | None = None,
          read: Callable[..., Any] = sefaria.read,
          raw: Callable[[str], dict] = _raw) -> Record:
    """One shelf record. Raises LookupError when no source edition exists."""
    today = today or datetime.date.today().isoformat()
    log: list[str] = []
    reading = read(entry.ref, version=("source", "translation"), max_editions=12)
    ref = reading.ref.normalized or entry.ref
    by_language = lambda lang: sorted(
        (o for o in reading.observations if (o.edition.language or "").startswith(lang)),
        key=lambda o: not o.edition.is_primary)
    source = by_language("he") or by_language("ar")
    english = by_language("en")
    if not source:
        raise LookupError(f"no Hebrew or Aramaic edition for {entry.ref}")

    # Ref.book is the last node on the navigation path, which on a complex
    # book (the Zohar, a Mekhilta tractate) is a section, not the index.
    index_title = raw(f"/v3/texts/{ref}").get("indexTitle") or ref
    index = raw(f"/v2/raw/index/{index_title.replace(' ', '_')}")
    categories = index.get("categories") or []
    kind = KIND_BY_CATEGORY.get(categories[0] if categories else "", "")
    if not kind:
        log.append(f"unmapped kind for {ref}: {categories}")

    title, title_note = ref, ""
    if index_title == "Zohar":
        daf, why = zohar_daf(ref, index)
        if daf:
            title = daf
            title_note = (f"the traditional daf, computed from the Zohar index's own "
                          f"alt_structs.Daf; Sefaria's segmented ref {ref} is kept as the retrieval key")
        else:
            log.append(f"Zohar daf not computed for {ref}: {why}")

    author = author_dates = ""
    if index.get("authors"):
        author, author_dates = _author(index["authors"][0], raw)
        if not author:
            log.append(f"author slug unresolved for {ref}: {index['authors']}")

    def licence(value: str, which: str) -> str:
        if (value or "").strip().lower() in UNSTATED:
            log.append(f"no licence stated for {ref} ({which})")
            return FLAG
        return value

    he = source[0].edition
    translation, licences = "", f"{licence(he.license, 'Hebrew')} (Hebrew)"
    if english:
        translation = english[0].edition.title
        licences += f"; {licence(english[0].edition.license, 'English')} (English)"
    elif entry.labelled_translation:
        translation = manifest.labelled_by or "Labelled translation; not a published edition"
        licences += "; translation is not a published edition (see Translator)"
    else:
        log.append(f"no English edition for {ref}, and the manifest supplies no labelled translation")

    composed, printed = index.get("compDate"), index.get("pubDate")
    front = [f"key: ancient|sefaria|{slug(ref)}", f"title: {_quote(title)}",
             f"sefaria_ref: {_quote(ref)}", f"work: {_quote(index_title)}"]
    if categories:
        front.append(f"corpus: {_quote(' / '.join(categories))}")
    front.append(f"edition: {_quote(he.title)}")
    if translation:
        front.append(f"translation: {_quote(translation)}")
    if he.source:
        front.append(f"edition_source: {_quote(he.source)}")
    front += [f"licence: {_quote(licences)}",
              f"language: {_quote('he; en' if english else 'he')}"]
    if author:
        front.append(f"author: {_quote(author)}")
    if author_dates:
        front.append(f"author_dates: {_quote(author_dates)}")
    if printed:
        front.append(f"year: {printed[0]}")
    if composed:
        front.append(f"composed: {_quote('c. ' + '-'.join(map(str, composed)) + ' CE per the Sefaria index record')}")
    if printed:
        place = index.get("pubPlace")
        front.append(f"first_printed: {_quote(', '.join(map(str, printed)) + (', ' + place if place else '') + ' (Sefaria index record)')}")
    if index.get("era"):
        front.append(f"era: {_quote(str(index['era']) + ' (Sefaria era code)')}")
    if kind:
        front.append(f"kind: {kind}")
    if title_note:
        front.append(f"title_note: {_quote(title_note)}")
    if manifest.project:
        front.append(f"project: {manifest.project}")
    if entry.echoes:
        front.append(f"echoes: {_quote(entry.echoes)}")
    front.append(f"sefaria_url: https://www.sefaria.org/{reading.ref.url_ref or ref.replace(' ', '_')}")
    front.append(f"fetched: {_quote(today + ' via meturgaman from Sefaria')}")
    if manifest.saga:
        front.append(f"saga: {_quote(manifest.saga)}")

    body = [f"# {title}", ""]
    if title != ref:
        body += [f"Sefaria ref: {ref}", ""]
    for observation in source[:1] + english[:1]:
        edition = observation.edition
        body += [f"## {edition.title} ({edition.language}, {edition.license or 'licence unknown, check the licence'})", ""]
        for segment in observation.segments:
            body += [(f"**{segment.anchor}** " if segment.anchor else "") + segment.text, ""]
    if not english and entry.labelled_translation:
        body += [f"## English: {translation}", "",
                 "Sefaria serves no published English edition at this segment. The English below "
                 "is a labelled translation, not an edition, and must be cited as such.", ""]
        for paragraph in entry.labelled_translation.split("\n\n"):
            body += [paragraph, ""]
    body.append(reading.attribution)

    text = "---\n" + "\n".join(front) + "\n---\n\n" + "\n".join(body) + "\n"
    return Record(ref=ref, filename=f"{slug(ref)}.md", text=text, log=log)


def build_all(manifest: Manifest, out_dir: Path, *, write: bool = True,
              **kwargs: Any) -> tuple[list[Record], list[str]]:
    records, failures = [], []
    for entry in manifest.entries:
        try:
            record = build(entry, manifest, **kwargs)
        except (LookupError, ValueError, OSError) as error:
            failures.append(f"{entry.ref}: {error}")
            continue
        records.append(record)
        if write:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / record.filename).write_text(record.text, encoding="utf-8", newline="\n")
    return records, failures
