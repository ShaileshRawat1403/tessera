from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from tessera_recipes.schema import Recipe

# Matches ${inputs.NAME} and ${steps.STEP_ID(.output|.anything)?}
_REF_RE = re.compile(r"\$\{\s*(inputs|steps)\.([a-zA-Z_][a-zA-Z0-9_-]*)(?:\.[a-zA-Z0-9_.-]+)?\s*\}")


@dataclass
class Reference:
    kind: str  # "inputs" or "steps"
    target: str


@dataclass
class GraphAnalysis:
    """Result of analyzing a recipe's step dependency graph."""

    order: list[str] = field(default_factory=list)  # topological order (empty if cyclic)
    edges: dict[str, list[str]] = field(default_factory=dict)  # step_id -> sorted dep ids
    cycle: list[str] = field(default_factory=list)  # one detected cycle, if any
    is_acyclic: bool = True


def extract_references(value: Any) -> list[Reference]:
    """Recursively find ${inputs.X} / ${steps.X} references in any input value."""
    refs: list[Reference] = []

    def walk(v: Any) -> None:
        if isinstance(v, str):
            for m in _REF_RE.finditer(v):
                refs.append(Reference(kind=m.group(1), target=m.group(2)))
        elif isinstance(v, dict):
            for item in v.values():
                walk(item)
        elif isinstance(v, (list, tuple)):
            for item in v:
                walk(item)

    walk(value)
    return refs


def referenced_step_ids(step_inputs: dict[str, Any]) -> set[str]:
    return {r.target for r in extract_references(step_inputs) if r.kind == "steps"}


def referenced_input_names(step_inputs: dict[str, Any]) -> set[str]:
    return {r.target for r in extract_references(step_inputs) if r.kind == "inputs"}


def build_edges(recipe: Recipe) -> dict[str, set[str]]:
    """Effective dependency edges = explicit needs UNION inferred from ${steps.X}."""
    edges: dict[str, set[str]] = {}
    for step in recipe.steps:
        deps = set(step.needs) | referenced_step_ids(step.inputs)
        deps.discard(step.id)  # ignore self-reference here; flagged separately
        edges[step.id] = deps
    return edges


def analyze(recipe: Recipe) -> GraphAnalysis:
    """Build edges, detect a cycle, and produce a topological order when acyclic."""
    edges = build_edges(recipe)
    known = set(edges.keys())

    # Restrict edges to known steps for ordering; unknown deps are a validation
    # concern handled elsewhere, not an ordering one.
    clean: dict[str, set[str]] = {sid: {d for d in deps if d in known} for sid, deps in edges.items()}

    order, cycle = _topo_sort(clean)
    return GraphAnalysis(
        order=order,
        edges={sid: sorted(deps) for sid, deps in edges.items()},
        cycle=cycle,
        is_acyclic=not cycle,
    )


def _topo_sort(edges: dict[str, set[str]]) -> tuple[list[str], list[str]]:
    """Kahn's algorithm. Returns (order, cycle). On a cycle, order is [] and
    cycle holds one representative cycle path."""
    # in-degree = number of deps each node still waits on
    indegree = {node: len(deps) for node, deps in edges.items()}
    # dependents map: dep -> nodes that depend on it
    dependents: dict[str, list[str]] = {node: [] for node in edges}
    for node, deps in edges.items():
        for d in deps:
            dependents.setdefault(d, []).append(node)

    ready = sorted([n for n, deg in indegree.items() if deg == 0])
    order: list[str] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for dependent in sorted(dependents.get(node, [])):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
        ready.sort()

    if len(order) == len(edges):
        return order, []

    # A cycle exists among the unresolved nodes; surface one path.
    unresolved = {n for n in edges if n not in set(order)}
    cycle = _find_one_cycle(edges, unresolved)
    return [], cycle


def _find_one_cycle(edges: dict[str, set[str]], pool: set[str]) -> list[str]:
    """DFS within ``pool`` to return one cycle as an ordered list of node ids."""
    color: dict[str, int] = {}  # 0=unvisited,1=in-stack,2=done
    stack: list[str] = []

    def dfs(node: str) -> list[str] | None:
        color[node] = 1
        stack.append(node)
        for dep in sorted(edges.get(node, set())):
            if dep not in pool:
                continue
            if color.get(dep, 0) == 1:
                idx = stack.index(dep)
                return stack[idx:] + [dep]
            if color.get(dep, 0) == 0:
                found = dfs(dep)
                if found:
                    return found
        stack.pop()
        color[node] = 2
        return None

    for n in sorted(pool):
        if color.get(n, 0) == 0:
            found = dfs(n)
            if found:
                return found
    return sorted(pool)  # fallback: report the whole tangle
