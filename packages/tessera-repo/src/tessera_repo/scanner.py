from __future__ import annotations

from collections import Counter
from pathlib import Path

from tessera_repo.languages import IGNORE_DIRS, kind_for, language_for
from tessera_repo.manifests import detect_and_parse
from tessera_repo.schema import RepoFile, RepoManifest, RepoMap

_TEXT_LANGS_SKIP_LOC = {"unknown"}


def _count_loc(path: Path, language: str) -> int:
    if language in _TEXT_LANGS_SKIP_LOC:
        return 0
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return 0
    return sum(1 for line in text.splitlines() if line.strip())


def scan_repo(root: Path) -> tuple[list[RepoFile], list[RepoManifest], dict]:
    """Walk the repo, returning files, parsed manifests, and hygiene signals."""
    files: list[RepoFile] = []
    manifests: list[RepoManifest] = []

    for path in sorted(root.rglob("*")):
        if any(part in IGNORE_DIRS for part in path.relative_to(root).parts):
            continue
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        language = language_for(rel)
        kind = kind_for(rel)
        loc = _count_loc(path, language) if kind in ("source", "test") else 0
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        files.append(RepoFile(path=rel.as_posix(), language=language, kind=kind, loc=loc, bytes=size))

        manifest = detect_and_parse(root, rel)
        if manifest is not None:
            manifests.append(manifest)

    signals = _signals(files)
    return files, manifests, signals


def _signals(files: list[RepoFile]) -> dict:
    names = {Path(f.path).name.lower() for f in files}
    top_level = {f.path.lower() for f in files if "/" not in f.path}
    has_readme = any(n.startswith("readme") for n in names)
    has_license = any(n.startswith("license") or n.startswith("licence") or n == "copying" for n in names)
    has_tests = any(f.kind == "test" for f in files)
    has_ci = any(
        f.path.startswith(".github/workflows/") or Path(f.path).name.lower() in (".gitlab-ci.yml", ".travis.yml")
        for f in files
    )
    has_gitignore = ".gitignore" in top_level
    return {
        "has_readme": has_readme,
        "has_license": has_license,
        "has_tests": has_tests,
        "has_ci": has_ci,
        "has_gitignore": has_gitignore,
    }


def build_map(root: Path, files: list[RepoFile], manifests: list[RepoManifest], signals: dict) -> RepoMap:
    languages = Counter(f.language for f in files if f.language != "unknown")
    by_kind = Counter(f.kind for f in files)
    top_dirs: Counter[str] = Counter()
    for f in files:
        head = f.path.split("/", 1)[0] if "/" in f.path else "(root)"
        top_dirs[head] += 1
    return RepoMap(
        root=str(root),
        file_count=len(files),
        total_loc=sum(f.loc for f in files),
        total_bytes=sum(f.bytes for f in files),
        languages=dict(languages.most_common()),
        by_kind=dict(by_kind.most_common()),
        top_dirs=dict(top_dirs.most_common()),
        manifests=manifests,
        signals=signals,
    )
