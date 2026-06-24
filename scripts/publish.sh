#!/usr/bin/env bash
# Paced PyPI upload that respects the new-project creation limit.
#
# PyPI caps how many brand-new projects an account can create (documented 20/hour
# per user, lower for fresh accounts), and EVERY attempt -- including rejected
# ones -- counts. So this script:
#   1. asks PyPI (read-only, free) whether each project already exists,
#   2. only uploads the ones that do not,
#   3. paces real creations under the limit,
#   4. STOPS on the first failure instead of retrying (retries just burn slots).
# --skip-existing keeps every run idempotent; re-run any time to resume.
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
echo "checking $total packages against PyPI (gap ${DELAY}s between new creates)"

created=0
skipped=0
for pkg in $pkgs; do
  dist_name=$(echo "$pkg" | tr '_' '-')
  code=$(curl -s -o /dev/null -w "%{http_code}" "$INDEX/$dist_name/json")
  if [ "$code" = "200" ]; then
    echo "== $dist_name already on PyPI, skipping"
    skipped=$((skipped + 1))
    continue
  fi

  echo "++ creating $dist_name"
  if $PY -m twine upload --skip-existing dist/"$pkg"-*; then
    created=$((created + 1))
    sleep "$DELAY"
  else
    echo ""
    echo "!! upload of $dist_name failed -- almost certainly PyPI's new-project"
    echo "   creation limit (HTTP 429 'Too many new projects created')."
    echo "   Stopping now so we do not burn more attempts against the limit."
    echo "   Created this run: $created. Already live: $skipped."
    echo "   Fix: wait for the window to clear, or request a limit increase at"
    echo "   https://github.com/pypi/support  then re-run (finished ones skip)."
    exit 1
  fi
done

echo "done: $created created this run, $skipped already live ($total total)."
