# Contracts for version 2

This file fixes the interfaces that the version 2 lanes share. `CONTRACTS.md` stays valid for version 1, and version 1 must keep its
behavior. When a lane must change an interface, it records the change here.

## Environment

As in `CONTRACTS.md`. The version 2 code is in `jev_mechanic/v2/`, the data is in
`data/v2/`, and the tests are in `tests/v2/`.

## Fault model (`jev_mechanic/v2/model.py`, finished)

The version 2 data file uses the version 1 schema, with three additions. The
`systems` of version 1 are the components of version 2.

```json
{
  "systems":   {"<component id>": {"label", "description", "entry"}},
  "symptoms":  {"<symptom id>": {"label", "description"}},
  "diagnoses": {"<diagnosis id>": {"label", "description", "systems", "prior", "fix",
                                   "explains": ["<symptom id>"], "causes": ["<diagnosis id>"]}},
  "nodes":     {"<node id>": "as version 1"}
}
```

- `explains` lists the symptoms that the fault produces. Each symptom needs at least
  one diagnosis that explains it.
- `causes` lists the faults that this fault can cause, for example
  `alternator_failure` causes `flat_battery`. The links must not form a cycle.
- `tests/v2/fixtures/mini_v2.json` is a small valid example.

```python
load(path) -> FaultModel
FaultModel.chart          # the version 1 Flowchart
FaultModel.components     # dict[str, System]
FaultModel.diagnoses      # dict[str, Diagnosis]
FaultModel.symptoms       # dict[str, Symptom(id, label, description)]
FaultModel.explains       # dict[diagnosis id, tuple[symptom id]]
FaultModel.causes         # dict[diagnosis id, tuple[diagnosis id]]
FaultModel.diagnoses_of(component_id) -> list[str]
FaultModel.explained_by(symptom_id) -> list[str]
FaultModel.caused_by(diagnosis_id) -> list[str]
FaultModel.root_first(diagnosis_ids) -> list[str]
MAX_FAULTS = 3
```

## Cases (`data/v2/cases.json`)

```json
[
  {
    "id": "golf_alternator_battery",
    "title": "Slow start and a battery light",
    "date": "2026-09-01",
    "faults": ["alternator_failure", "flat_battery"],
    "tags": ["cascade"],
    "report": "Customer text, 2 to 6 sentences.",
    "case_file": {
      "vehicle": {"make": "VW", "model": "Golf", "year": 2014, "mileage_km": 128400},
      "obd_codes": [{"code": "P0562", "description": "System voltage low", "status": "active", "mileage_km": 128350}],
      "freeze_frame": {"battery_voltage_v": 11.6, "coolant_temp_c": 88},
      "service_history": [{"date": "2025-11-02", "mileage_km": 119800, "work": "Oil and filter change"}],
      "technician_notes": ["Battery light flickered on the road test."]
    },
    "answers": {"<node id>": "free-text answer of the mechanic"}
  }
]
```

- `faults` is the true set, 1 to 3 diagnoses.
- `tags` uses these values: `cascade`, `look_alike`, `vague_report`, `unclear_answer`,
  `independent_faults`, `no_fix`.
- `obd_codes.status` is `active`, `pending`, `history` or `cleared`.
- Each source has some irrelevant entries, such as an old cleared code or a routine
  service line.
- `answers` has an answer for each node that the case can reach, in each branch that
  the app can visit.

## Evidence (`jev_mechanic/v2/casefile.py`)

```python
filter_case_file(case_file: dict, date: str) -> tuple[dict, list[dict]]
    # returns (kept case file, removed entries)
    # remove a cleared code more than 5,000 km before vehicle.mileage_km
    # remove a service entry more than 24 months before `date`, but keep the last 3 entries
    # each removed entry: {"source": "obd_codes", "entry": {...}, "reason": "cleared 12,000 km ago"}
evidence_state(mode: str, report: str, case_file: dict | None) -> dict
    # mode "report":    {"customer_report": report}
    # mode "case_file": {"customer_report": report, "obd_codes": [...], "freeze_frame": {...},
    #                    "service_history": [...], "technician_notes": [...], "vehicle": {...}}
```

## Jev requests (`jev_mechanic/v2/questions.py`)

| Request | When | State | Questions |
| --- | --- | --- | --- |
| E, evidence | once, at start | the evidence state | `sym_<id>`: one Noul for each symptom. `comp_<id>`: one Noul for each component. |
| A, branch | once for each loop | the evidence state | `pre_<node>`: one Choice for each node of the selected component, plus `not_stated` |
| B, answer | once for each answer | as version 1 | as version 1, with `extra_` inside the component |
| C, independent | at start and after each answer | the evidence state plus `questions_and_answers` | `diag_<id>`: one Noul for each diagnosis |

Send C at the same time as E, and at the same time as B.

## Session (`jev_mechanic/v2/session.py`)

```python
class Session:
    def __init__(self, model, jev, mode, report, case_file=None, date=None,
                 extra_questions=True, independent_lane=True): ...
    def start(self) -> None
    def answer(self, text: str) -> None
    def choose(self, option_id: str) -> None
    def accept(self) -> None
    def keep_going(self) -> None
    def view(self) -> dict
```

The session reuses `SessionError` from `jev_mechanic.session`.

### The loop

