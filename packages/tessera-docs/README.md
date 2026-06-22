# tesserakit-docs

Measure Python docstring coverage for public symbols.

`tessera-docs` parses Python source with the standard-library `ast` module (it never imports or runs the code), inventories every documentable symbol (modules, classes, functions, methods), and reports which public ones lack docstrings.

## Coverage check

```bash
tessera docs coverage --input . --output ./out/docs_pack
tessera docs coverage --input . --include-tests   # also scan test files
```

Test files are excluded by default; pass `--include-tests` to include them.

Artifacts written:

```text
symbols.jsonl            one DocSymbol per symbol (kind, public, has_docstring, line)
index.md                 coverage headline
validation_report.md     missing-docstring findings + low-coverage warning
coverage_report.md       coverage by kind and lowest-coverage files
undocumented.md          every undocumented public symbol with file:line
```

## What counts

- **Public** = name does not start with `_` (so `_private` and `__dunder__` are excluded).
- Symbol kinds: `module`, `class`, `function`, `method`.
- A symbol is documented if `ast.get_docstring` returns a value.

## Findings

- `missing_module_docstring` (info)
- `missing_class_docstring`, `missing_function_docstring`, `missing_method_docstring` (warning)
- `low_doc_coverage` — overall public coverage below 80%
- `parse_error` — a file could not be parsed
- `no_public_symbols` — nothing public found
