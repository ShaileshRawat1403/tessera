# tesserakit-i18n

Check translation-key coverage across locale files.

`tessera-i18n` reads JSON locale files, flattens their (possibly nested) keys, picks a reference locale, and reports which keys are missing, extra, or empty in each locale. No network, no execution.

## Check

```bash
tessera i18n check --input locales/ --output ./out/i18n_pack
```

Locale files are JSON; the locale name is taken from the filename (`en.json` → `en`, `messages.fr.json` → `fr`). Nested keys are flattened with dot notation (`menu.file.open`). Common non-locale files (`package.json`, `tsconfig.json`, ...) are skipped.

The reference locale is `en` if present, otherwise the locale with the most keys.

Artifacts written:

```text
locales.jsonl            one LocaleFile per locale (coverage, missing/extra/empty)
index.md                 coverage table
validation_report.md     per-locale findings
coverage_report.md       fully-translated count + average coverage
missing_keys.md          the actual missing keys per locale (actionable)
```

## Findings

- `missing_translations` — keys in the reference absent from a locale
- `extra_keys` — keys in a locale not in the reference (likely stale)
- `empty_values` — keys present but with an empty string
- `low_coverage` — a locale below 90% of the reference keys
- `parse_error`, `no_locales`, `single_locale`
