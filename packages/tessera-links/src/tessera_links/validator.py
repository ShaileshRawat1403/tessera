from __future__ import annotations

from typing import Any

from tessera_core.models import ValidationFinding

from tessera_links.schema import Link


def validate_link_records(links: list[Link], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    for link in links:
        if not link.broken:
            continue
        loc = f"{link.source_file}:{link.lineno}"
        code = "broken_anchor" if "anchor" in link.reason else "broken_link"
        findings.append(
            ValidationFinding(
                severity="warning", code=code,
                message=f"{loc}: [{link.text}]({link.href}) — {link.reason}",
                field="links", metadata={"source_file": link.source_file, "lineno": link.lineno, "href": link.href},
            )
        )

    # Only report orphans when the project actually cross-links docs with inline
    # markdown links. Sphinx/mkdocs projects navigate via toctree/nav, so every
    # page would look orphaned — that is noise, not signal.
    MIN_MD_LINK_GRAPH = 3
    if options.get("_referenced_md_count", 0) >= MIN_MD_LINK_GRAPH:
        for orphan in options.get("_orphans", []):
            findings.append(
                ValidationFinding(
                    severity="info", code="orphan_doc",
                    message=f"{orphan} is not linked from any other doc",
                    field="links", metadata={"file": orphan},
                )
            )

    if not links and not options.get("_orphans"):
        findings.append(ValidationFinding(severity="info", code="no_links",
                                          message="no markdown links found", field=None))

    return findings
