"""Export canonical eval records to framework-native interchange files.

Tessera stays framework-independent: it emits each target's documented file
format rather than importing the framework. A canonical ``EvalRecord`` maps to:

  input    <- input.user_message
  expected <- expected.reference_answer
  context  <- context.source_text (optional)

Targets:
  deepeval      -> goldens JSON (list of {input, expected_output, context})
  ragas         -> JSONL of {question, ground_truth, contexts}
  openai-evals  -> JSONL of {input: [chat messages], ideal}
  langsmith     -> JSONL of {inputs, outputs}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from tessera_evals.schema import EvalRecord

TARGETS = ("deepeval", "ragas", "openai-evals", "langsmith")


def _input_text(rec: EvalRecord) -> str:
    return str(rec.input.get("user_message", "")).strip()


def _expected_text(rec: EvalRecord) -> str:
    return str(rec.expected.get("reference_answer", "")).strip()


def _context_list(rec: EvalRecord) -> list[str]:
    src = str(rec.context.get("source_text", "")).strip()
    return [src] if src else []


def to_deepeval(records: list[EvalRecord]) -> str:
    """DeepEval goldens JSON: a list of golden objects."""
    goldens = [
        {
            "input": _input_text(r),
            "expected_output": _expected_text(r) or None,
            "context": _context_list(r) or None,
            "additional_metadata": {
                "id": r.id,
                "task_type": r.task_type,
                "review_status": r.expected.get("review_status", ""),
            },
        }
        for r in records
    ]
    return json.dumps({"goldens": goldens}, ensure_ascii=False, indent=2) + "\n"


def to_ragas(records: list[EvalRecord]) -> str:
    """RAGAS evaluation dataset as JSONL: question / ground_truth / contexts."""
    lines = []
    for r in records:
        lines.append(
            json.dumps(
                {
                    "question": _input_text(r),
                    "ground_truth": _expected_text(r),
                    "contexts": _context_list(r),
                },
                ensure_ascii=False,
            )
        )
    return "\n".join(lines) + ("\n" if lines else "")


def to_openai_evals(records: list[EvalRecord]) -> str:
    """OpenAI Evals samples.jsonl: {input: [messages], ideal}."""
    lines = []
    for r in records:
        sample: dict[str, Any] = {
            "input": [{"role": "user", "content": _input_text(r)}],
            "ideal": _expected_text(r),
        }
        lines.append(json.dumps(sample, ensure_ascii=False))
    return "\n".join(lines) + ("\n" if lines else "")


def to_langsmith(records: list[EvalRecord]) -> str:
    """LangSmith dataset examples JSONL: {inputs, outputs}."""
    lines = []
    for r in records:
        example = {
            "inputs": {"input": _input_text(r)},
            "outputs": {"expected": _expected_text(r)},
            "metadata": {"id": r.id, "task_type": r.task_type},
        }
        lines.append(json.dumps(example, ensure_ascii=False))
    return "\n".join(lines) + ("\n" if lines else "")


_ADAPTERS: dict[str, tuple[Callable[[list[EvalRecord]], str], str]] = {
    "deepeval": (to_deepeval, "deepeval_goldens.json"),
    "ragas": (to_ragas, "ragas_dataset.jsonl"),
    "openai-evals": (to_openai_evals, "openai_evals_samples.jsonl"),
    "langsmith": (to_langsmith, "langsmith_examples.jsonl"),
}


def load_dataset(path: Path) -> list[EvalRecord]:
    """Read a canonical dataset.jsonl (the evals pack's output) into EvalRecords."""
    records: list[EvalRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(EvalRecord.model_validate_json(line))
    return records


def export(records: list[EvalRecord], target: str, output_dir: Path) -> Path:
    """Write one target's interchange file; return its path."""
    if target not in _ADAPTERS:
        raise ValueError(f"unknown target '{target}'; choose from {', '.join(TARGETS)}")
    render, filename = _ADAPTERS[target]
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / filename
    out.write_text(render(records), encoding="utf-8")
    return out


def export_all(records: list[EvalRecord], output_dir: Path) -> list[Path]:
    return [export(records, t, output_dir) for t in TARGETS]
