#!/usr/bin/env bash
# Paced PyPI upload. Uploads one package (wheel + sdist) at a time with a short
# gap between, and backs off + retries on rate limits (HTTP 429). This matters
# only for the very first publish, when PyPI throttles creation of many new
# projects from a fresh account; --skip-existing makes every run idempotent.
#
#   ./scripts/publish.sh                      # -> real PyPI
#   TWINE_REPOSITORY=testpypi ./scripts/publish.sh   # -> TestPyPI
#
# Env knobs: PY, PUBLISH_DELAY (gap between packages, s), PUBLISH_RETRIES.
set -uo pipefail

PY="${PY:-$([ -x .venv/bin/python ] && echo .venv/bin/python || echo python)}"
DELAY="${PUBLISH_DELAY:-12}"
RETRIES="${PUBLISH_RETRIES:-5}"

if ! ls dist/*.whl >/dev/null 2>&1; then
  echo "no artifacts in dist/ — run 'make build' first" >&2
  exit 1
fi

# Distinct package stems, e.g. tesserakit_core, from the built wheels.
pkgs=$(ls dist/*.whl | sed -E 's#^dist/##; s/-[0-9].*$//' | sort -u)
total=$(echo "$pkgs" | wc -w | tr -d ' ')
echo "publishing $total packages (delay ${DELAY}s, up to $RETRIES retries each)"

failed=""
for pkg in $pkgs; do
  attempt=1
  backoff=60
  while true; do
    if $PY -m twine upload --skip-existing dist/"$pkg"-*; then
      break
    fi
    if [ "$attempt" -ge "$RETRIES" ]; then
      echo "!! gave up on $pkg after $RETRIES attempts"
      failed="$failed $pkg"
      break
    fi
    echo ".. $pkg throttled or failed; waiting ${backoff}s (attempt $attempt/$RETRIES)"
    sleep "$backoff"
    backoff=$((backoff * 2))
    attempt=$((attempt + 1))
  done
  sleep "$DELAY"
done

if [ -n "$failed" ]; then
  echo "FAILED:$failed"
  echo "re-run this command; finished packages are skipped automatically."
  exit 1
fi
echo "all $total packages published."
