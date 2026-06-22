from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from tessera_gha.schema import WorkflowInfo, WorkflowItem

_SHA_RE = re.compile(r"@[0-9a-f]{40}$")
_RISKY_TRIGGERS = {"pull_request_target", "workflow_run"}
# refs that resolve to attacker-controlled PR code
_UNTRUSTED_REF_RE = re.compile(
    r"github\.event\.pull_request\.head\.(?:sha|ref)|github\.head_ref|"
    r"github\.event\.workflow_run\.head_(?:sha|branch)",
    re.IGNORECASE,
)


def _is_write_all(permissions: object) -> bool:
    if permissions == "write-all":
        return True
    if isinstance(permissions, dict):
        return any(str(v).lower() == "write" for v in permissions.values()) and len(permissions) >= 5
    return False
# untrusted event fields that are dangerous when interpolated into run: scripts
_INJECTION_RE = re.compile(
    r"\$\{\{\s*github\.event\.(?:issue\.title|issue\.body|pull_request\.title|"
    r"pull_request\.body|comment\.body|review\.body|head_commit\.message|"
    r"pull_request\.head\.ref|head_ref)\b",
    re.IGNORECASE,
)


def discover_workflows(root: Path) -> list[Path]:
    wf_dir = root / ".github" / "workflows"
    if not wf_dir.is_dir():
        # also accept being pointed straight at a workflows dir or a file
        if root.is_file() and root.suffix in (".yml", ".yaml"):
            return [root]
        if root.name == "workflows" and root.is_dir():
            wf_dir = root
        else:
            return []
    return [p for p in sorted(wf_dir.rglob("*")) if p.suffix in (".yml", ".yaml")]


def _trigger_keys(on: Any) -> list[str]:
    if isinstance(on, str):
        return [on]
    if isinstance(on, list):
        return [str(x) for x in on]
    if isinstance(on, dict):
        return [str(k) for k in on.keys()]
    return []


def load_gha_records(input_path: Path, options: dict[str, Any]) -> list[WorkflowItem]:
    root = input_path if input_path.is_dir() else input_path.parent
    files = discover_workflows(input_path)

    items: list[WorkflowItem] = []
    infos: list[WorkflowInfo] = []
    parse_errors: list[dict[str, str]] = []

    for f in files:
        rel = f.relative_to(root).as_posix() if f.is_relative_to(root) else f.name
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError, UnicodeDecodeError) as exc:
            parse_errors.append({"path": rel, "error": str(exc)})
            continue
        if not isinstance(doc, dict):
            continue

        # NB: PyYAML parses the bare key `on:` as boolean True
        on = doc.get("on", doc.get(True, {}))
        jobs = doc.get("jobs", {}) or {}
        info = WorkflowInfo(
            workflow=rel,
            triggers=_trigger_keys(on),
            jobs=list(jobs.keys()) if isinstance(jobs, dict) else [],
            has_top_permissions="permissions" in doc,
            has_risky_trigger=bool(set(_trigger_keys(on)) & _RISKY_TRIGGERS),
            write_all_permissions=_is_write_all(doc.get("permissions")),
        )

        if isinstance(jobs, dict):
            for job_name, job in jobs.items():
                if not isinstance(job, dict):
                    continue
                if "permissions" not in job and not info.has_top_permissions:
                    info.jobs_without_permissions.append(str(job_name))
                if "timeout-minutes" not in job:
                    info.jobs_without_timeout.append(str(job_name))
                if _is_write_all(job.get("permissions")):
                    info.write_all_permissions = True
                for step in job.get("steps", []) or []:
                    if not isinstance(step, dict):
                        continue
                    name = str(step.get("name", ""))
                    if "uses" in step:
                        action = str(step["uses"])
                        with_block = step.get("with", {}) or {}
                        is_checkout = action.split("@")[0].lower().endswith("actions/checkout") or \
                            action.lower().startswith("actions/checkout")
                        ref = str(with_block.get("ref", "")) if isinstance(with_block, dict) else ""
                        untrusted = bool(_UNTRUSTED_REF_RE.search(ref))
                        persist = ""
                        if isinstance(with_block, dict) and "persist-credentials" in with_block:
                            persist = str(with_block.get("persist-credentials"))
                        if is_checkout and untrusted:
                            info.checks_out_untrusted_code = True
                        items.append(WorkflowItem(
                            workflow=rel, job=str(job_name), step=name, kind="uses",
                            action=action, action_pinned=bool(_SHA_RE.search(action)),
                            is_checkout=is_checkout, checkout_untrusted_ref=untrusted,
                            persist_credentials=persist,
                        ))
                    elif "run" in step:
                        run = str(step["run"])
                        items.append(WorkflowItem(
                            workflow=rel, job=str(job_name), step=name, kind="run",
                            run_injection=bool(_INJECTION_RE.search(run)),
                        ))
        infos.append(info)

    options["_infos"] = infos
    options["_parse_errors"] = parse_errors
    options["_root"] = str(root)
    return items
