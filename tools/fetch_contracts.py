"""Fetch and verify the API contracts named in `docs/api/README.md`.

Why this exists
---------------
`docs/api/` holds what Sefaria and Hebcal publish about themselves, committed so
the code is written against a recorded spec rather than against anyone's memory
of one. A committed copy is only worth what its provenance is worth, so the
README records a URL and a SHA-256 for each file and this script is what makes
those checkable.

It replaces two lines of prose telling the reader to run `curl`. That prose was
wrong on Windows in two ways at once: the backslash line continuation is bash,
and `curl` in Windows PowerShell 5.1 is an alias for `Invoke-WebRequest`, whose
arguments are nothing like curl's, so `-sSL -o` fails with a parameter error that
says nothing about the actual task. A command that works everywhere is better
than a command with a footnote.

It also removes a step that was already done wrong once. The README used to ask
the reader to record the new byte count and SHA-256 by hand, and the first three
hashes committed here were computed from Windows working copies under
`core.autocrlf=true` and so described one platform's rendering of a file rather
than the file. This prints the values to paste, computed from the bytes the
service actually served.

What it refuses to do
---------------------
A hash mismatch means the publisher changed the document since it was committed.
That is a fact worth knowing before the file is trusted again, so it is reported
and the existing copy is left alone. `--refresh` is how you say you want the new
one.

Usage
-----
    python -m tools.fetch_contracts             # verify, and fetch anything missing
    python -m tools.fetch_contracts --check     # verify what is on disk, fetch nothing
    python -m tools.fetch_contracts --upstream  # ask whether the publisher has moved
    python -m tools.fetch_contracts --refresh   # take the current upstream copy

The default stops at a local copy whose hash matches, which is right for a
verification pass and useless for noticing that a publisher has quietly revised
its document. `--upstream` fetches every one and compares, and writes nothing.
`sefaria-llms.txt` is a living index of a documentation site and moves; the
OpenAPI document is the stable thing.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = REPO_ROOT / "docs" / "api"
README = CONTRACTS / "README.md"

#: The packaged copy LawOS builds its online skill set from. It is a real
#: directory rather than a symlink because a zip cannot carry one, so anything
#: written here has to be written there too or the two drift.
VENDORED = REPO_ROOT / "desktop-skill" / "scripts" / "meturgaman" / "data" / "api"

USER_AGENT = "meturgaman/0.1 (+https://github.com/Oranburg/meturgaman)"


@dataclass(frozen=True)
class Contract:
    """One published contract, as the README records it."""

    name: str
    url: str | None
    sha256: str

    @property
    def path(self) -> Path:
        return CONTRACTS / self.name

    def on_disk_digest(self) -> str | None:
        if not self.path.exists():
            return None
        return hashlib.sha256(self.path.read_bytes()).hexdigest()


# The README is prose for humans first. Rather than invent a parallel machine
# format that could drift out of step with it, this reads the prose. Each entry
# is a bolded filename followed by a bulleted block.
_URL = re.compile(r"^- URL\s+`(?P<url>https?://\S+?)`\s*$", re.MULTILINE)
_SHA = re.compile(r"^- SHA-256\s+`(?P<sha>[0-9a-f]{64})`\s*$", re.MULTILINE)


def read_readme(readme: Path | None = None) -> list[Contract]:
    """Parse the provenance section into Contract records.

    An entry with no backticked URL is kept rather than skipped, because
    `hebcal-openapi.json` is exactly that: committed before anyone wrote down
    where it came from. It can still be verified against its recorded hash, and
    saying so is more useful than pretending it is not there.
    """
    if readme is None:
        readme = README
    if not readme.exists():
        raise FileNotFoundError(f"no contracts README at {readme}")

    text = readme.read_text(encoding="utf-8")
    contracts: list[Contract] = []
    for chunk in re.split(r"(?m)^(?=\*\*`)", text):
        heading = re.match(r"\*\*`([a-z0-9._-]+)`\*\*", chunk)
        if not heading:
            continue
        sha = _SHA.search(chunk)
        if not sha:
            raise ValueError(f"{heading.group(1)} has no SHA-256 recorded")
        url = _URL.search(chunk)
        contracts.append(
            Contract(
                name=heading.group(1),
                url=url.group("url") if url else None,
                sha256=sha.group("sha"),
            )
        )
    if not contracts:
        raise ValueError(f"{readme} named no contracts")
    return contracts


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _write(contract: Contract, payload: bytes) -> None:
    """Write both copies, so the packaged one cannot fall behind silently."""
    contract.path.write_bytes(payload)
    if VENDORED.is_dir():
        shutil.copy2(contract.path, VENDORED / contract.name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fetch_contracts", description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify what is on disk and fetch nothing")
    parser.add_argument("--upstream", action="store_true",
                        help="fetch every contract and report drift, writing nothing")
    parser.add_argument("--refresh", action="store_true",
                        help="take the current upstream copy even where it differs")
    arguments = parser.parse_args(argv)

    contracts = read_readme()
    problems = 0
    changed: list[tuple[Contract, bytes]] = []

    for contract in contracts:
        digest = contract.on_disk_digest()

        if digest == contract.sha256 and not (arguments.refresh or arguments.upstream):
            print(f"verified   {contract.name}")
            continue

        if digest is not None and digest != contract.sha256:
            print(f"MISMATCH   {contract.name}")
            print(f"           on disk  {digest}")
            print(f"           README   {contract.sha256}")
            if not arguments.refresh:
                print("           left alone. --refresh takes the upstream copy.")
                problems += 1
                continue

        if arguments.check:
            if digest is None:
                print(f"MISSING    {contract.name}")
                problems += 1
            continue

        if contract.url is None:
            print(f"no URL     {contract.name}  (recorded without one; cannot refetch)")
            if digest is None:
                problems += 1
            continue

        try:
            payload = fetch(contract.url)
        except (urllib.error.URLError, TimeoutError) as error:
            print(f"FAILED     {contract.name}: {error}")
            problems += 1
            continue

        got = hashlib.sha256(payload).hexdigest()
        if got == contract.sha256:
            if not arguments.upstream:
                _write(contract, payload)
            print(f"{'unmoved   ' if arguments.upstream else 'fetched   '} {contract.name}"
                  f"  matches the recorded hash")
            continue

        if arguments.upstream:
            print(f"MOVED      {contract.name} has been revised since it was committed")
            print(f"           README   {contract.sha256}")
            print(f"           upstream {got}  ({len(payload):,} bytes)")
            print("           nothing written. --refresh takes it.")
            problems += 1
            continue

        if arguments.refresh:
            _write(contract, payload)
            changed.append((contract, payload))
            print(f"refreshed  {contract.name}  upstream has moved")
        else:
            print(f"UPSTREAM   {contract.name} has changed since it was committed")
            print(f"           README   {contract.sha256}")
            print(f"           upstream {got}")
            print("           nothing written. --refresh takes it.")
            problems += 1

    if changed:
        print()
        print("Paste these into docs/api/README.md, then rebuild:")
        for contract, payload in changed:
            print(f"  {contract.name}")
            print(f"    bytes    {len(payload):,}")
            print(f"    SHA-256  {hashlib.sha256(payload).hexdigest()}")
        print()
        print("  python tools/build_skill.py --sync")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
