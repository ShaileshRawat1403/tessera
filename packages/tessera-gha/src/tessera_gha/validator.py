from __future__ import annotations

from typing import Any

from tessera_core.models import ValidationFinding

from tessera_gha.schema import WorkflowInfo, WorkflowItem

_RISKY_TRIGGERS = {"pull_request_target", "workflow_run"}


def validate_gha_records(items: list[WorkflowItem], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    for err in options.get("_parse_errors", []):
        findings.append(ValidationFinding(severity="error", code="parse_error",
                                          message=f"{err['path']}: {err['error']}", field=None))

    infos: list[WorkflowInfo] = options.get("_infos", [])
    if not items and not infos and not options.get("_parse_errors"):
        findings.append(ValidationFinding(severity="info", code="no_workflows",
                                          message="no GitHub Actions workflows found", field=None))
        return findings

    # per-item
    for it in items:
        where = f"{it.workflow} [{it.job}]"

        def f(severity: str, code: str, message: str) -> ValidationFinding:
            return ValidationFinding(severity=severity, code=code, message=message,
                                     field="gha", metadata={"workflow": it.workflow, "job": it.job})

        if it.kind == "uses" and it.action and not it.action_pinned:
            # third-party actions should be pinned to a commit SHA
            if not it.action.startswith("./") and "docker://" not in it.action:
                findings.append(f("warning", "unpinned_action",
                                  f"{where}: action '{it.action}' is not pinned to a commit SHA"))
        if it.kind == "run" and it.run_injection:
            findings.append(f("error", "script_injection_risk",
                              f"{where}: run script interpolates an untrusted github.event field; use an env var"))

    # per-workflow
    for info in infos:
        def wf(severity: str, code: str, message: str) -> ValidationFinding:
            return ValidationFinding(severity=severity, code=code, message=message,
                                     field="gha", metadata={"workflow": info.workflow})

        if set(info.triggers) & _RISKY_TRIGGERS:
            risky = sorted(set(info.triggers) & _RISKY_TRIGGERS)
            wf_ = wf("warning", "risky_trigger",
                     f"{info.workflow}: uses {risky} which runs with repo secrets on untrusted input")
            findings.append(wf_)
        if not info.has_top_permissions and info.jobs_without_permissions:
            findings.append(wf("info", "missing_permissions",
                               f"{info.workflow}: no explicit permissions; jobs {info.jobs_without_permissions} default to broad scopes"))
        if info.jobs_without_timeout:
            findings.append(wf("info", "missing_timeout",
                               f"{info.workflow}: jobs {info.jobs_without_timeout} have no timeout-minutes"))

    return findings
