# Tessera release helpers. All free, all offline except `publish*`.
#
# Uses .venv/bin/python if present, otherwise falls back to `python`
# (so the same targets work locally and in CI). Override with `make PY=...`.
PY ?= $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python)
PACKAGES := $(wildcard packages/*/)

.PHONY: help tools install test clean build check publish-test publish

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

tools: ## Install build + upload tooling (build, twine)
	$(PY) -m pip install --quiet --upgrade build twine

install: ## Editable-install every package into the active environment
	$(PY) -m pip install $(foreach p,$(PACKAGES),-e $(p))

test: ## Run the test suite
	$(PY) -m pytest -q

clean: ## Remove build artifacts
	rm -rf dist build packages/*/dist packages/*/build

build: clean tools ## Build a wheel + sdist for all packages into dist/
	@for pkg in $(PACKAGES); do \
		$(PY) -m build --outdir dist "$$pkg" >/tmp/tessera-build.log 2>&1 \
			|| { echo "FAIL building $$pkg"; tail -20 /tmp/tessera-build.log; exit 1; }; \
	done
	@echo "built $$(ls dist | wc -l | tr -d ' ') artifacts into dist/"

check: ## Validate built artifacts (run after `make build`)
	$(PY) -m twine check dist/*

publish-test: ## Upload to TestPyPI (needs a TestPyPI token; dry run)
	PY="$(PY)" TWINE_REPOSITORY=testpypi ./scripts/publish.sh

publish: ## Upload to real PyPI (paced + retried; needs your PyPI token)
	PY="$(PY)" ./scripts/publish.sh
