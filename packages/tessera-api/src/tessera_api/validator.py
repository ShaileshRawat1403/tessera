from __future__ import annotations

from collections import Counter

from tessera_core.models import ValidationFinding

from tessera_api.redact import SECRET_HEADER_NAMES, SECRET_QUERY_NAMES
from tessera_api.schema import ApiRequest


def validate_api_records(records: list[ApiRequest]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    for r in records:
        findings.extend(_validate_one(r))

    # Cross-record: duplicate method+url+body
    seen: dict[tuple[str, str, str | None], int] = Counter()
    for r in records:
        seen[(r.method, r.url, r.body)] += 1
    for (method, url, _body), count in seen.items():
        if count > 1:
            findings.append(
                ValidationFinding(
                    severity="info",
                    code="duplicate_request",
                    message=f"{count} identical requests: {method} {url}",
                    field=None,
                    metadata={"method": method, "url": url, "count": count},
                )
            )

    # Cross-record: surface multiple hosts (not an error, just visibility)
    hosts = sorted({r.host for r in records if r.host})
    if len(hosts) > 1:
        findings.append(
            ValidationFinding(
                severity="info",
                code="multiple_hosts",
                message=f"requests span {len(hosts)} hosts: {', '.join(hosts)}",
                field="host",
                metadata={"hosts": hosts},
            )
        )

    return findings


def _validate_one(r: ApiRequest) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    src = r.metadata.get("source_file", "")

    def f(severity: str, code: str, message: str, field: str | None = None) -> ValidationFinding:
        return ValidationFinding(
            severity=severity, code=code, message=message, field=field,
            metadata={"id": r.id, "source_file": src},
        )

    if r.scheme == "http":
        findings.append(f("warning", "insecure_scheme",
                          f"{r.method} {r.host}{r.path} uses http; credentials and data are sent in cleartext",
                          "scheme"))

    if not r.host:
        findings.append(f("error", "missing_host", "request has no host", "host"))

    # A secret in the query string is worse than in a header: URLs get logged.
    query_redactions = [red for red in r.redactions if red.location.startswith("query:")]
    if query_redactions:
        names = ", ".join(red.location.split(":", 1)[1] for red in query_redactions)
        findings.append(f("warning", "secret_in_url_query",
                          f"secret(s) in URL query ({names}); URLs are commonly logged, prefer a header",
                          "query"))

    if not r.auth.present:
        findings.append(f("info", "no_auth_detected",
                          f"{r.method} {r.host}{r.path} has no detectable auth", "auth"))

    # A secret found by shape in a field whose NAME is not a known secret name
    # is high-signal: a custom auth header or a token hiding in an odd field.
    for red in r.redactions:
        loc = red.location
        if loc.startswith("header:"):
            name = loc.split(":", 1)[1]
            if name not in SECRET_HEADER_NAMES:
                findings.append(f("warning", "secret_in_nonstandard_location",
                                  f"a {red.kind} was detected in header '{name}', which is not a conventional secret header",
                                  "headers"))
        elif loc.startswith("query:"):
            name = loc.split(":", 1)[1]
            if name not in SECRET_QUERY_NAMES:
                findings.append(f("warning", "secret_in_nonstandard_location",
                                  f"a {red.kind} was detected in query param '{name}', which is not a conventional secret name",
                                  "query"))

    return findings
