"""Download every published standard named in `sources/manifest.md` and verify it.

Why this exists
---------------
The romanization tables in `schemes/` are extracted from five published
documents. Two of those documents are copyrighted commercial publications, so
`sources/pdf/` is gitignored and nothing but provenance is committed.

That would make the tables unverifiable by anyone but their author, which is
unacceptable for data whose whole claim is that it was copied rather than
invented. This script closes that gap. It reads the manifest, fetches each
document from the URL recorded there, and checks the bytes against the recorded
SHA-256. After it runs, anyone can re-derive every table from primary sources
and check the result against what is committed.

What it refuses to do
---------------------
A hash mismatch means the publisher changed the document since the tables were
built. That is a fact worth knowing before the tables are trusted again, so the
fetcher reports it and leaves the existing file alone rather than overwriting a
verified copy with an unverified one.

Usage
-----
    python -m tools.fetch_sources              # fetch anything missing, verify all
    python -m tools.fetch_sources --check      # verify what is on disk, fetch nothing
    python -m tools.fetch_sources --force      # re-fetch even what is already present
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "sources" / "manifest.md"

# Some publishers refuse a request with no User-Agent. Identifying the tool
# honestly is better than pretending to be a browser.
USER_AGENT = "meturgaman/0.1 (+https://github.com/Oranburg/meturgaman)"


@dataclass(frozen=True)
class Source:
    """One published standard, as the manifest records it."""

    title: str
    path: Path
    url: str
    size: int
    sha256: str

    def on_disk_digest(self) -> str | None:
        """The SHA-256 of the local copy, or None when there is no local copy."""
        if not self.path.exists():
            return None
        return hashlib.sha256(self.path.read_bytes()).hexdigest()


# The manifest is prose for humans first. Rather than invent a parallel machine
# format that could drift out of step with it, this reads the prose. Each entry
# is an H2 heading followed by a bulleted block; these three fields are the ones
# that have to be exact.
_ENTRY = re.compile(
    r"^##\s+(?P<title>.+?)\s*$"
    r".*?\*\*File\*\*\s*`(?P<path>[^`]+)`\s*\((?P<size>[\d,]+)\s*bytes\)"
    r".*?\*\*URL\*\*\s*(?P<url>\S+)"
    r".*?\*\*SHA-256\*\*\s*`(?P<sha>[0-9a-f]{64})`",
    re.MULTILINE | re.DOTALL,
)


def read_manifest(manifest: Path = MANIFEST) -> list[Source]:
    """Parse `sources/manifest.md` into Source records.

    Raises rather than returning a short list. A manifest that half-parses is
    worse than one that does not parse, because the missing entries would look
    like sources that simply are not required.
    """
    if not manifest.exists():
        raise FileNotFoundError(f"no manifest at {manifest}")

    text = manifest.read_text(encoding="utf-8")

    # Split on H2 boundaries first so a malformed entry cannot swallow the next
    # one through the non-greedy DOTALL match above.
    chunks = re.split(r"(?m)^(?=##\s)", text)
    sources: list[Source] = []
    for chunk in chunks:
        if not chunk.lstrip().startswith("## "):
            continue
        if "**SHA-256**" not in chunk:
            # Sections like "## Re-fetching" are prose, not source entries.
            continue
        match = _ENTRY.search(chunk)
        if not match:
            heading = chunk.splitlines()[0].strip()
            raise ValueError(
                f"manifest entry {heading!r} is missing one of File, URL, or SHA-256"
            )
        sources.append(
            Source(
                title=match["title"].strip(),
                path=REPO_ROOT / match["path"],
                url=match["url"].strip(),
                size=int(match["size"].replace(",", "")),
                sha256=match["sha"],
            )
        )

    if not sources:
        raise ValueError(f"{manifest} named no sources")
    return sources


def fetch(source: Source) -> bytes:
    """Retrieve one source over HTTPS, returning the raw bytes."""
    request = urllib.request.Request(source.url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fetch_sources", description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify what is already on disk and download nothing",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-download every source even when a verified copy is present",
    )
    arguments = parser.parse_args(argv)

    sources = read_manifest()
    failures = 0

    for source in sources:
        digest = source.on_disk_digest()

        if digest == source.sha256 and not arguments.force:
            print(f"ok       {source.path.name}  ({source.size:,} bytes)")
            continue

        if digest is not None and digest != source.sha256:
            # A local copy that does not match. Never silently replace it: the
            # tables were built against whatever these bytes are, and knowing
            # they have drifted matters more than getting a fresh download.
            print(f"MISMATCH {source.path.name}")
            print(f"         on disk  {digest}")
            print(f"         manifest {source.sha256}")
            print("         left in place. Investigate before trusting the tables.")
            failures += 1
            continue

        if arguments.check:
            print(f"MISSING  {source.path.name}  (run without --check to fetch)")
            failures += 1
            continue

        print(f"fetching {source.path.name}  <- {source.url}")
        try:
            payload = fetch(source)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as error:
            print(f"FAILED   {source.path.name}: {error}")
            failures += 1
            continue

        got = hashlib.sha256(payload).hexdigest()
        if got != source.sha256:
            # The publisher has changed the document. Refuse to write it: an
            # unverified PDF on disk would look identical to a verified one the
            # next time someone checks.
            print(f"MISMATCH {source.path.name} as published today")
            print(f"         downloaded {got}")
            print(f"         manifest   {source.sha256}")
            print("         not written. The publisher changed the document.")
            failures += 1
            continue

        source.path.parent.mkdir(parents=True, exist_ok=True)
        source.path.write_bytes(payload)
        print(f"ok       {source.path.name}  ({len(payload):,} bytes, verified)")

    print()
    if failures:
        print(f"{failures} of {len(sources)} sources could not be verified.")
        return 1
    print(f"All {len(sources)} sources verified against the manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
