"""Load, validate and draw the diagnostic flowchart."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "flowchart.json"

# The leaf for a case that no diagnosis in the flowchart explains.
SPECIALIST = "specialist"

# Answer options that carry no evidence about any diagnosis.
NEUTRAL_OPTIONS = frozenset({"not_sure", "unclear", "not_stated"})

YES_NO_OPTIONS = frozenset({"yes", "no", "not_sure"})

DEFAULT_LIKELIHOOD = 0.1


class FlowchartError(ValueError):
    """The flowchart data breaks one or more rules of the schema."""

    def __init__(self, errors: list[str]):
        super().__init__("flowchart is not valid:\n  " + "\n  ".join(errors))
        self.errors = errors


@dataclass(frozen=True)
class System:
    id: str
    label: str
    description: str
    entry: str


@dataclass(frozen=True)
class Diagnosis:
    id: str
    label: str
    description: str
    systems: tuple[str, ...]
    prior: float
    fix: tuple[str, ...]


@dataclass(frozen=True)
class Option:
    id: str
    text: str
    next: str


@dataclass(frozen=True)
class Node:
    id: str
    question: str
    options: dict[str, Option]
    evidence: dict[str, dict[str, float]]
    default_likelihood: float = DEFAULT_LIKELIHOOD

    @property
    def is_yes_no(self) -> bool:
        return set(self.options) <= YES_NO_OPTIONS and {"yes", "no"} <= set(self.options)

    def likelihood(self, option_id: str, diagnosis_id: str) -> float:
        """Return P(option | diagnosis) for one answer option of this node."""
        if option_id in NEUTRAL_OPTIONS or option_id not in self.evidence:
            return 1.0
        return self.evidence[option_id].get(diagnosis_id, self.default_likelihood)


@dataclass(frozen=True)
class Flowchart:
    systems: dict[str, System]
    diagnoses: dict[str, Diagnosis]
    nodes: dict[str, Node]
    raw: dict = field(repr=False, compare=False)

    def is_leaf(self, target: str) -> bool:
        return target == SPECIALIST or target in self.diagnoses

    def reachable_nodes(self, start: str) -> list[str]:
        """Return the node ids reachable from `start`, in breadth-first order, `start` first."""
        if start not in self.nodes:
            return []
        seen = [start]
        queue = deque([start])
        while queue:
            for option in self.nodes[queue.popleft()].options.values():
                if option.next in self.nodes and option.next not in seen:
                    seen.append(option.next)
                    queue.append(option.next)
        return seen

    def system_of_node(self, node_id: str) -> str | None:
        for system in self.systems.values():
            if node_id in self.reachable_nodes(system.entry):
                return system.id
        return None

    def to_mermaid(self, path: list[str] | None = None, current: str | None = None) -> str:
        """Return Mermaid flowchart text. Nodes in `path` and the `current` node get a class."""
        path_set = set(path or [])
        lines = ["flowchart TD"]
        for system in self.systems.values():
            lines.append(f'  sys_{system.id}(["{_label(system.label)}"]) --> {system.entry}')
        for node in self.nodes.values():
            lines.append(f'  {node.id}{{"{_label(node.question)}"}}')
            for option in node.options.values():
                target = option.next
                lines.append(f'  {node.id} -->|"{_label(option.id.replace("_", " "))}"| {target}')
        for diagnosis in self.diagnoses.values():
            lines.append(f'  {diagnosis.id}["{_label(diagnosis.label)}"]')
        lines.append(f'  {SPECIALIST}["Refer to a specialist"]')
        lines.append("  classDef leaf fill:#eef6ee,stroke:#5a8f5a")
        lines.append("  classDef onpath fill:#fff3c4,stroke:#b58900,stroke-width:2px")
        lines.append("  classDef current fill:#ffd166,stroke:#9c6500,stroke-width:3px")
        leaves = [*self.diagnoses, SPECIALIST]
        lines.append(f"  class {','.join(leaves)} leaf")
        on_path = [n for n in path_set if n != current]
        if on_path:
            lines.append(f"  class {','.join(sorted(on_path))} onpath")
        if current:
            lines.append(f"  class {current} current")
        return "\n".join(lines)


def _label(text: str) -> str:
    return text.replace('"', "'")


def validate(raw: dict) -> list[str]:
    """Return a list of schema errors. An empty list means that the data is valid."""
    errors: list[str] = []
    systems = raw.get("systems") or {}
    diagnoses = raw.get("diagnoses") or {}
    nodes = raw.get("nodes") or {}
    if not systems:
        errors.append("no systems")
    if not diagnoses:
        errors.append("no diagnoses")
    if not nodes:
        errors.append("no nodes")

    ids = [*systems, *diagnoses, *nodes]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        errors.append(f"ids used twice across systems, diagnoses and nodes: {sorted(duplicates)}")
    if SPECIALIST in ids:
        errors.append(f"'{SPECIALIST}' is reserved")

    for sid, system in systems.items():
        if system.get("entry") not in nodes:
            errors.append(f"system {sid}: entry {system.get('entry')!r} is not a node")
        for key in ("label", "description"):
            if not system.get(key):
                errors.append(f"system {sid}: no {key}")

    for did, diagnosis in diagnoses.items():
        for key in ("label", "description"):
            if not diagnosis.get(key):
                errors.append(f"diagnosis {did}: no {key}")
        if not diagnosis.get("systems"):
            errors.append(f"diagnosis {did}: no systems")
        for sid in diagnosis.get("systems", []):
            if sid not in systems:
                errors.append(f"diagnosis {did}: unknown system {sid!r}")
        prior = diagnosis.get("prior")
        if not isinstance(prior, (int, float)) or not 0 < prior <= 1:
            errors.append(f"diagnosis {did}: prior {prior!r} is not in (0, 1]")
        fix = diagnosis.get("fix") or []
        if not 3 <= len(fix) <= 8:
            errors.append(f"diagnosis {did}: {len(fix)} fix steps, expected 3 to 8")

    for nid, node in nodes.items():
        if not node.get("question"):
            errors.append(f"node {nid}: no question")
        options = node.get("options") or {}
        if len(options) < 2:
            errors.append(f"node {nid}: fewer than 2 options")
        for oid, option in options.items():
            if oid in {"unclear", "not_stated"}:
                errors.append(f"node {nid}: option id {oid!r} is reserved")
            if not option.get("text"):
                errors.append(f"node {nid}.{oid}: no text")
            target = option.get("next")
            if target not in nodes and target not in diagnoses and target != SPECIALIST:
                errors.append(f"node {nid}.{oid}: next {target!r} is not a node or a leaf")
        for oid, table in (node.get("evidence") or {}).items():
            if oid not in options:
                errors.append(f"node {nid}: evidence for unknown option {oid!r}")
            for did, value in table.items():
                if did not in diagnoses:
                    errors.append(f"node {nid}.{oid}: evidence for unknown diagnosis {did!r}")
                if not isinstance(value, (int, float)) or not 0 < value <= 1:
                    errors.append(f"node {nid}.{oid}.{did}: likelihood {value!r} is not in (0, 1]")
        default = node.get("default_likelihood", DEFAULT_LIKELIHOOD)
        if not isinstance(default, (int, float)) or not 0 < default <= 1:
            errors.append(f"node {nid}: default_likelihood {default!r} is not in (0, 1]")

    if errors:
        return errors

    chart = _build(raw)
    reachable: set[str] = set()
    for system in chart.systems.values():
        reachable.update(chart.reachable_nodes(system.entry))
    for nid in sorted(set(nodes) - reachable):
        errors.append(f"node {nid}: not reachable from a system entry")
    for nid in _cycle_nodes(chart):
        errors.append(f"node {nid}: part of a cycle, so a path from it can never end at a leaf")
    leaves = {o.next for n in chart.nodes.values() for o in n.options.values() if chart.is_leaf(o.next)}
    for did in sorted(set(diagnoses) - leaves):
        errors.append(f"diagnosis {did}: no option leads to it")
    return errors


def _cycle_nodes(chart: Flowchart) -> list[str]:
    """Return the nodes that are on a cycle of the flowchart graph."""
    on_cycle: set[str] = set()
    state: dict[str, int] = {}  # 1 = on the stack, 2 = finished

    def visit(nid: str, stack: list[str]) -> None:
        state[nid] = 1
        stack.append(nid)
        for option in chart.nodes[nid].options.values():
            target = option.next
            if target not in chart.nodes:
                continue
            if state.get(target) == 1:
                on_cycle.update(stack[stack.index(target):])
            elif target not in state:
                visit(target, stack)
        stack.pop()
        state[nid] = 2

    for nid in chart.nodes:
        if nid not in state:
            visit(nid, [])
    return sorted(on_cycle)


def _build(raw: dict) -> Flowchart:
    systems = {
        sid: System(sid, s["label"], s["description"], s["entry"]) for sid, s in raw["systems"].items()
    }
    diagnoses = {
        did: Diagnosis(
            did, d["label"], d["description"], tuple(d["systems"]), float(d["prior"]), tuple(d["fix"])
        )
        for did, d in raw["diagnoses"].items()
    }
    nodes = {
        nid: Node(
            nid,
            n["question"],
            {oid: Option(oid, o["text"], o["next"]) for oid, o in n["options"].items()},
            {oid: dict(table) for oid, table in (n.get("evidence") or {}).items()},
            float(n.get("default_likelihood", DEFAULT_LIKELIHOOD)),
        )
        for nid, n in raw["nodes"].items()
    }
    return Flowchart(systems, diagnoses, nodes, raw)


def parse(raw: dict) -> Flowchart:
    """Validate raw flowchart data and return the typed flowchart."""
    errors = validate(raw)
    if errors:
        raise FlowchartError(errors)
    return _build(raw)


def load(path: str | Path = DEFAULT_PATH) -> Flowchart:
    """Read, validate and return the flowchart at `path`."""
    return parse(json.loads(Path(path).read_text()))


def main() -> None:
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    chart = load(path)
    print(
        f"{path}: valid, {len(chart.systems)} systems, {len(chart.diagnoses)} diagnoses, "
        f"{len(chart.nodes)} nodes"
    )


if __name__ == "__main__":
    main()
