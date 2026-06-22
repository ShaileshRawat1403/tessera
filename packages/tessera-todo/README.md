# tesserakit-todo

Turn scattered code markers into a triaged backlog.

`tessera-todo` scans source files for `TODO`, `FIXME`, `HACK`, `XXX`, `BUG`, `NOTE`, `OPTIMIZE`, `REFACTOR`, and `DEPRECATED` markers, captures their owner and description, assigns a priority, and produces a prioritized, grouped backlog. No code execution.

## Scan

```bash
tessera todo scan --input . --output ./out/todo_pack
```

Artifacts written:

```text
todos.jsonl              one TodoItem per marker (marker, priority, owner, text, file:line)
index.md                 the backlog, high priority first
validation_report.md     findings (high-priority markers, ownerless TODOs)
coverage_report.md       counts by priority, marker, and file
by_owner.md              markers grouped by owner (TODO(owner): ...)
```

## Priorities

- **high**: `FIXME`, `HACK`, `XXX`, `BUG`
- **normal**: `TODO`, `REFACTOR`
- **low**: `NOTE`, `OPTIMIZE`, `DEPRECATED`

## Findings

- `high_priority_marker` — a FIXME/HACK/XXX/BUG is present
- `todo_without_owner` — a `TODO` with no `(owner)`
- `marker_without_text` — a marker with no description
- `no_markers` — nothing found

Owners are parsed from the `TODO(owner): ...` convention.
