#!/usr/bin/env python3
"""Build the uploadable skill packages, and prove each one works.

    python tools/build_skill.py                    # both surfaces, staged, packed, tested
    python tools/build_skill.py --surface desktop  # one of them
    python tools/build_skill.py --sync             # also refresh the vendored copy on disk
    python tools/build_skill.py --keep             # leave the staging trees in place
    python tools/build_skill.py --no-test          # skip the extract-and-run pass

`python` rather than `python3`, because this runs on the maintainer's own machine
and Windows has no `python3` on the path: it ships a `python3.exe` App Execution
Alias that opens the Microsoft Store instead of an interpreter, so `python3` there
fails with advice about the Store rather than anything about this repository. The
`python3` inside the SKILL.md files is right and stays, because those run in a
Linux sandbox where `python3` is the name there is.

Two surfaces, one tree
----------------------
`desktop-skill/` is the whole package: SKILL.md, ten reference files, the
launcher, the probe, the API reader. `claude-ai/skill/` is an overlay of the
handful of pages that differ, and the claude.ai build lays it over the top, so a
file present in both wins from the overlay. Forking the shared prose would mean a
correction to one copy silently missing the other, and the manifest this prints
says which side every file came from.

Why this is Python and not shell
--------------------------------
The two scripts that first built the Desktop package were bash with one
developer's home directory written into them, so they ran on exactly one machine.
Everything here is derived from this file's own location.

Three things it does that a copy would not.

**It resolves `meturgaman/data/`.** Three entries there (`api`, `rules`,
`schemes`) are symlinks pointing up out of the package into the repository. A zip
cannot carry one usefully, and on a Windows checkout without symlink support git
leaves them as ordinary files whose contents are the target path. Both shapes are
resolved into real directories here, so the archive is the same either way.

**It watches the vendored copy for drift.** `desktop-skill/scripts/meturgaman/`
is committed, because LawOS builds its online skill set by copying that directory
whole and a zip cannot hold a symlink. Committed means it can fall behind the
package it was copied from. Every build compares the two and says so; `--sync`
writes the fresh vendor back.

**It tests the artifact rather than the staging tree.** Each zip is extracted
somewhere new, with a cold HOME and an empty PYTHONPATH, and the commands its
SKILL.md promises are run there. Anything that passes does so because of what is
in the archive.
"""

from __future__ import annotations

import argparse
import filecmp
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent

PACKAGE = REPO / "meturgaman"
DESKTOP = REPO / "desktop-skill"
OVERLAY = REPO / "claude-ai" / "skill"
VENDORED = DESKTOP / "scripts" / "meturgaman"
DIST = REPO / "dist"

SKILL_NAME = "meturgaman"

#: claude.ai rejects an upload on either of these, and the description is also
#: the entire trigger mechanism, so it is worth watching rather than merely
#: passing.
NAME_PATTERN = re.compile(r"[a-z0-9-]{1,64}")
DESCRIPTION_LIMIT = 1024

SURFACES = {
    "desktop": {
        "layers": (("desktop-skill", DESKTOP),),
        "output": "meturgaman-desktop-skill.zip",
    },
    "claude-ai": {
        "layers": (("desktop-skill", DESKTOP), ("claude-ai/skill", OVERLAY)),
        "output": "meturgaman-claude-ai-skill.zip",
    },
}

NOISE_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "_build"}
NOISE_SUFFIXES = {".pyc", ".pyo"}
NOISE_NAMES = {".DS_Store"}


# ---------------------------------------------------------------------------
# vendoring


