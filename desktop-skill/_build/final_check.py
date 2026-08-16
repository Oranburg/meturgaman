"""Extract the delivered zip and exercise it, the way Desktop will.

Everything until now tested the staging directory. This tests the artifact that
actually ships: unzip it somewhere new, with a cold HOME and no PYTHONPATH, and
run the commands the SKILL.md promises. Anything that passes here passes because
of what is in the archive, not because of this machine.
"""

import os
import subprocess
import sys
import tempfile
import zipfile

ZIP = "/Users/sco/Downloads/meturgaman-skill.zip"

workdir = tempfile.mkdtemp(prefix="mtg-final-")
with zipfile.ZipFile(ZIP) as zf:
    names = zf.namelist()
    zf.extractall(workdir)

skill = os.path.join(workdir, "meturgaman")

print(f"extracted {len(names)} entries to {skill}")
print(f"SKILL.md at root: {os.path.isfile(os.path.join(skill, 'SKILL.md'))}")
print(f"no __MACOSX:      {not any(n.startswith('__MACOSX') for n in names)}")
print(f"no .DS_Store:     {not any('.DS_Store' in n for n in names)}")
print(f"no symlinks:      {not any(os.path.islink(os.path.join(dp, f))
                                   for dp, _, fs in os.walk(skill) for f in fs)}")
print()

cold_home = tempfile.mkdtemp(prefix="mtg-final-home-")
env = dict(os.environ)
env["HOME"] = cold_home
env["XDG_CACHE_HOME"] = os.path.join(cold_home, ".cache")
env["PYTHONPATH"] = ""
env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"

CASES = [
    (["scripts/probe.py"], "probe"),
    (["scripts/mtg.py", "romanize", "כָּל־הָאָרֶץ"], "romanize (offline)"),
    (["scripts/mtg.py", "detect", "Shabbos and halachah"], "detect (offline)"),
    (["scripts/mtg.py", "law", "tiers"], "law tiers (offline)"),
    (["scripts/mtg.py", "text", "Genesis 1:1"], "text (live)"),
    (["scripts/mtg.py", "topics", "charity"], "topics (live)"),
    (["scripts/mtg.py", "sugya", "Bava Metzia 75b:2"], "sugya (live)"),
]

failures = 0
for argv, label in CASES:
    proc = subprocess.run(
        [sys.executable] + argv,
        cwd=skill,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    crashed = "Traceback" in err
    if crashed:
        failures += 1
    first = (out or err).splitlines()[0][:60] if (out or err) else "(none)"
    status = "CRASH" if crashed else "ok"
    print(f"  {status:6} {label:22} | {first}")
    if crashed:
        print("         " + err.splitlines()[-1][:110])

print(f"\ncrashes: {failures}")
