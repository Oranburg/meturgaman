#!/usr/bin/env python3
"""Install the Claude Code copy of this skill into ~/.claude/skills/meturgaman.

The claude.ai account sync carries SKILL.md and nothing else: a session that
reads the synced copy is told to run `scripts/mtg.py` and to consult
`references/quoting-conventions.md`, and neither is there. On 2026-09-17 a
session working on Seth's iA Writer templates reached for the skill, found the
stub, and had to work without the typesetting conventions.

So the machine keeps its own copy: the Claude Code variant of SKILL.md, which
drives the installed `meturgaman` command rather than a vendored script, plus
the reference files, which are the same prose on either surface.

    python3 tools/install_code_skill.py            # say what would change
    python3 tools/install_code_skill.py --write    # install

It also reports whether `meturgaman` is on PATH, because the skill is useless
without it; `ln -s "$(pwd)/.venv/bin/meturgaman" ~/.local/bin/meturgaman` is the
usual fix on the Mac.
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEST = Path.home() / ".claude" / "skills" / "meturgaman"
SKILL = REPO / "skills" / "meturgaman" / "SKILL.md"
REFERENCES = REPO / "desktop-skill" / "references"


def plan() -> list[str]:
    changes = []
    if not SKILL.is_file():
        raise SystemExit(f"the Claude Code SKILL.md is missing: {SKILL}")
    target = DEST / "SKILL.md"
    if not target.exists() or not filecmp.cmp(SKILL, target, shallow=False):
        changes.append(f"SKILL.md -> {target}")
    for source in sorted(REFERENCES.glob("*.md")):
        copy = DEST / "references" / source.name
        if not copy.exists() or not filecmp.cmp(source, copy, shallow=False):
            changes.append(f"references/{source.name} -> {copy}")
    return changes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="copy the files; without it, only say what would change")
    args = ap.parse_args()
    changes = plan()
    for line in changes:
        print(("wrote " if args.write else "would write ") + line)
    if not changes:
        print("the installed skill already matches this checkout")
    if args.write:
        (DEST / "references").mkdir(parents=True, exist_ok=True)
        shutil.copy2(SKILL, DEST / "SKILL.md")
        for source in sorted(REFERENCES.glob("*.md")):
            shutil.copy2(source, DEST / "references" / source.name)
    if shutil.which("meturgaman") is None:
        print("note: `meturgaman` is not on PATH; the skill drives that command", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
