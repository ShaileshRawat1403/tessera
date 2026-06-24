# Publishing to PyPI

Tessera ships 24 distributions (`tesserakit-*`). There are two ways to publish,
both free:

- **Automated (recommended):** push a `v*` tag, and GitHub Actions builds and
  publishes everything via Trusted Publishing. No tokens stored anywhere.
- **Manual:** one `make` command from your laptop, using your PyPI token.

The first publish is manual (the projects do not exist on PyPI yet). After that,
tagging is the whole release.

---

## Manual publish (the first release)

Everything is wrapped in the `Makefile`:

```bash
cd "<repo>"
make build          # clean + build wheel & sdist for all 24 packages into dist/
make check          # twine check dist/*  (expect: 48 PASSED)
make publish        # twine upload --skip-existing dist/*
#   username: __token__
#   password: <your pypi-... token>
```

`make publish` is irreversible (a published version cannot be re-used) and needs
**your** PyPI token, so run it yourself. `--skip-existing` makes it safe to
re-run: it uploads only what is not already on PyPI.

Tip: avoid retyping the token for all 24 uploads:

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-XXXX...   # your full token, including the pypi- prefix
make publish
```

### The new-project rate limit (expect this on a fresh account)

PyPI caps how many brand-new projects an account can create (documented as
20/hour per user, but fresh accounts hit a stricter, lower wall as anti-spam).
With 24 new projects at once you *will* hit `429 Too many new projects created`.
Two things matter:

- **Every attempt counts, including rejected ones.** Do not retry into a 429 and
  do not loop with backoff; that keeps the limiter pinned. `scripts/publish.sh`
  checks PyPI first and only attempts genuinely-new projects, paces them, and
  stops on the first failure for exactly this reason.
- **The dependable fix is a limit increase.** Open a request at
  https://github.com/pypi/support/issues/new/choose ("limit increase"), explain
  it is one monorepo of related `tesserakit-*` packages, and PyPI staff raise the
  ceiling (usually a day or two). Then `make publish` finishes the rest cleanly.

This only bites the first publish. Once the projects exist, version bumps and the
tag-triggered CI workflow are not "new project" creates and are not limited.

### Optional dry run on TestPyPI

Needs a separate TestPyPI account + token (https://test.pypi.org/).

```bash
make publish-test   # uploads to TestPyPI
python -m pip install -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ tesserakit-app
tessera plugins
```

(`--extra-index-url` lets TestPyPI packages pull their real deps, typer/rich/
pydantic, from real PyPI.)

---

## Automated publish (every release after the first)

`.github/workflows/release.yml` runs on any pushed `v*` tag: it builds all 24
packages and publishes them to PyPI using **Trusted Publishing (OIDC)**. GitHub
proves the workflow's identity to PyPI, so there is no token to create, store, or
rotate.

Once it is set up, cutting a release is just:

```bash
make build && make check          # optional local sanity check
git tag v0.4.0 && git push --tags # CI does the rest
```

### Trusted Publishing setup (one-time, per project)

Trusted Publishing trusts a specific repo + workflow + environment. You register
that trust on each project. Do it **after** the first manual publish, when the 24
projects already exist:

For each `tesserakit-*` project on PyPI → *Manage* → *Publishing* → *Add a new
publisher* → **GitHub**, with the same four values every time:

| Field           | Value                       |
| --------------- | --------------------------- |
| Owner           | `ShaileshRawat1403`         |
| Repository      | `tessera`                   |
| Workflow name   | `release.yml`               |
| Environment     | `pypi`                      |

The `pypi` environment is created automatically on the first workflow run; you
can later add required reviewers/branch rules to it under repo *Settings* →
*Environments* for an extra approval gate before publish.

> 24 registrations is tedious but one-time. If you would rather not register
> each project, swap the workflow's `pypa/gh-action-pypi-publish` step to use a
> `PYPI_API_TOKEN` repo secret instead (less future-proof: a long-lived token
> lives in GitHub and should be rotated).

---

## Verify

```bash
pip install tesserakit-app          # pulls in tesserakit-core et al.
tessera plugins                     # should list the job packs
tessera run --input . --output run  # smoke test on a project
```

## Notes

- Distribution names are `tesserakit-*`; import names stay `tessera_*` and the
  CLI stays `tessera`. So `pip install tesserakit-evals` provides `tessera_evals`
  and contributes to the `tessera` CLI.
- Do not commit tokens. `twine` reads them interactively or from `~/.pypirc` /
  `TWINE_PASSWORD`. Trusted Publishing avoids the question entirely.
