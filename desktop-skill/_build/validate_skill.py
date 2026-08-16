"""Validate the skill against the packaging rules Claude Desktop enforces.

The rules that actually reject an upload are the frontmatter ones: `name` must
be lowercase letters, numbers and hyphens within 64 characters, and
`description` must fit 1024 characters. The description matters beyond passing
validation, because on Desktop it is the whole trigger mechanism: it is what
decides whether the skill is invoked, and anything it promises that the sandbox
cannot deliver produces a refusal the user was told to expect.
"""

import pathlib
import re

SKILL = pathlib.Path("/Users/sco/.claude/jobs/67abed40/tmp/build/meturgaman")
md = SKILL / "SKILL.md"

text = md.read_text(encoding="utf-8")
lines = text.splitlines()

if not text.startswith("---"):
    raise SystemExit("FAIL: no YAML frontmatter")

end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
front = "\n".join(lines[1:end])
body = lines[end + 1 :]

name = re.search(r"^name:\s*(.+)$", front, re.M).group(1).strip()
desc = re.search(r"^description:\s*(.+)$", front, re.M).group(1).strip()

print(f"name                 {name!r}")
print(f"  valid pattern      {bool(re.fullmatch(r'[a-z0-9-]{1,64}', name))}")
print(f"description length   {len(desc)} chars (limit 1024)")
print(f"  within limit       {len(desc) <= 1024}")
print(f"SKILL.md body lines  {len(body)}")
print(f"SKILL.md total lines {len(lines)}")

# Nothing in the description should promise a capability the map lists as absent.
forbidden = ["read aloud", "hear a passage", "audio", "listen"]
hits = [w for w in forbidden if w in desc.lower()]
print(f"  promises audio     {hits if hits else 'no'}")

# Every reference file the SKILL.md names must exist.
named = set(re.findall(r"`references/([a-z0-9\-]+\.md)`", text))
named |= set(re.findall(r"^\| `([a-z0-9\-]+\.md)`", text, re.M))
present = {p.name for p in (SKILL / "references").glob("*.md")}
print()
print(f"reference files named   {len(named)}")
print(f"reference files present {len(present)}")
missing = named - present
orphan = present - named
print(f"  named but missing     {sorted(missing) if missing else 'none'}")
print(f"  present but unnamed   {sorted(orphan) if orphan else 'none'}")

# Scripts the SKILL.md tells the model to run must exist.
scripts = set(re.findall(r"python3 (scripts/[a-z0-9_]+\.py)", text))
print()
for s in sorted(scripts):
    print(f"  {s:22} {'ok' if (SKILL / s).exists() else 'MISSING'}")
