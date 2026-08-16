#!/bin/bash
# Stage the Claude Desktop skill tree.
#
# Two things make this more than a copy. First, meturgaman/data/ holds three
# symlinks (api, rules, schemes) pointing up out of the package into the repo;
# a zip would either store dangling links or refuse them, so `cp -RL` resolves
# each into real files. Second, __pycache__ directories carry .pyc files
# compiled by the local 3.14 interpreter, which are useless to a sandbox on a
# different version and only inflate the upload, so they are removed.
set -euo pipefail

REPO="/Users/sco/Repos/meturgaman"
STAGE="/Users/sco/.claude/jobs/67abed40/tmp/build/meturgaman"

rm -rf "/Users/sco/.claude/jobs/67abed40/tmp/build"
mkdir -p "$STAGE/scripts" "$STAGE/references"

# The package itself, symlinks resolved into real files.
cp -RL "$REPO/meturgaman" "$STAGE/scripts/meturgaman"

# Drop compiled bytecode and any stray cache.
find "$STAGE" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" -name "*.pyc" -delete 2>/dev/null || true

# The licence travels with the code.
cp "$REPO/LICENSE" "$STAGE/LICENSE"

echo "staged at: $STAGE"
du -sh "$STAGE"
echo "--- tree ---"
find "$STAGE" -type d | sed "s|$STAGE|.|" | sort
echo "--- file count ---"
find "$STAGE" -type f | wc -l
echo "--- dangling symlinks (should be none) ---"
find "$STAGE" -type l | wc -l
