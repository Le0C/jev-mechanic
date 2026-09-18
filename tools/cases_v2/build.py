"""Build data/v2/cases.json from the case sources and the answer banks."""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

from banks import HEALTHY  # noqa: E402
from cases_src import CASES  # noqa: E402

from jev_mechanic.v2 import model as fm  # noqa: E402

model = fm.load()


def selectable(faults):
    symptoms = {s for f in faults for s in model.explains[f]}
    return [c for c in model.components if any(set(model.explains[d]) & symptoms for d in model.diagnoses_of(c))]


out = []
for c in CASES:
    comps = selectable(c["faults"])
    extra = set(c["answers"]) - set(comps)
    assert not extra, (c["id"], extra)
    answers = {}
    for comp in comps:
        nodes = model.chart.reachable_nodes(model.components[comp].entry)
        bank = dict(HEALTHY[comp])
        bank.update(c["answers"].get(comp, {}))
        assert set(bank) == set(nodes), (c["id"], comp, set(bank) ^ set(nodes))
        for nid in nodes:
            answers[nid] = bank[nid]
    out.append({
        "id": c["id"],
        "title": c["title"],
        "date": c["date"],
        "faults": c["faults"],
        "tags": c["tags"],
        "report": c["report"],
        "case_file": {
            "vehicle": c["vehicle"],
            "obd_codes": c["obd"],
            "freeze_frame": c["freeze"],
            "service_history": c["service"],
            "technician_notes": c["notes"],
        },
        "answers": answers,
    })
    print(f"{c['id']:28} {len(c['faults'])} {','.join(c['tags']):40} comps={','.join(comps)} answers={len(answers)}")

(ROOT / "data" / "v2" / "cases.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print(len(out), "cases written")
