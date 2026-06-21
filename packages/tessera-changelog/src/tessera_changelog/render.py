from __future__ import annotations

from collections import defaultdict

from tessera_changelog.schema import Commit

# Display order and headings for the changelog sections.
_SECTIONS = [
    ("feat", "Features"),
    ("fix", "Fixes"),
    ("perf", "Performance"),
    ("refactor", "Refactors"),
    ("docs", "Documentation"),
    ("test", "Tests"),
    ("build", "Build"),
    ("ci", "CI"),
    ("chore", "Chores"),
    ("style", "Style"),
    ("revert", "Reverts"),
    ("other", "Other"),
]


def _line(c: Commit) -> str:
    desc = c.metadata.get("description") or c.subject
    scope = f"**{c.scope}:** " if c.scope else ""
    pr = f" (#{c.pr_number})" if c.pr_number else ""
    sha = f" `{c.short_hash}`" if c.short_hash else ""
    return f"- {scope}{desc}{pr}{sha}"


def render_changelog(commits: list[Commit], title: str = "Changelog") -> str:
    grouped: dict[str, list[Commit]] = defaultdict(list)
    for c in commits:
        grouped[c.type].append(c)

    lines = [f"# {title}", ""]

    breaking = [c for c in commits if c.breaking]
    if breaking:
        lines.append("## Breaking Changes")
        lines.append("")
        for c in breaking:
            lines.append(_line(c))
        lines.append("")

    for key, heading in _SECTIONS:
        items = grouped.get(key, [])
        if not items:
            continue
        lines.append(f"## {heading}")
        lines.append("")
        for c in items:
            lines.append(_line(c))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_release_notes(commits: list[Commit]) -> str:
    feats = [c for c in commits if c.type == "feat"]
    fixes = [c for c in commits if c.type == "fix"]
    breaking = [c for c in commits if c.breaking]

    lines = ["# Release Notes", ""]
    lines.append(f"This release includes {len(commits)} commits: "
                 f"{len(feats)} features, {len(fixes)} fixes"
                 + (f", {len(breaking)} breaking changes" if breaking else "") + ".")
    lines.append("")

    if breaking:
        lines.append("## Heads up: breaking changes")
        lines.append("")
        for c in breaking:
            lines.append(_line(c))
        lines.append("")

    if feats:
        lines.append("## Highlights")
        lines.append("")
        for c in feats[:10]:
            lines.append(_line(c))
        if len(feats) > 10:
            lines.append(f"- ... and {len(feats) - 10} more features")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
