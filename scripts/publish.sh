#!/usr/bin/env bash
# Paced PyPI upload that respects the new-project creation limit.
#
# Two kinds of uploads have different rate-limit behaviour:
#   EXISTING project, new version  -- no new-project limit; upload freely.
#   NEW project (first upload)     -- counts against the new-project cap.
#
# This script:
#   1. For each package, asks PyPI whether the project already exists.
#   2. Existing projects: upload immediately (new version is not rate-limited).
#   3. New projects: upload one at a time with a gap, stop on first 429.
#   --skip-existing keeps every run idempotent; re-run any time to resume.
#
#   ./scripts/publish.sh                              # -> real PyPI
#   TWINE_REPOSITORY=testpypi ./scripts/publish.sh    # -> TestPyPI
#
# Env knobs: PY, PUBLISH_DELAY (seconds between new-project creates; default 240
# => ~15/hour, safely under the 20/hour cap).
set -uo pipefail

PY="${PY:-$([ -x .venv/bin/python ] && echo .venv/bin/python || echo python)}"
DELAY="${PUBLISH_DELAY:-240}"
INDEX="${PUBLISH_INDEX_URL:-https://pypi.org/pypi}"

if ! ls dist/*.whl >/dev/null 2>&1; then
  echo "no artifacts in dist/ -- run 'make build' first" >&2
  exit 1
fi

# Distinct package stems from the built wheels, e.g. tesserakit_core.
pkgs=$(ls dist/*.whl | sed -E 's#^dist/##; s/-[0-9].*$//' | sort -u)
total=$(echo "$pkgs" | wc -w | tr -d ' ')
echo "uploading $total packages (gap ${DELAY}s between NEW project creates)"

updated=0
created=0
failed=""

for pkg in $pkgs; do
  dist_name=$(echo "$pkg" | tr '_' '-')
  http_code=$(curl -s -o /dev/null -w "%{http_code}" "$INDEX/$dist_name/json")

  if [ "$http_code" = "200" ]; then
    # Project exists: upload the new version freely (no creation rate limit).
    echo "~~ $dist_name exists — uploading new version"
    if $PY -m twine upload --skip-existing dist/"$pkg"-*; then
      updated=$((updated + 1))
    else
      echo "!! $dist_name version upload failed (unexpected — project already exists)"
      failed="$failed $dist_name"
    fi
  else
    # New project: subject to creation rate limit.
    echo "++ creating $dist_name"
    if $PY -m twine upload --skip-existing dist/"$pkg"-*; then
      created=$((created + 1))
      sleep "$DELAY"
    else
      echo ""
      echo "!! upload of $dist_name failed -- PyPI new-project creation limit."
      echo "   Stopping now so we do not burn more attempts against the limit."
      echo "   Updated: $updated. Created this run: $created."
      [ -n "$failed" ] && echo "   Other failures: $failed"
      echo "   Re-run later; finished packages are skipped automatically."
      exit 1
    fi
  fi
done

echo "done: $updated existing updated, $created new created ($total total)."
[ -n "$failed" ] && echo "WARNING: some version uploads failed: $failed"
