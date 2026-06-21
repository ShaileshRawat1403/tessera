"""Run the applicable job packs over a project and summarize the run."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tessera_core.models import RunContext
from tessera_core.plugins import load_jobpacks
from tessera_core.workspace import write_json

from tessera_app.detect import Detection, detect_packs


@dataclass
class PackResult:
    pack: str
    reason: str
    ok: bool
    record_count: int = 0
    finding_count: int = 0
    error_count: int = 0
    artifacts: list[str] = field(default_factory=list)
    output_dir: str = ""
    error: str = ""


def run_project(project: Path, output_dir: Path, only: list[str] | None = None) -> list[PackResult]:
    """Detect applicable packs, run each into output_dir/<pack>/, and summarize."""
    detections = detect_packs(project)
    if only:
        detections = [d for d in detections if d.pack in only]

    packs = load_jobpacks()
    results: list[PackResult] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for det in detections:
        pack = packs.get(det.pack)
        if pack is None:
            results.append(PackResult(det.pack, det.reason, ok=False, error="pack not installed"))
            continue
        pack_out = output_dir / det.pack
        ctx = RunContext(job_name=det.pack, output_dir=pack_out)
        try:
            artifacts = pack.run(input_path=det.input_path, ctx=ctx, options=dict(det.options))
            findings = ctx.metadata.get("findings", []) or []
            errors = sum(1 for f in findings if getattr(f, "severity", "") == "error")
            results.append(
                PackResult(
                    pack=det.pack,
                    reason=det.reason,
                    ok=True,
                    record_count=ctx.metadata.get("record_count", 0),
                    finding_count=ctx.metadata.get("finding_count", len(findings)),
                    error_count=errors,
                    artifacts=[a.name for a in artifacts],
                    output_dir=str(pack_out),
                )
            )
        except Exception as exc:  # keep the run going; record the failure
            results.append(PackResult(det.pack, det.reason, ok=False, error=str(exc), output_dir=str(pack_out)))

    _write_manifest(project, output_dir, results)
    return results


def _write_manifest(project: Path, output_dir: Path, results: list[PackResult]) -> None:
    manifest: dict[str, Any] = {
        "project": str(project),
        "packs": [
            {
                "pack": r.pack,
                "reason": r.reason,
                "ok": r.ok,
                "record_count": r.record_count,
                "finding_count": r.finding_count,
                "error_count": r.error_count,
                "artifacts": r.artifacts,
                "output_dir": r.output_dir,
                "error": r.error,
            }
            for r in results
        ],
    }
    write_json(output_dir / "run_manifest.json", manifest)
