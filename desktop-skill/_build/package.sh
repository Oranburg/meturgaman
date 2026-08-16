#!/bin/bash
# Build the uploadable zip.
#
# Claude Desktop expects a zip containing a single top-level folder whose name
# matches the skill and which holds SKILL.md at its root, so the zip is made
# from the parent of the staged folder rather than from inside it. macOS adds
# .DS_Store and AppleDouble files to anything it touches; -x drops them, since
# they are noise in an upload and __MACOSX entries confuse some extractors.
set -euo pipefail

BUILD="/Users/sco/.claude/jobs/67abed40/tmp/build"
OUT="/Users/sco/Downloads/meturgaman-skill.zip"

rm -f "$OUT"

cd "$BUILD"
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

zip -r -q -X "$OUT" meturgaman -x '*.DS_Store' -x '__MACOSX/*'

echo "wrote: $OUT"
ls -lh "$OUT" | awk '{print "size: " $5}'
echo
echo "--- top of archive ---"
unzip -l "$OUT" | head -20
echo "..."
echo "--- counts ---"
unzip -l "$OUT" | tail -1
