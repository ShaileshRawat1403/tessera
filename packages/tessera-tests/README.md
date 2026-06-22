# tesserakit-tests

Audit a Python test suite for hygiene problems.

`tessera-tests` parses test files with `ast` (never imports or runs them), inventories the test functions and methods, and surfaces the tests that aren't really protecting anything: tests with no assertions, and tests that are skipped or expected to fail.

## Audit

```bash
tessera tests audit --input . --output ./out/tests_pack
```

Test discovery follows pytest/unittest conventions: files named `test_*.py` / `*_test.py` or under a `tests/` directory; functions named `test*`; methods named `test*` inside `Test*` classes.

Artifacts written:

```text
tests.jsonl              one TestCase per test (asserts, skip/xfail/param flags)
index.md                 the test inventory
validation_report.md     hygiene findings
coverage_report.md       counts (skipped/xfail/parametrized/no-assert) + per-file
not_running.md           skipped + xfail tests (present but not protecting anything)
```

## What it detects

- **Assertions**: `assert` statements, `self.assert*` calls, and `pytest.raises`/`warns` blocks.
- **Markers**: `@pytest.mark.skip` / `skipif`, `xfail`, `parametrize` (matched on the decorator name).

## Findings

- `no_assertion_test` (warning) — a test with zero assertions that isn't skipped/xfail
- `skipped_test` (info) — a skipped test
- `xfail_test` (info) — an expected-failure test
- `parse_error`, `no_tests_found`