1. Request E. A symptom with a Noul of more than 0.5 is present.
2. Select the next component. Use only an open component that has a
   diagnosis that explains an unexplained present symptom. Score each such component:
   `comp_noul × (number of unexplained present symptoms that it can explain)`. Add 1
   when a found fault has a cause in that component. Take the highest score.
3. If no open component remains, or the session found `MAX_FAULTS` faults, complete the case.
4. Request A for the selected component, and apply the known answers as in version 1.
5. Walk the branch as in version 1. The branch scores cover the diagnoses of the
   component only. Start them from the priors, times the symptom evidence: multiply by
   0.8 for each present symptom that the diagnosis explains, then normalize.
6. At a diagnosis leaf, or after `accept`, record the fault. Mark its symptoms as
   explained. Mark the component as done. Go to step 2.
7. At the `specialist` leaf, mark the component as done with no fault. Go to step 2.

### Status values

`asking`, `confirm`, `reask` and `flagged` have the version 1 meaning. `complete`
means that the loop ended with at least one fault. `specialist` means that it ended
with no fault.

### The view

```json
{
  "id": "s_1a2b", "version": 2, "mode": "case_file", "status": "asking",
  "evidence": {"report": "...", "case_file": {}, "removed": [{"source": "...", "entry": {}, "reason": "..."}]},
  "symptoms": [{"id": "slow_crank", "label": "Slow crank", "probability": 0.93, "present": true,
                "explained_by": "flat_battery"}],
  "components": [{"id": "charge", "label": "Charge system", "probability": 0.8,
                  "state": "active", "score": 2.4}],
  "loop": {"index": 2, "component": "charge"},
  "current": "as version 1",
  "confirm_options": [],
  "steps": [{"...": "as version 1", "loop": 2, "component": "charge"}],
  "branch_scores": [{"id": "alternator_failure", "label": "...", "score": 0.7}],
  "flag": null,
  "faults": [{"id": "flat_battery", "label": "...", "score": 0.93, "component": "battery",
              "loop": 1, "explains": ["slow_crank"], "caused_by_found": ["alternator_failure"]}],
  "fix": [{"diagnosis": "alternator_failure", "label": "...", "steps": ["..."]}],
  "unexplained": [{"id": "coolant_smell", "label": "..."}],
  "independent": {"enabled": true, "faults": [{"id": "...", "label": "...", "score": 0.8}],
                  "top": [{"id": "...", "label": "...", "score": 0.8}]},
  "path": ["q_chg_running_voltage"],
  "mermaid": "the active component branch only",
  "ledger": "as version 1, with the kinds E, A, B and C"
}
```

- `fix` lists the found faults root first, with `FaultModel.root_first`. It removes a
  step that an earlier fault in the list already has.
- `independent.faults` holds each diagnosis with a Noul of more than 0.5. `top` holds
  the top eight.
- `mermaid` draws the branch of the active component only. A drawing of 150 nodes is
  not readable.

## HTTP API additions (`jev_mechanic/server.py`)

| Method and path | Body | Action |
| --- | --- | --- |
| `GET /api/v2/cases` | none | `[{"id", "title", "report", "case_file", "faults", "tags", "date"}]` |
| `POST /api/sessions` | `{"version": 2, "mode": "report" or "case_file", "report"?, "case_id"?, "extra_questions"?, "independent_lane"?}` | a version 2 session |

A version 2 body with `case_id` takes the report, the case file and the date from that
case. A body with `mode: "report"` and no `case_id` takes the typed `report`. A body
with no `version` makes a version 1 session. The other routes work for both versions.

The server takes `--flowchart-v2`, and it loads `data/v2/flowchart.json` by default.

## Changes from the engine lane (2026-09-18)

These items change the contract above, or add a detail that it does not give.

- Loop step 5: the start of the branch scores multiplies by 0.8 for each present
  symptom that the diagnosis explains. It multiplies by 0.2 for each present symptom
  that the diagnosis does not explain. With 0.8 only, a diagnosis that explains more symptoms gets a lower
  score. The present symptoms include the symptoms that a found fault explains.
- Ledger steps: request E and its request C have the step 0. Each request A and each
  request B gets the next step number, and a request C has the step of its request B.
  Thus `wait_seconds` adds the A time to the E time.
- `components[].state` is `open`, `active`, `fault` or `no_fault`.
  `components[].score` is null when the loop cannot select the component.
- `branch_scores` is empty when no component is active.
- `mermaid` draws the branch of the last component when no component is active, and it
  is an empty string before the first loop.
- `faults[].explains` lists the present symptoms that the fault explained first. A
  symptom that an earlier fault explains stays with that earlier fault.
- A diagnosis leaf that the session found before does not make a second fault. The
  component still becomes `fault`.
- `fix` keeps an entry for each fault, also when the entry has no steps left.
- `Session(date=None)` uses the date of today for the filter. `Session` raises
  `ValueError` for the mode `case_file` with no case file.
- Request A: the `pre_` questions name each field of the evidence state, and give a
  short note on each source in `instructions.sources`.
- `jev_mechanic.v2.session` exports `COMPLETE = "complete"` and the version 1 status
  names.
- CLI: `python -m jev_mechanic.cli --v2 [--mode report|case_file] [--case <id>]
  [--cases <file>] [--chart <file>]`. `--case` takes the report, the case file and the
  date from `data/v2/cases.json`. `--mode case_file` needs `--case`.