def _clean(tree: pathlib.Path) -> None:
    """Drop bytecode and desktop clutter, which are noise in an upload.

    Compiled bytecode is doubly useless: it was produced by whatever interpreter
    the maintainer happens to run, the sandbox runs 3.11, and a mismatched `.pyc`
    is ignored rather than used. It only inflates the archive.
    """
    for path in sorted(tree.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir() and path.name in NOISE_DIRS:
            shutil.rmtree(path, ignore_errors=True)
        elif path.is_file() and (
            path.suffix in NOISE_SUFFIXES or path.name in NOISE_NAMES
        ):
            path.unlink(missing_ok=True)


def _resolve_data_entry(entry: pathlib.Path) -> pathlib.Path | None:
    """Return the real directory behind `meturgaman/data/<entry>`.

    Three shapes turn up. A real directory, on a machine where the package was
    vendored rather than checked out. A genuine symlink, on macOS and Linux. And
    a small text file holding a relative path, which is what git writes on a
    Windows checkout with `core.symlinks=false`; that file is indistinguishable
    from a one-line data file except by trying the path it names.
    """
    if entry.is_dir() and not entry.is_symlink():
        return entry
    if entry.is_symlink():
        target = pathlib.Path(os.path.realpath(entry))
        return target if target.is_dir() else None
    if entry.is_file() and entry.stat().st_size < 256:
        text = entry.read_text(encoding="utf-8", errors="replace").strip()
        if text and "\n" not in text:
            target = (entry.parent / text).resolve()
            if target.is_dir():
                return target
    return None


def vendor(destination: pathlib.Path) -> None:
    """Copy the package with `data/` resolved into real directories."""
    shutil.copytree(
        PACKAGE,
        destination,
        symlinks=False,
        ignore=shutil.ignore_patterns(*NOISE_DIRS, "*.pyc", ".DS_Store"),
    )
    data = PACKAGE / "data"
    if not data.is_dir():
        return
    for entry in sorted(data.iterdir()):
        target = _resolve_data_entry(entry)
        staged = destination / "data" / entry.name
        if target is None:
            if not staged.is_dir():
                raise SystemExit(
                    f"cannot resolve {entry} into a directory; the build would "
                    f"ship a dangling link"
                )
            continue
        if staged.is_dir():
            shutil.rmtree(staged)
        elif staged.exists():
            staged.unlink()
        shutil.copytree(target, staged)


def _differences(left: pathlib.Path, right: pathlib.Path, prefix: str = "") -> list[str]:
    """Every file that differs between two trees, by relative path."""
    comparison = filecmp.dircmp(left, right, ignore=list(NOISE_DIRS) + [".DS_Store"])
    out = [f"{prefix}{name}  (only in the fresh vendor)" for name in comparison.left_only]
    out += [f"{prefix}{name}  (only on disk)" for name in comparison.right_only]
    out += [f"{prefix}{name}  (contents differ)" for name in comparison.diff_files]
    for name in comparison.common_dirs:
        out += _differences(left / name, right / name, f"{prefix}{name}/")
    return out


def check_vendored(fresh: pathlib.Path, sync: bool) -> list[str]:
    """Compare the committed vendored copy against a fresh one.

    `desktop-skill/scripts/meturgaman/` is committed because LawOS's online skill
    build copies that directory whole and cannot follow a symlink. Committed means
    it can fall behind, silently, and the thing that would then ship is a stale
    library under a current SKILL.md.
    """
    if not VENDORED.is_dir():
        return ["desktop-skill/scripts/meturgaman/ does not exist"]
    drift = _differences(fresh, VENDORED)
    if drift and sync:
        shutil.rmtree(VENDORED)
        shutil.copytree(fresh, VENDORED)
        return []
    return drift


# ---------------------------------------------------------------------------
# staging


def stage(destination: pathlib.Path, surface: str) -> list[tuple[str, str]]:
    """Assemble one skill tree. Returns (path, provenance) for every file."""
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    provenance: dict[str, str] = {}

    vendor(destination / "scripts" / SKILL_NAME)
    for path in (destination / "scripts" / SKILL_NAME).rglob("*"):
        if path.is_file():
            provenance[path.relative_to(destination).as_posix()] = "package"

    for label, root in SURFACES[surface]["layers"]:
        for source in sorted(root.rglob("*")):
            if source.is_dir() or source.name in NOISE_NAMES:
                continue
            relative = source.relative_to(root)
            if relative.parts[0] in NOISE_DIRS:
                continue
            # The vendored library is assembled above, from the package itself,
            # rather than copied out of whichever layer happens to hold a copy.
            if relative.parts[:2] == ("scripts", SKILL_NAME):
                continue
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            provenance[relative.as_posix()] = label

    shutil.copy2(REPO / "LICENSE", destination / "LICENSE")
    provenance["LICENSE"] = "repo root"

    _clean(destination)
    return sorted(provenance.items())


# ---------------------------------------------------------------------------
# validation


def validate(skill: pathlib.Path) -> list[str]:
    """Check what claude.ai checks, plus what the SKILL.md promises exists."""
    problems: list[str] = []
    md = skill / "SKILL.md"
    if not md.is_file():
        return ["SKILL.md is missing"]

    text = md.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not text.startswith("---"):
        return ["SKILL.md has no YAML frontmatter"]
    try:
        end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return ["SKILL.md frontmatter is never closed"]
    front = "\n".join(lines[1:end])

    name_match = re.search(r"^name:\s*(.+)$", front, re.M)
    desc_match = re.search(r"^description:\s*(.+)$", front, re.M)
    if not name_match or not desc_match:
        return ["SKILL.md frontmatter needs both name and description"]

    name = name_match.group(1).strip()
    description = desc_match.group(1).strip().strip('"')
    print(f"    name                {name!r}")
    if not NAME_PATTERN.fullmatch(name):
        problems.append(f"name {name!r} is not 1-64 characters of [a-z0-9-]")
    for reserved in ("anthropic", "claude"):
        if reserved in name:
            problems.append(f"name may not contain the reserved word {reserved!r}")
    print(f"    description         {len(description)} chars (limit {DESCRIPTION_LIMIT})")
    if len(description) > DESCRIPTION_LIMIT:
        problems.append(f"description is {len(description)} characters, over the limit")
    if "<" in name or "<" in description:
        problems.append("name and description may not contain XML tags")
    print(f"    SKILL.md            {len(lines)} lines")

    named = set(re.findall(r"`references/([a-z0-9._-]+\.md)`", text))
    named |= set(re.findall(r"^\| `([a-z0-9._-]+\.md)`", text, re.M))
    present = {p.name for p in (skill / "references").glob("*.md")}
    print(f"    references          {len(present)} present, {len(named)} named")
    for missing in sorted(named - present):
        problems.append(f"SKILL.md names references/{missing}, absent from the build")
    for orphan in sorted(present - named):
        problems.append(f"references/{orphan} ships but no SKILL.md line sends anyone to it")

    for script in sorted(set(re.findall(r"python3 (scripts/[a-z0-9_]+\.py)", text))):
        ok = (skill / script).is_file()
        print(f"    {script:20}{'ok' if ok else 'MISSING'}")
        if not ok:
            problems.append(f"SKILL.md tells the model to run {script}, which is absent")

    return problems


# ---------------------------------------------------------------------------
# packing and proving


def pack(staged: pathlib.Path, output: pathlib.Path) -> None:
    """One top-level folder named for the skill, with SKILL.md at its root."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(staged.rglob("*")):
            if path.is_file():
                arcname = pathlib.PurePosixPath(SKILL_NAME) / path.relative_to(
                    staged
                ).as_posix()
                archive.write(path, str(arcname))


CASES = (
    (["scripts/probe.py"], "probe"),
    (["scripts/mtg.py", "romanize", "כָּל־הָאָרֶץ"], "romanize (offline)"),
    (["scripts/mtg.py", "detect", "Shabbos and halachah"], "detect (offline)"),
    (["scripts/mtg.py", "law", "tiers"], "law tiers (offline)"),
    (["scripts/api.py", "--index"], "api index (offline)"),
    (["scripts/api.py", "api/v3/texts"], "api parameters (offline)"),
    (["scripts/api.py", "--responses", "api/ref/"], "api responses (offline)"),
    (["scripts/api.py", "--docs", "passages"], "api docs index (offline)"),
    (["scripts/mtg.py", "text", "Genesis 1:1"], "text (live)"),
    (["scripts/mtg.py", "topics", "charity"], "topics (live)"),
)


def prove(archive: pathlib.Path) -> int:
    """Extract the zip somewhere new and run what the SKILL.md promises."""
    workdir = pathlib.Path(tempfile.mkdtemp(prefix="mtg-proof-"))
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        zf.extractall(workdir)
    skill = workdir / SKILL_NAME

    print(f"    extracted           {len(names)} entries")
    print(f"    SKILL.md at root    {(skill / 'SKILL.md').is_file()}")
    print(f"    no __MACOSX         {not any(n.startswith('__MACOSX') for n in names)}")
    print(f"    no .DS_Store        {not any('.DS_Store' in n for n in names)}")
    print(f"    no bytecode         {not any(n.endswith('.pyc') for n in names)}")
    print()

    home = pathlib.Path(tempfile.mkdtemp(prefix="mtg-proof-home-"))
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["XDG_CACHE_HOME"] = str(home / ".cache")
    env["PYTHONPATH"] = ""
    env["PYTHONIOENCODING"] = "utf-8"

    crashes = 0
    for argv, label in CASES:
        result = subprocess.run(
            [sys.executable, *argv],
            cwd=skill,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        crashed = "Traceback" in err
        crashes += crashed
        first = (out or err).splitlines()[0][:56] if (out or err) else "(no output)"
        print(f"    {'CRASH' if crashed else 'ok':6}{label:24}| {first}")
        if crashed:
            print("           " + err.splitlines()[-1][:108])

    shutil.rmtree(workdir, ignore_errors=True)
    shutil.rmtree(home, ignore_errors=True)
    return crashes


def build(surface: str, args) -> int:
    print(f"\n=== {surface} " + "=" * (56 - len(surface)))
    staging = pathlib.Path(tempfile.mkdtemp(prefix=f"mtg-{surface}-")) / SKILL_NAME

    provenance = stage(staging, surface)
    counts: dict[str, int] = {}
    for _, source in provenance:
        counts[source] = counts.get(source, 0) + 1
    print("  staged")
    for source, count in sorted(counts.items()):
        print(f"    {count:5} files from {source}")
    for relative, source in provenance:
        if source not in ("package",):
            print(f"          {source:16} {relative}")

    print("  validating")
    problems = validate(staging)
    if problems:
        print("\n  FAILED")
        for problem in problems:
            print(f"    - {problem}")
        return 1

    output = DIST / SURFACES[surface]["output"]
    pack(staging, output)
    print(f"  packed  {output.name}  {output.stat().st_size / 1024:.0f} KB")

    crashes = 0
    if not args.no_test:
        print("  proving the archive")
        crashes = prove(output)
        print(f"    crashes: {crashes}")

    if args.keep:
        print(f"  staging kept at {staging}")
    else:
        shutil.rmtree(staging.parent, ignore_errors=True)
    return 1 if crashes else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the meturgaman skill packages.")
    parser.add_argument(
        "--surface", choices=(*SURFACES, "both"), default="both",
        help="which package to build (default: both)",
    )
    parser.add_argument("--sync", action="store_true",
                        help="rewrite desktop-skill/scripts/meturgaman/ from the package")
    parser.add_argument("--keep", action="store_true", help="leave the staging trees")
    parser.add_argument("--no-test", action="store_true",
                        help="skip the extract-and-run pass")
    args = parser.parse_args()

    print("vendored copy on disk")
    fresh = pathlib.Path(tempfile.mkdtemp(prefix="mtg-vendor-")) / SKILL_NAME
    vendor(fresh)
    drift = check_vendored(fresh, args.sync)
    if drift:
        print(f"  DRIFT: {len(drift)} differences from the package")
        for line in drift[:20]:
            print(f"    {line}")
        if len(drift) > 20:
            print(f"    ... and {len(drift) - 20} more")
        print("  LawOS copies that directory whole. Run with --sync to refresh it.")
    elif args.sync:
        print("  synced from meturgaman/")
    else:
        print("  matches meturgaman/")
    shutil.rmtree(fresh.parent, ignore_errors=True)

    surfaces = list(SURFACES) if args.surface == "both" else [args.surface]
    failures = sum(build(surface, args) for surface in surfaces)

    print()
    if drift and not args.sync:
        print("note: desktop-skill/scripts/meturgaman/ is stale on disk; the zips")
        print("      above were built from meturgaman/ and are correct regardless.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
