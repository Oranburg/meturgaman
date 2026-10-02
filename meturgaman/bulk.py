"""Fetch a whole work from Sefaria, every freely licensed version, chapter by chapter.

Run it as `python -m meturgaman.bulk "<Sefaria index title>" --out <folder>`.
Built and proven on the Maimonides corpus on the PC on 2026-10-02 (the Guide's
Ibn Tibbon and Munk versions match the index shape, 76/534, 48/379, 54/451).

Why this exists
---------------
Sefaria's reader shows one small portion at a time, and its texts endpoint
refuses a request for a whole complex work: asking for "Guide for the
Perplexed" answers HTTP 400, because the work is a tree of parts and
introductions rather than one array. Getting a whole work means walking that
tree and asking for each piece.

This module does the walking. It reads the work's shape (every leaf node, how
many chapters, how many segments in each), reads the list of every version
Sefaria holds with its licence, and asks for each chapter once, naming up to
six versions per request. It writes one file per version, and a manifest that
sets what came back beside what the shape says should be there.

What it refuses to do
---------------------
It fetches no version whose licence is not stated as free. A version listed
with licence "unknown" is recorded in the manifest as skipped, with the reason,
and nothing of it is written to disk.

A request that was rate limited, timed out, or met a server error is recorded
as "not fetched yet", never as missing. Only a successful answer that holds no
text for a version is evidence that the version lacks that chapter.

Every chapter that arrives is written to disk at once under `sections/`, and a
second run skips every chapter already there.

Usage
-----
    python sefaria_bulk.py "Guide for the Perplexed" --out corpus/
    python sefaria_bulk.py "Eight Chapters" --out corpus/ --version english
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from meturgaman.net import NetworkError

#: Licence words that mean a version may be copied for study. "unknown" and an
#: empty string match none of these, which is the point.
FREE_LICENCE_TOKENS = ("public domain", "cc0", "cc-by", "creative commons")

#: Versions named per request. More builds a URL the server has answered with
#: a 502 (the same limit meturgaman's sefaria.read observes).
BATCH = 6

#: HTTP statuses that mean "ask again later", never "this does not exist".
RETRYABLE = {408, 425, 429, 500, 502, 503, 504}


def slug(text: str) -> str:
    """A filename-safe form of a title. Lossy, so the manifest keeps the title."""
    text = re.sub(r"[^\w\s.-]", " ", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text.strip())
    return text.strip("-.")[:90] or "untitled"


def is_free_licence(licence: str) -> bool:
    text = (licence or "").lower()
    return any(token in text for token in FREE_LICENCE_TOKENS)


def _total(node: Any) -> int:
    if isinstance(node, bool):
        return 0
    if isinstance(node, int):
        return max(node, 0)
    if isinstance(node, list):
        return sum(_total(item) for item in node)
    return 0


@dataclass(frozen=True)
class Leaf:
    """One text-bearing node: an introduction, a part, a book.

    `counts` is the shape record's own value: an int (a node of depth 1 with so
    many segments), a list of ints (chapters of so many segments), or deeper
    lists.
    """

    title: str
    counts: Any

    @property
    def expected_segments(self) -> int:
        return _total(self.counts)

    @property
    def expected_chapters(self) -> int:
        if isinstance(self.counts, list):
            return sum(1 for item in self.counts if _total(item) > 0)
        return 1 if _total(self.counts) > 0 else 0


def leaves(shape_payload: Any) -> list[Leaf]:
    """Every text-bearing node in a shape payload. Pure, no network.

    A simple work's shape is a record whose `chapters` is a list of counts. A
    complex work's shape is a record whose `chapters` is a list of child
    records, each with its own `title` and `chapters`.
    """
    found: list[Leaf] = []

    def visit(record: Any) -> None:
        if not isinstance(record, dict):
            return
        chapters = record.get("chapters")
        title = str(record.get("title") or record.get("book") or "")
        if isinstance(chapters, list) and chapters and all(isinstance(i, dict) for i in chapters):
            for child in chapters:
                visit(child)
            return
        if title and isinstance(chapters, (int, list)) and not isinstance(chapters, bool):
            found.append(Leaf(title=title, counts=chapters))

    for record in shape_payload if isinstance(shape_payload, list) else [shape_payload]:
        visit(record)
    return found


def section_refs(leaf: Leaf) -> list[tuple[str, int]]:
    """The requests that cover one leaf, with the segments each should hold."""
    if not isinstance(leaf.counts, list):
        return [(leaf.title, _total(leaf.counts))]
    return [
        (f"{leaf.title} {index}", _total(item))
        for index, item in enumerate(leaf.counts, start=1)
        if _total(item) > 0
    ]


def _clean(value: Any) -> str:
    from meturgaman.sources.sefaria import _clean as clean
    return clean(value)


def flatten(text: Any, base: str, whole_node: bool) -> list[tuple[str, str]]:
    """Jagged text as (anchor, text) pairs, anchored the way Sefaria cites.

    Whole depth-1 node "Work, Introduction" -> "Work, Introduction 3".
    Section "Work, Part 1 2" -> "Work, Part 1 2:3".
    """
    pairs: list[tuple[str, str]] = []

    def walk(node: Any, path: tuple[int, ...]) -> None:
        if node is None:
            return
        if isinstance(node, str):
            cleaned = _clean(node)
            if not cleaned:
                return
            numbers = [str(i + 1) for i in path]
            if not numbers:
                anchor = base
            elif whole_node:
                anchor = f"{base} {':'.join(numbers)}"
            else:
                anchor = f"{base}:{':'.join(numbers)}"
            pairs.append((anchor, cleaned))
            return
        if isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, path + (index,))

    walk(text, ())
    return pairs


@dataclass
class VersionInfo:
    title: str
    language: str
    family: str
    actual_language: str
    licence: str
    source: str
    free: bool

    @property
    def request_name(self) -> str:
        # The texts endpoint wants the full language name, not the ISO code.
        return f"{self.family}|{self.title}"

    @property
    def file_stem(self) -> str:
        return slug(f"{self.actual_language or self.language} {self.title}")


def versions_from(payload: Any) -> list[VersionInfo]:
    found: list[VersionInfo] = []
    for row in payload if isinstance(payload, list) else []:
        if not isinstance(row, dict) or not row.get("versionTitle"):
            continue
        licence = str(row.get("license") or "")
        found.append(VersionInfo(
            title=str(row["versionTitle"]),
            language=str(row.get("language") or ""),
            family=str(row.get("languageFamilyName") or ""),
            actual_language=str(row.get("actualLanguage") or ""),
            licence=licence,
            source=str(row.get("versionSource") or ""),
            free=is_free_licence(licence),
        ))
    return found


def _status_of(error: BaseException) -> int | None:
    cause = error.__cause__ or error.__context__
    code = getattr(cause, "code", None)
    return code if isinstance(code, int) else None


def _retry_after(error: BaseException) -> float | None:
    cause = error.__cause__ or error.__context__
    headers = getattr(cause, "headers", None)
    value = headers.get("Retry-After") if headers is not None else None
    try:
        return float(value) if value else None
    except (TypeError, ValueError):
        return None


def default_get(path: str, params: dict[str, Any] | None = None) -> Any:
    from meturgaman.sources import sefaria
    # The section store is this job's cache; meturgaman's response cache is not
    # filled with a whole work as well.
    return sefaria._get(path, params, use_cache=False).payload


def ask(get, path, params, *, retries, backoff, sleep, log) -> tuple[Any, str]:
    """One request with exponential backoff. Returns (payload, "") or (None, reason)."""
    delay = backoff
    reason = ""
    for attempt in range(retries + 1):
        try:
            return get(path, params), ""
        except NetworkError as error:
            status = _status_of(error)
            if status is not None and status not in RETRYABLE:
                return None, f"HTTP {status}: {str(error).splitlines()[0][:200]}"
            reason = str(error).splitlines()[0][:200]
            if attempt == retries:
                break
            wait = max(delay, _retry_after(error) or 0.0)
            log(f"    retry {attempt + 1}/{retries} in {wait:.0f}s: {reason}")
            sleep(wait)
            delay = min(delay * 2, 600.0)
    return None, f"not fetched yet after {retries + 1} attempts: {reason}"


def _section_file(work_dir: Path, ref: str) -> Path:
    return work_dir / "sections" / f"{slug(ref)}.json"


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1)
    temporary.replace(path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _wanted(version: VersionInfo, selectors: Iterable[str]) -> bool:
    chosen = [s.strip() for s in selectors if s.strip()]
    if not chosen:
        return True
    for text in chosen:
        if "|" in text:
            if text.lower() == version.request_name.lower():
                return True
        elif text.lower() in (version.title.lower(), version.language.lower(),
                              version.family.lower(), version.actual_language.lower()):
            return True
    return False


def _url_section(ref: str) -> str:
    """'Work, Part 1 2' -> 'Work,_Part_1.2', the form Sefaria's own URLs use."""
    head, _, number = ref.rpartition(" ")
    return f"{head.replace(' ', '_')}.{number}"


