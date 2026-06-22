from __future__ import annotations

from typing import Any

from tessera_core.models import ValidationFinding

from tessera_config.schema import ConfigKey


def validate_config_records(keys: list[ConfigKey], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    if not keys:
        findings.append(
            ValidationFinding(severity="info", code="no_config_keys",
                              message="no env files or env-var references found", field=None)
        )
        return findings

    for k in keys:
        def f(severity: str, code: str, message: str) -> ValidationFinding:
            return ValidationFinding(severity=severity, code=code, message=message,
                                     field="config", metadata={"key": k.name})

        # A secret value sitting in a committed-style .env is the headline risk.
        if k.is_secret and k.in_env and k.value_preview:
            findings.append(f("warning", "possible_committed_secret",
                              f"{k.name} holds a secret value in a .env file; ensure it is gitignored"))

        # A secret VALUE under a key not named like a secret — name-based
        # detection would miss this (e.g. MY_THING=ghp_...).
        shape = k.metadata.get("secret_by_shape")
        if shape and k.in_env:
            findings.append(f("warning", "secret_value_in_nonsecret_key",
                              f"{k.name} holds a value shaped like a {shape}, though its name is not secret-like"))

        # used in code but not documented anywhere
        if k.in_code and not k.in_example:
            findings.append(f("warning", "missing_in_example",
                              f"{k.name} is used in code but not documented in any .env.example"))

        # set in a real .env but not documented
        if k.in_env and not k.in_example:
            findings.append(f("info", "undocumented_env_key",
                              f"{k.name} is set in .env but not present in any .env.example"))

        # documented but never used or set
        if k.in_example and not k.in_code and not k.in_env:
            findings.append(f("info", "unused_documented_key",
                              f"{k.name} is documented in .env.example but never used in code or set in .env"))

    return findings
