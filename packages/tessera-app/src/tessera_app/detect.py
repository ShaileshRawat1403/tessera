"""Detect which job packs apply to a project directory."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_IGNORE = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    "dist", "build", ".tox", "target", ".mypy_cache", ".ruff_cache",
}


@dataclass
class Detection:
    pack: str
    reason: str
    input_path: Path
    options: dict[str, Any] = field(default_factory=dict)


def _walk(root: Path):
    for p in root.rglob("*"):
        if any(part in _IGNORE for part in p.relative_to(root).parts):
            continue
        yield p


def detect_packs(project: Path) -> list[Detection]:
    """Return the detections that apply to ``project`` (a directory)."""
    project = project if project.is_dir() else project.parent
    files = [p for p in _walk(project) if p.is_file()]
    names = {p.name.lower() for p in files}
    detections: list[Detection] = []

    def any_suffix(*suffixes: str) -> bool:
        return any(p.suffix.lower() in suffixes for p in files)

    def any_named(predicate) -> bool:
        return any(predicate(p) for p in files)

    # prompts
    if any_named(lambda p: p.name.endswith(".prompt.md") or p.name.lower() == "prompt.md"):
        detections.append(Detection("prompts", "found .prompt.md / PROMPT.md files", project))

    # skills
    if "skill.md" in names:
        detections.append(Detection("skills", "found SKILL.md files", project))

    # recipes
    if any_named(lambda p: p.name.endswith(".recipe.md") or p.name.lower() == "recipe.md"):
        detections.append(Detection("recipes", "found .recipe.md / RECIPE.md files", project))

    # api (curl files)
    if any_suffix(".curl") or any_named(lambda p: p.suffix.lower() == ".sh" and "curl" in _safe_head(p)):
        detections.append(Detection("api", "found curl/.sh files", project))

    # rag (corpus/ + queries.*)
    corpus = project / "corpus"
    has_queries = any(p.name.lower() in ("queries.jsonl", "queries.yaml", "queries.yml") for p in files)
    if corpus.is_dir() and has_queries:
        detections.append(Detection("rag", "found corpus/ and a queries file", project))

    # evals (first CSV)
    csvs = sorted(p for p in files if p.suffix.lower() == ".csv")
    if csvs:
        detections.append(Detection("evals", f"found CSV: {csvs[0].name}", csvs[0], {"task_type": "generic"}))

    # repo (a manifest or any source file => treat as a repository)
    manifest_names = {"pyproject.toml", "package.json", "cargo.toml", "go.mod", "requirements.txt"}
    source_suffixes = {".py", ".js", ".ts", ".go", ".rs", ".java", ".rb"}
    if names & manifest_names or any_suffix(*source_suffixes):
        detections.append(Detection("repo", "found source files / a dependency manifest", project))

    # deps (a dependency manifest => audit pinning/duplicates)
    if names & manifest_names or any_named(lambda p: p.name.lower().startswith("requirements") and p.name.lower().endswith(".txt")):
        detections.append(Detection("deps", "found a dependency manifest", project))

    # config (any .env-style file present)
    if any_named(lambda p: p.name.lower() == ".env" or p.name.lower().startswith(".env.") or p.name.lower().endswith(".env")):
        detections.append(Detection("config", "found .env / .env.example files", project))

    # openapi (a yaml/json spec mentioning openapi/swagger)
    spec = next(
        (p for p in files
         if p.suffix.lower() in (".yaml", ".yml", ".json")
         and ("openapi" in _safe_head(p) or "swagger" in _safe_head(p))),
        None,
    )
    if spec is not None:
        detections.append(Detection("openapi", f"found an OpenAPI/Swagger spec: {spec.name}", spec))

    # docs (any Python source -> docstring coverage)
    if any_suffix(".py"):
        detections.append(Detection("docs", "found Python source for docstring coverage", project))

    # sql (any .sql files)
    if any_suffix(".sql"):
        detections.append(Detection("sql", "found .sql files", project))

    # todo (any common source/doc files -> marker backlog)
    if any_suffix(".py", ".js", ".ts", ".go", ".rs", ".java", ".rb", ".md", ".sql", ".sh"):
        detections.append(Detection("todo", "found source/doc files to scan for markers", project))

    # changelog (a git repo, or a commits.jsonl)
    if (project / ".git").exists():
        detections.append(Detection("changelog", "found a git repository", project))
    elif any(p.name.lower() == "commits.jsonl" for p in files):
        detections.append(Detection("changelog", "found commits.jsonl", project))

    return detections


def _safe_head(path: Path, n: int = 400) -> str:
    try:
        return path.read_text(encoding="utf-8")[:n]
    except (OSError, UnicodeDecodeError):
        return ""