def fetch_work(
    title: str,
    out: str | Path,
    *,
    versions: Iterable[str] = (),
    pause: float = 1.0,
    retries: int = 6,
    backoff: float = 5.0,
    get: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = lambda line: None,
    now: Callable[[], str] | None = None,
) -> dict[str, Any]:
    """Fetch every free version of `title` into `out/<slug>/`, return the manifest."""
    get = get or default_get
    now = now or (lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    work_dir = Path(out) / slug(title)
    work_dir.mkdir(parents=True, exist_ok=True)
    url_title = title.replace(" ", "_")
    started = now()
    asked = {"requests": 0}
    versions = list(versions)

    def request(path, params=None):
        if asked["requests"]:
            sleep(pause)
        asked["requests"] += 1
        return ask(get, path, params, retries=retries, backoff=backoff, sleep=sleep, log=log)

    shape_payload, why = request(f"/shape/{url_title}")
    if shape_payload is None:
        raise LookupError(f"{title!r}: shape not fetched yet ({why})")
    if isinstance(shape_payload, dict) and shape_payload.get("error"):
        raise LookupError(f"{title!r}: {shape_payload['error']}")
    listing, why = request(f"/texts/versions/{url_title}")
    if listing is None:
        raise LookupError(f"{title!r}: version listing not fetched yet ({why})")
    _write_json(work_dir / "shape.json", shape_payload)
    _write_json(work_dir / "versions.json", listing)

    all_versions = versions_from(listing)
    chosen = [v for v in all_versions if v.free and _wanted(v, versions)]
    skipped = [
        {"title": v.title, "language": v.actual_language or v.language,
         "licence": v.licence or "(none stated)", "source": v.source,
         "reason": ("licence not stated as free; nothing fetched" if not v.free
                    else "not selected")}
        for v in all_versions if v not in chosen
    ]
    work_leaves = leaves(shape_payload)
    if not work_leaves:
        raise LookupError(f"{title!r}: the shape record names no text-bearing node")

    not_fetched: list[dict[str, str]] = []
    for leaf in work_leaves:
        whole = not isinstance(leaf.counts, list)
        for ref, _expected in section_refs(leaf):
            target = _section_file(work_dir, ref)
            if target.exists():
                continue
            gathered: list[dict[str, Any]] = []
            warnings: list[Any] = []
            failed = ""
            for start in range(0, len(chosen), BATCH):
                batch = chosen[start:start + BATCH]
                path = f"/v3/texts/{ref.replace(' ', '_') if whole else _url_section(ref)}"
                payload, why = request(path, {"version": [v.request_name for v in batch],
                                              "return_format": "text_only"})
                if payload is None or not isinstance(payload, dict):
                    failed = why or "unexpected reply"
                    break
                if payload.get("error"):
                    failed = f"service error: {payload['error']}"
                    break
                for entry in payload.get("versions") or []:
                    gathered.append({
                        "versionTitle": entry.get("versionTitle"),
                        "language": entry.get("language"),
                        "license": entry.get("license"),
                        "text": entry.get("text"),
                    })
                warnings.extend(payload.get("warnings") or [])
            if failed:
                not_fetched.append({"ref": ref, "reason": failed})
                log(f"  NOT FETCHED {ref}: {failed}")
                continue
            _write_json(target, {"ref": ref, "whole_node": whole, "fetched_at": now(),
                                 "versions": gathered, "warnings": warnings})
            log(f"  fetched {ref} ({len(gathered)} versions)")

    manifest = assemble(title, work_dir, work_leaves, chosen, skipped, not_fetched,
                        started, now())
    manifest["requests_this_run"] = asked["requests"]
    _write_json(work_dir / "manifest.json", manifest)
    return manifest


def assemble(title, work_dir, work_leaves, chosen, skipped, not_fetched, started, finished):
    """Write one file per version from the section store, and count against the shape."""
    # Keyed by language and title together: Sefaria reuses one versionTitle for
    # an English and a Hebrew version (Gorfinkle's Eight Chapters, Wikisource's
    # Mishneh Torah), and keying by title alone merged the two into one file.
    per_version = {(v.language, v.title): {"segments": [], "by_leaf": {}} for v in chosen}
    missing_sections = {row["ref"]: row["reason"] for row in not_fetched}
    for leaf in work_leaves:
        whole = not isinstance(leaf.counts, list)
        for ref, _expected in section_refs(leaf):
            path = _section_file(work_dir, ref)
            if not path.exists():
                missing_sections.setdefault(ref, "not on disk")
                continue
            stored = json.loads(path.read_text(encoding="utf-8"))
            for entry in stored.get("versions") or []:
                bucket = per_version.get((str(entry.get("language") or ""),
                                          str(entry.get("versionTitle"))))
                if bucket is None:
                    continue
                pairs = flatten(entry.get("text"), ref, whole)
                if not pairs:
                    continue
                counts = bucket["by_leaf"].setdefault(leaf.title, {"chapters": 0, "segments": 0})
                counts["chapters"] += 1
                counts["segments"] += len(pairs)
                bucket["segments"].append({"leaf": leaf.title, "section": ref, "pairs": pairs})

    shape_rows = [{"leaf": leaf.title, "chapters": leaf.expected_chapters,
                   "segments": leaf.expected_segments} for leaf in work_leaves]
    version_rows = []
    for version in chosen:
        bucket = per_version[(version.language, version.title)]
        stem = version.file_stem
        json_path = work_dir / f"{stem}.json"
        md_path = work_dir / f"{stem}.md"
        record = {
            "work": title, "version": version.title,
            "language": version.actual_language or version.language,
            "licence": version.licence, "source": version.source,
            "served_by": "https://www.sefaria.org", "fetched": finished,
            "segments": [{"ref": a, "text": t}
                         for item in bucket["segments"] for a, t in item["pairs"]],
        }
        _write_json(json_path, record)
        write_markdown(md_path, version, title, bucket["segments"], finished)
        leaf_rows = []
        complete = True
        for leaf in work_leaves:
            got = bucket["by_leaf"].get(leaf.title, {"chapters": 0, "segments": 0})
            ok = (got["chapters"], got["segments"]) == (leaf.expected_chapters,
                                                        leaf.expected_segments)
            complete = complete and ok
            leaf_rows.append({"leaf": leaf.title,
                              "chapters": got["chapters"], "expected_chapters": leaf.expected_chapters,
                              "segments": got["segments"], "expected_segments": leaf.expected_segments,
                              "matches_shape": ok})
        version_rows.append({
            "title": version.title, "language": version.actual_language or version.language,
            "licence": version.licence, "source": version.source,
            "files": {"json": json_path.name, "markdown": md_path.name},
            "sha256": {"json": _sha256(json_path), "markdown": _sha256(md_path)},
            "segments": len(record["segments"]),
            "complete_against_shape": complete and not missing_sections,
            "by_leaf": leaf_rows,
        })
    return {
        "work": title, "service": "https://www.sefaria.org/api",
        "started": started, "finished": finished,
        "shape": shape_rows,
        "shape_totals": {"chapters": sum(r["chapters"] for r in shape_rows),
                         "segments": sum(r["segments"] for r in shape_rows)},
        "versions": version_rows,
        "skipped_versions": skipped,
        "sections_not_fetched_yet": [{"ref": k, "reason": v}
                                     for k, v in sorted(missing_sections.items())],
        "note": ("A version whose counts fall short of the shape, with no section listed as "
                 "not fetched yet, lacks that text on Sefaria. A section listed as not fetched "
                 "yet was rate limited or failed and is not evidence of anything; run the same "
                 "command again to resume."),
    }


def write_markdown(path, version, title, sections, fetched) -> None:
    lines = [
        "---",
        f"title: {json.dumps(title + ' - ' + version.title, ensure_ascii=False)}",
        f"work: {json.dumps(title, ensure_ascii=False)}",
        f"version: {json.dumps(version.title, ensure_ascii=False)}",
        f"language: {version.actual_language or version.language}",
        f"licence: {json.dumps(version.licence, ensure_ascii=False)}",
        f"source: {json.dumps(version.source, ensure_ascii=False)}",
        "served_by: https://www.sefaria.org",
        f"fetched: {fetched}",
        "---", "",
        f"# {title}", "",
        f"{version.title}. Licence: {version.licence}. Source: {version.source}.", "",
    ]
    current_leaf = None
    for item in sections:
        if item["leaf"] != current_leaf:
            current_leaf = item["leaf"]
            lines += [f"## {current_leaf}", ""]
        if item["section"] != item["leaf"]:
            lines += [f"### {item['section']}", ""]
        for anchor, text in item["pairs"]:
            lines += [f"[{anchor}] {text}", ""]
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("title", nargs="+", help="Sefaria index title(s)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--version", action="append", default=[],
                        help="version title, language, or 'language|Title'. Repeatable.")
    parser.add_argument("--pause", type=float, default=1.0, help="seconds between requests")
    parser.add_argument("--retries", type=int, default=6)
    parser.add_argument("--backoff", type=float, default=5.0)
    arguments = parser.parse_args(argv)
    status = 0
    for title in arguments.title:
        print(f"== {title}", flush=True)
        try:
            manifest = fetch_work(title, arguments.out, versions=arguments.version,
                                  pause=arguments.pause, retries=arguments.retries,
                                  backoff=arguments.backoff,
                                  log=lambda line: print(line, flush=True))
        except (LookupError, NetworkError) as error:
            print(f"refused: {error}", file=sys.stderr, flush=True)
            status = 1
            continue
        totals = manifest["shape_totals"]
        print(f"shape: {totals['chapters']} chapters, {totals['segments']} segments")
        for row in manifest["versions"]:
            flag = "matches shape" if row["complete_against_shape"] else "DIFFERS from shape"
            print(f"  {row['language']:3} {row['segments']:6}  {flag}  {row['title']} [{row['licence']}]")
        for row in manifest["skipped_versions"]:
            print(f"  skipped {row['title']} [{row['licence']}]: {row['reason']}")
        if manifest["sections_not_fetched_yet"]:
            status = 1
            print(f"  NOT FETCHED YET: {len(manifest['sections_not_fetched_yet'])} sections")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
