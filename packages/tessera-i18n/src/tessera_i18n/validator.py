from __future__ import annotations

from typing import Any

from tessera_core.models import ValidationFinding

from tessera_i18n.schema import LocaleFile

LOW_COVERAGE = 0.90


def validate_i18n_records(locales: list[LocaleFile], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    for err in options.get("_parse_errors", []):
        findings.append(ValidationFinding(severity="error", code="parse_error",
                                          message=f"{err['path']}: {err['error']}", field=None))

    if not locales:
        if not options.get("_parse_errors"):
            findings.append(ValidationFinding(severity="info", code="no_locales",
                                              message="no locale files found", field=None))
        return findings

    if len(locales) == 1:
        findings.append(ValidationFinding(severity="info", code="single_locale",
                                          message="only one locale found; nothing to compare against", field=None))

    ref = options.get("_reference", "")
    for loc in locales:
        def f(severity: str, code: str, message: str) -> ValidationFinding:
            return ValidationFinding(severity=severity, code=code, message=message,
                                     field="i18n", metadata={"locale": loc.locale, "path": loc.path})

        if loc.is_reference:
            if loc.empty_keys:
                findings.append(f("info", "empty_values",
                                  f"reference locale '{loc.locale}' has {len(loc.empty_keys)} empty values"))
            continue

        if loc.missing_keys:
            findings.append(f("warning", "missing_translations",
                              f"'{loc.locale}' is missing {len(loc.missing_keys)} keys present in '{ref}'"))
        if loc.extra_keys:
            findings.append(f("info", "extra_keys",
                              f"'{loc.locale}' has {len(loc.extra_keys)} keys not in '{ref}'"))
        if loc.empty_keys:
            findings.append(f("info", "empty_values",
                              f"'{loc.locale}' has {len(loc.empty_keys)} empty values"))
        if loc.coverage < LOW_COVERAGE:
            findings.append(f("warning", "low_coverage",
                              f"'{loc.locale}' coverage is {loc.coverage*100:.0f}% (below {int(LOW_COVERAGE*100)}%)"))

    return findings
