from __future__ import annotations

from typing import Any

from tessera_core.models import ValidationFinding

from tessera_workflow.schema import WorkflowDefinition

_VALID_PROMOTION_RULES = {"after_review", "manual", "auto"}


def validate_workflow_records(
    records: list[WorkflowDefinition],
    options: dict[str, Any],
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    for err in options.get("_parse_errors", []):
        findings.append(ValidationFinding(
            severity="error", code="parse_error",
            message=f"{err.get('file', '?')}: {err['error']}",
            field=None,
        ))

    for wf in records:
        findings.extend(_validate_one(wf))

    return findings


def _validate_one(wf: WorkflowDefinition) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    step_names = {s.name for s in wf.steps}
    step_order = {s.name: i for i, s in enumerate(wf.steps)}

    # no_steps
    if not wf.steps:
        findings.append(ValidationFinding(
            severity="error", code="no_steps",
            message=f"[{wf.name}] workflow defines no steps — nothing to govern.",
            field="steps",
        ))
        return findings  # further checks meaningless

    # missing_recursion_fence
    if wf.recursion_fence is None:
        findings.append(ValidationFinding(
            severity="warning", code="missing_recursion_fence",
            message=(
                f"[{wf.name}] no recursion_fence defined. Without it, the workflow "
                "could recursively modify its own kernel paths."
            ),
            field="recursion_fence",
        ))

    # invalid_promotion_rule
    if wf.promotion_rule not in _VALID_PROMOTION_RULES:
        findings.append(ValidationFinding(
            severity="error", code="invalid_promotion_rule",
            message=(
                f"[{wf.name}] promotion_rule '{wf.promotion_rule}' is not valid. "
                f"Must be one of: {', '.join(sorted(_VALID_PROMOTION_RULES))}."
            ),
            field="promotion_rule",
        ))

    # promotion_without_review
    if wf.promotion_rule == "after_review" and not wf.review_gates:
        findings.append(ValidationFinding(
            severity="warning", code="promotion_without_review",
            message=(
                f"[{wf.name}] promotion_rule is 'after_review' but no review_gates are defined. "
                "The promotion guard has no gate to enforce."
            ),
            field="review_gates",
        ))

    # review_gate_unknown_step + promotion_before_review
    for gate in wf.review_gates:
        if gate.after_step not in step_names:
            findings.append(ValidationFinding(
                severity="error", code="review_gate_unknown_step",
                message=(
                    f"[{wf.name}] review gate references unknown step '{gate.after_step}'. "
                    "Check step names for typos."
                ),
                field="review_gates",
                metadata={"after_step": gate.after_step},
            ))
        else:
            gate_pos = step_order[gate.after_step]
            # Check if any step after the gate produces outputs that feed the last step
            # Simple check: last step must come after the gate
            last_pos = max(step_order.values())
            if gate_pos >= last_pos:
                findings.append(ValidationFinding(
                    severity="warning", code="review_gate_after_last_step",
                    message=(
                        f"[{wf.name}] review gate 'after_step: {gate.after_step}' is at or after "
                        "the last step — nothing executes after the review."
                    ),
                    field="review_gates",
                    metadata={"after_step": gate.after_step},
                ))

    # undefined_adapter
    declared = set(wf.required_adapters)
    for step in wf.steps:
        if declared and step.adapter not in declared:
            findings.append(ValidationFinding(
                severity="warning", code="undefined_adapter",
                message=(
                    f"[{wf.name}] step '{step.name}' uses adapter '{step.adapter}' "
                    "which is not listed in required_adapters."
                ),
                field="required_adapters",
                metadata={"step": step.name, "adapter": step.adapter},
            ))

    # step_missing_outputs
    for step in wf.steps:
        if not step.outputs:
            findings.append(ValidationFinding(
                severity="info", code="step_missing_outputs",
                message=(
                    f"[{wf.name}] step '{step.name}' declares no outputs — "
                    "its results cannot be referenced by downstream steps."
                ),
                field="steps",
                metadata={"step": step.name},
            ))

    # missing_evidence_hash_invariant
    if not wf.evidence_policy.hash_invariant_steps:
        findings.append(ValidationFinding(
            severity="warning", code="missing_evidence_hash_invariant",
            message=(
                f"[{wf.name}] evidence_policy defines no hash_invariant_steps. "
                "Without hash invariants, a patch could be silently swapped between "
                "review and promotion (TOCTOU risk)."
            ),
            field="evidence_policy",
        ))

    # step_undefined_input: input artifact not produced by any earlier step
    produced: set[str] = set()
    for step in wf.steps:
        for inp in step.inputs:
            if inp not in produced:
                findings.append(ValidationFinding(
                    severity="warning", code="step_undefined_input",
                    message=(
                        f"[{wf.name}] step '{step.name}' declares input '{inp}' "
                        "but no earlier step produces it."
                    ),
                    field="steps",
                    metadata={"step": step.name, "input": inp},
                ))
        produced.update(step.outputs)

    # capability_envelope_unknown_step
    envelope_steps = {e.step for e in wf.capability_envelopes}
    for step_name in envelope_steps:
        if step_name not in step_names:
            findings.append(ValidationFinding(
                severity="error", code="capability_envelope_unknown_step",
                message=(
                    f"[{wf.name}] capability_envelope references unknown step '{step_name}'."
                ),
                field="capability_envelopes",
                metadata={"step": step_name},
            ))

    return findings
