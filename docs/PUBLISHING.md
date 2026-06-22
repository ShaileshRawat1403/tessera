# Publishing to PyPI

The 24 packages are built, validated, and ready to publish as `tesserakit-*`
(version `0.3.1`). The build artifacts live in `dist/` (48 files: a wheel + an
sdist per package). All pass `twine check`. All 24 names are available on PyPI.

The actual upload is the one step that requires **your** PyPI account and an API
token, and it is irreversible (a published version cannot be re-used). Do it
yourself with the commands below.

## 1. Create accounts + tokens

- PyPI: https://pypi.org/account/register/ → Account settings → **API tokens** →
  "Add API token" (scope: *Entire account* for the first upload; you can narrow
  to per-project tokens afterward).
- (Recommended) TestPyPI for a dry run: https://test.pypi.org/account/register/
  → its own API token.

## 2. Rebuild (so dist matches the current tree)

```bash
cd "<repo>"
rm -rf dist
for pkg in packages/*/; do python -m build --outdir dist "$pkg"; done
python -m twine check dist/*          # expect: 48 PASSED
```

## 3. Dry run on TestPyPI (recommended)

```bash
python -m twine upload --repository testpypi dist/*
# username: __token__
# password: <your TestPyPI token>
```

Then verify an install resolves (core must be present for the others):

```bash
python -m pip install -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ tesserakit-app
tessera plugins
```

(The `--extra-index-url` lets TestPyPI packages pull their real deps —
typer/rich/pydantic — from real PyPI.)

## 4. Publish for real

```bash
python -m twine upload dist/*
# username: __token__
# password: <your PyPI token>
```

`twine upload dist/*` uploads all 24 packages in one go. Order does not matter
for the upload; for a later *install* to resolve, `tesserakit-core` must be
present, which it will be after this command.

## 5. Verify

```bash
pip install tesserakit-app          # pulls in tesserakit-core et al.
tessera plugins                     # should list the job packs
tessera run --input . --output run  # smoke test on a project
```

## Notes

- Distribution names are `tesserakit-*`; import names stay `tessera_*` and the
  CLI stays `tessera`. So `pip install tesserakit-evals` provides `tessera_evals`
  and contributes to the `tessera` CLI.
- After the first publish, switch to **per-project API tokens** and consider a
  GitHub Actions release workflow with **Trusted Publishing** (OIDC) so future
  releases need no long-lived token.
- Do not commit tokens. `twine` reads them interactively or from
  `~/.pypirc` / `TWINE_PASSWORD`.
