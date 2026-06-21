from __future__ import annotations

from typing import Any

_GENERIC = {
    "task_type": "generic",
    "dimensions": ["correctness", "completeness", "groundedness", "safety_or_policy_fit"],
    "must": [
        "answer the user request directly",
        "use available context when context is provided",
        "avoid unsupported claims",
    ],
    "must_not": [
        "invent facts not present in the input or context",
        "ignore explicit user constraints",
    ],
}

_TEMPLATES: dict[str, dict[str, Any]] = {
    "generic": _GENERIC,
    "customer_support": {
        "task_type": "customer_support",
        "dimensions": ["correctness", "completeness", "tone_appropriate", "policy_fit"],
        "must": [
            "acknowledge the customer issue",
            "resolve or route the request",
            "follow documented policy when available",
        ],
        "must_not": [
            "promise outcomes outside policy",
            "blame the customer",
            "leave the request unanswered",
        ],
    },
    "rag_qa": {
        "task_type": "rag_qa",
        "dimensions": ["correctness", "groundedness", "citation_present", "completeness"],
        "must": [
            "ground every claim in the retrieved context",
            "answer only what the context supports",
            "cite the source span when a citation field is expected",
        ],
        "must_not": [
            "answer beyond the retrieved context",
            "fabricate citations",
        ],
    },
    "summarization": {
        "task_type": "summarization",
        "dimensions": ["faithfulness", "coverage", "concision", "structure"],
        "must": [
            "preserve all key facts from the source",
            "stay within any length constraint provided",
        ],
        "must_not": [
            "introduce facts not in the source",
            "drop facts the user flagged as important",
        ],
    },
    "classification": {
        "task_type": "classification",
        "dimensions": ["label_correct", "format_valid"],
        "must": [
            "output exactly one label from the allowed set",
            "match the requested output format",
        ],
        "must_not": [
            "invent labels outside the allowed set",
            "return prose when a single label is requested",
        ],
    },
    "agent_workflow": {
        "task_type": "agent_workflow",
        "dimensions": ["goal_achieved", "tool_selection_correct", "step_efficiency", "safety"],
        "must": [
            "achieve the stated goal",
            "use the minimum number of tool calls",
            "stop when the goal is reached",
        ],
        "must_not": [
            "call tools the user has not authorized",
            "loop after the goal is reached",
        ],
    },
}


def default_rubric(task_type: str) -> dict[str, Any]:
    return _TEMPLATES.get(task_type, _GENERIC)


def supported_task_types() -> list[str]:
    return sorted(_TEMPLATES.keys())
