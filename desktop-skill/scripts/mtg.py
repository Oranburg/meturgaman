#!/usr/bin/env python3
"""Launcher for the bundled meturgaman package.

The package is vendored whole inside this skill rather than installed, because a
Claude Desktop sandbox may have no package index reachable, and because
meturgaman needs nothing from one: its core is standard library on purpose. That
leaves a single problem, which is that `meturgaman/` sits beside this file
rather than on the import path. This puts its directory first on sys.path and
hands off to the real CLI, so every documented command works unchanged:

    python3 scripts/mtg.py romanize "כָּל־הָאָרֶץ"
    python3 scripts/mtg.py text "Genesis 1:1" --full
    python3 scripts/mtg.py law tiers

Run `python3 scripts/probe.py` before any of this. It reports which hosts the
sandbox can reach, and two behaviours make that report worth having.

The CLI exits 0 even when it refuses. A refusal is a sentence on stdout
beginning "refused:", not a non-zero status, so branching on the exit code reads
a refusal as a success. Read the text.

A refusal can mean the network is gone rather than the citation is bad. With no
egress, reference resolution fails before the fetch does, so a good citation
comes back as "did not resolve" with the real cause on the second line. Never
report a citation as unrecognized without checking the probe first.
"""

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent

# The vendored package lives at scripts/meturgaman/. Putting its parent first on
# sys.path means an unrelated installed copy cannot shadow the bundled one.
sys.path.insert(0, str(HERE))


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {"--diagnose", "--probe"}:
        # One way to classify the environment, and it lives in probe.py.
        import probe

        return probe.main()

    from meturgaman.cli import main as cli_main

    sys.argv[0] = "meturgaman"
    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
