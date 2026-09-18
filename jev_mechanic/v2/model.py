"""Load and validate the version 2 fault model: the flowchart plus symptoms and cause links."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .. import flowchart as fc

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "v2" / "flowchart.json"

MAX_FAULTS = 3


@dataclass(frozen=True)
class Symptom:
    id: str
    label: str
    description: str


@dataclass(frozen=True)
class FaultModel:
    """The version 1 flowchart, where each system is a component, plus symptoms and cause links."""

    chart: fc.Flowchart
    symptoms: dict[str, Symptom]
    explains: dict[str, tuple[str, ...]]  # diagnosis id -> symptom ids that it explains
    causes: dict[str, tuple[str, ...]]  # diagnosis id -> diagnosis ids that it can cause

    @property
    def components(self) -> dict[str, fc.System]:
        return self.chart.systems

    @property
    def diagnoses(self) -> dict[str, fc.Diagnosis]:
        return self.chart.diagnoses

    def diagnoses_of(self, component_id: str) -> list[str]:
        return [d.id for d in self.diagnoses.values() if component_id in d.systems]

    def explained_by(self, symptom_id: str) -> list[str]:
        return [d for d, symptoms in self.explains.items() if symptom_id in symptoms]

    def caused_by(self, diagnosis_id: str) -> list[str]:
        return [d for d, effects in self.causes.items() if diagnosis_id in effects]

    def ancestors(self, diagnosis_id: str) -> set[str]:
        """Return every diagnosis that can cause `diagnosis_id`, directly or through a chain."""
        found: set[str] = set()
        stack = [diagnosis_id]
        while stack:
            for cause in self.caused_by(stack.pop()):
                if cause not in found:
                    found.add(cause)
                    stack.append(cause)
        return found

    def root_first(self, diagnosis_ids: list[str]) -> list[str]:
        """Return the diagnoses in an order where each cause comes before its effects.

        A chain counts too: when A causes B and B causes C, A comes before C even when B is
        not in the list.
        """
        chosen = set(diagnosis_ids)
        ordered: list[str] = []

        def visit(d: str) -> None:
            if d in ordered:
                return
            for cause in sorted(self.ancestors(d) & chosen):
                visit(cause)
            ordered.append(d)

        for d in diagnosis_ids:
            visit(d)
        return ordered


def validate(raw: dict) -> list[str]:
    """Return a list of schema errors for version 2 data. An empty list means valid data."""
    errors = fc.validate(raw)
    symptoms = raw.get("symptoms") or {}
    diagnoses = raw.get("diagnoses") or {}
    if not symptoms:
        errors.append("no symptoms")
    for sid, symptom in symptoms.items():
        for key in ("label", "description"):
            if not symptom.get(key):
                errors.append(f"symptom {sid}: no {key}")
    explained: set[str] = set()
    for did, diagnosis in diagnoses.items():
        explains = diagnosis.get("explains") or []
        if not explains:
            errors.append(f"diagnosis {did}: explains no symptom")
        for sid in explains:
            if sid not in symptoms:
                errors.append(f"diagnosis {did}: explains unknown symptom {sid!r}")
            explained.add(sid)
        for effect in diagnosis.get("causes") or []:
            if effect not in diagnoses:
                errors.append(f"diagnosis {did}: causes unknown diagnosis {effect!r}")
            if effect == did:
                errors.append(f"diagnosis {did}: causes itself")
    for sid in sorted(set(symptoms) - explained):
        errors.append(f"symptom {sid}: no diagnosis explains it")
    errors.extend(_cause_cycles(diagnoses))
    return errors


def _cause_cycles(diagnoses: dict) -> list[str]:
    state: dict[str, int] = {}
    errors: list[str] = []

    def visit(d: str) -> None:
        state[d] = 1
        for effect in diagnoses[d].get("causes") or []:
            if effect not in diagnoses:
                continue
            if state.get(effect) == 1:
                errors.append(f"diagnosis {d}: cause link to {effect} closes a cycle")
            elif effect not in state:
                visit(effect)
        state[d] = 2

    for d in diagnoses:
        if d not in state:
            visit(d)
    return errors


def parse(raw: dict) -> FaultModel:
    """Validate raw version 2 data and return the fault model."""
    errors = validate(raw)
    if errors:
        raise fc.FlowchartError(errors)
    chart = fc.parse(raw)
    symptoms = {
        sid: Symptom(sid, s["label"], s["description"]) for sid, s in raw["symptoms"].items()
    }
    explains = {did: tuple(d["explains"]) for did, d in raw["diagnoses"].items()}
    causes = {did: tuple(d.get("causes") or ()) for did, d in raw["diagnoses"].items()}
    return FaultModel(chart, symptoms, explains, causes)


def load(path: str | Path = DEFAULT_PATH) -> FaultModel:
    """Read, validate and return the version 2 fault model at `path`."""
    return parse(json.loads(Path(path).read_text()))


def _longest_path(chart: fc.Flowchart, node_id: str) -> int:
    node = chart.nodes[node_id]
    return 1 + max((_longest_path(chart, o.next) for o in node.options.values() if o.next in chart.nodes), default=0)


def main() -> None:
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    model = load(path)
    depth = max(_longest_path(model.chart, c.entry) for c in model.components.values())
    links = sum(len(v) for v in model.causes.values())
    print(
        f"{path}: valid, {len(model.components)} components, {len(model.diagnoses)} diagnoses, "
        f"{len(model.symptoms)} symptoms, {len(model.chart.nodes)} nodes, {links} cause links, "
        f"longest branch {depth} questions"
    )


if __name__ == "__main__":
    main()
