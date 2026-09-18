# Contracts between the modules

This file fixes the interfaces that the build lanes share.
When a lane must change an interface, it records the change here and says so in its
report.

## Environment

- Run Python from `.venv/bin/python` (Python 3.11). `uv sync` creates it.
- The TypeSafe key is in `TYPESAFE_API_KEY`. The SDK reads it.
- Run the tests with `.venv/bin/python -m pytest -q`.
- The tests never call the live API. Only the harness and the CLI call it.

## Flowchart data (`jev_mechanic/flowchart.py`, finished)

`load(path)` returns a `Flowchart`, and `parse(raw)` does the same for a dict. Both
raise `FlowchartError` with a list of errors. The schema is in
`tests/fixtures/mini_flowchart.json`, a small valid example.

```python
Flowchart.systems:   dict[str, System]     # System(id, label, description, entry)
Flowchart.diagnoses: dict[str, Diagnosis]  # Diagnosis(id, label, description, systems, prior, fix)
Flowchart.nodes:     dict[str, Node]       # Node(id, question, options, evidence, default_likelihood)
Node.options:        dict[str, Option]     # Option(id, text, next); next = node id | diagnosis id | "specialist"
Node.is_yes_no                             # options are yes, no and (optional) not_sure
Node.likelihood(option_id, diagnosis_id)   # P(option | diagnosis); 1.0 for a neutral option
Flowchart.is_leaf(target)
Flowchart.reachable_nodes(start) -> list[str]
Flowchart.system_of_node(node_id) -> str | None
Flowchart.to_mermaid(path=None, current=None) -> str
SPECIALIST = "specialist"
NEUTRAL_OPTIONS = {"not_sure", "unclear", "not_stated"}
```

Evidence rules:

- An option with no `evidence` entry is neutral. It gives the likelihood 1.0 to each
  diagnosis.
- In an option with an entry, a diagnosis that the entry does not name gets
  `default_likelihood` (0.1 when the node does not set it).
- The Jev questions use the option ids `unclear` and `not_stated`. A node cannot use
  them.

## Jev client (`jev_mechanic/jev.py`)

```python
@dataclass
class JevResult:
    answers: dict[str, dict]   # the HTTP API answer shape, for example
                               # {"type": "choice", "choice": "x", "probabilities": {...}, "confidence": 0.9}
                               # {"type": "noul", "noul": 0.8}
    input_tokens: int
    output_tokens: int
    model: str                 # the versioned model id of the response
    seconds: float             # wall time of the call, time.perf_counter()
    request_id: str | None

class JevClient(Protocol):
    def ask(self, state: dict | str, questions: dict[str, dict]) -> JevResult: ...

class LiveJev:                 # typesafe_sdk.TypeSafeClient, model "jev-latest"
class FakeJev:                 # for tests: returns scripted answers, counts calls
    def __init__(self, script: dict[str, dict] | None = None, seed: int | None = None): ...
```

`FakeJev` looks up each question id in `script` and returns that answer. A question id
that `script` does not have gets a random distribution over its options, from `seed`.
`FakeJev()` with no script is the `--fake` mode of the server. It reports token counts
from the length of the request JSON, and a time of 0.05 s.

Additions from the engine lane (2026-09-18):

- `FakeJev(script, seed, delay=0.0)`. With `delay` more than 0, each call sleeps for
  `delay` and reports the measured time.
- A `script` value can be an answer dict, a list of answer dicts (one for each call),
  or a function of `(state, question)`. A `script` key can be a shell pattern, such as
  `pre_*`. `make_choice(probabilities, confidence=None)` makes an answer dict.
- `FakeJev.calls` keeps each `(state, questions)` pair, and `FakeJev.call_count` gives
  the number of calls.

Questions use the HTTP API shape, a plain dict. The SDK accepts that shape:
`{"type": "choice", "instructions": "...", "criteria": {"option": "description"}}`.

## Requests (`jev_mechanic/questions.py`)

Each function returns `(state, questions)`.

```python
triage_request(chart, report) -> tuple[dict, dict]
    # question "system": Choice over chart.systems plus "none"
    # questions "pre_<node_id>": Choice over the node options plus "not_stated", for each node
answer_request(chart, report, node_id, answer_text, extra_node_ids) -> tuple[dict, dict]
    # question "answer": Choice over the node options plus "unclear"
    # questions "extra_<node_id>": Choice over the options plus "not_stated", at most 8
independent_request(chart, report, qa) -> tuple[dict, dict]
    # qa: list[{"question": str, "answer": str}]
    # question "diagnosis": Choice over chart.diagnoses plus "none"
```

The `pre_` and `extra_` questions do not include the neutral option `not_sure` of a
node. The option `not_stated` covers that case, and two options for one case confuse
Jev.

## Scores (`jev_mechanic/scoring.py`)

```python
initial_scores(chart, system_probs: dict[str, float]) -> dict[str, float]
update(chart, scores, node_id, option_probs: dict[str, float]) -> dict[str, float]
top(scores, n) -> list[tuple[str, float]]
FLAG_THRESHOLD = 0.9
```

## Ledger (`jev_mechanic/ledger.py`)

```python
JEV_PRICE_PER_MTOK = 0.042
OPUS5_INPUT_PRICE_PER_MTOK = 5.00

@dataclass
class LedgerRow:
    step: int          # 0 = triage, then 1, 2, ... for each answer
    lane: str          # "flowchart" | "independent"
    kind: str          # "A" | "B" | "C"
    input_tokens: int
    output_tokens: int
    model: str
    seconds: float
    jev_cost: float
    opus5_cost: float

class Ledger:
    def add(self, step, lane, kind, result: JevResult) -> LedgerRow: ...
    def totals(self) -> dict  # keys below
```

`totals()` returns `requests`, `input_tokens`, `output_tokens`, `jev_cost`,
`opus5_cost`, `compute_seconds` and `wait_seconds`. The value `wait_seconds` is the sum,
over the steps, of the longest request in each step.

## Session (`jev_mechanic/session.py`)

```python
class Session:
    def __init__(self, chart, jev: JevClient, report: str,
                 extra_questions: bool = True, independent_lane: bool = True): ...
    def start(self) -> None        # request A, and C at the same time
    def answer(self, text: str) -> None    # request B, and C at the same time
    def choose(self, option_id: str) -> None   # the user selects an option after "confirm"
    def accept(self) -> None       # the user accepts the flagged diagnosis
    def keep_going(self) -> None   # the user continues after a flag
    def view(self) -> dict         # the JSON view below
```

Send requests B and C at the same time with a `ThreadPoolExecutor` of two workers.

An action that does not apply to the status raises `session.SessionError`, a subclass
of `ValueError`. The server returns the status 400 for it. Each public method holds a
lock, so one session is safe across server threads.

### Status values

| Status | Meaning |
| --- | --- |
| `asking` | The app waits for an answer to `current.node_id`. |
| `confirm` | Jev was not sure. The UI shows `confirm_options` as buttons, and `choose` takes one. |
| `reask` | Jev could not map the answer. The UI shows the question again, with all option texts. |
| `flagged` | A diagnosis passed 0.9. The UI offers `accept` or `keep_going`. |
| `diagnosed` | The flowchart got to a diagnosis leaf, or the user accepted a flag. `fix` is set. |
| `specialist` | The flowchart got to the specialist leaf, or triage selected `none`. |

### The view

```json
{
  "id": "s_3f2a",
  "report": "...",
  "status": "asking",
  "triage": {"system": "no_start", "probabilities": {"no_start": 0.9, "brakes": 0.1, "none": 0.0}, "confidence": 0.85},
  "current": {
    "node_id": "q_key_turn",
    "question": "What happens when the driver turns the key to start?",
    "options": [{"id": "click_only", "text": "One click or rapid clicks, the engine does not turn"}],
    "yes_no": false
  },
  "confirm_options": [{"id": "click_only", "text": "...", "probability": 0.6}],
  "steps": [
    {"step": 1, "node_id": "q_key_turn", "question": "...", "answer_text": "a few clicks",
     "source": "user", "option": "click_only", "probabilities": {"click_only": 0.9, "unclear": 0.1},
     "confidence": 0.82, "outcome": "accepted"}
  ],
  "scores": [{"id": "flat_battery", "label": "Flat battery", "score": 0.62}],
  "flag": {"id": "flat_battery", "label": "Flat battery", "score": 0.93},
  "independent": {"enabled": true, "top": [{"id": "flat_battery", "label": "Flat battery", "score": 0.7}],
                  "flag": null},
  "diagnosis": {"id": "flat_battery", "label": "Flat battery", "description": "...", "fix": ["..."]},
  "path": ["q_key_turn"],
  "mermaid": "flowchart TD ...",
  "ledger": {"rows": [{"step": 0, "lane": "flowchart", "kind": "A", "input_tokens": 2100,
                      "output_tokens": 900, "model": "jev-1.13.0", "seconds": 0.8,
                      "jev_cost": 0.0000882, "opus5_cost": 0.0105}],
             "totals": {"requests": 2, "input_tokens": 3200, "output_tokens": 1000,
                        "jev_cost": 0.0001344, "opus5_cost": 0.016,
                        "compute_seconds": 1.5, "wait_seconds": 0.8}}
}
```

Field rules:

- `current` is null when the status is `diagnosed` or `specialist`.
- `confirm_options` is empty unless the status is `confirm`.
- `flag` and `diagnosis` are null when they do not apply.
- `scores` has the top eight diagnoses, and `independent.top` has the top five.
- The `source` of a step is `user` or `report`. A `report` step came from a `pre_` or an
  `extra_` answer. The `outcome` is `accepted`, `confirm`, `reask` or `chosen`.
- The `step` of a step is the number of the request that produced it, which matches the
  ledger. A `report` step from triage has the number 0. A `chosen` step has the number
  of its `confirm` step.

## HTTP API (`jev_mechanic/server.py`)

The server is a standard library `ThreadingHTTPServer`. It serves `static/` at `/` and
keeps the sessions in a dict in memory. Each POST body is JSON. Each response is the
session view, or an error `{"error": "..."}` with the status 400 or 404.

| Method and path | Body | Action |
| --- | --- | --- |
| `GET /api/examples` | none | `[{"id": ..., "title": ..., "report": ...}]` from `data/scenarios.json` |
| `POST /api/sessions` | `{"report", "extra_questions"?, "independent_lane"?}` | `Session(...)`, then `start()` |
| `GET /api/sessions/<id>` | none | `view()` |
| `POST /api/sessions/<id>/answer` | `{"text"}` | `answer(text)` |
| `POST /api/sessions/<id>/choose` | `{"option"}` | `choose(option)` |
| `POST /api/sessions/<id>/accept` | `{}` | `accept()` |
| `POST /api/sessions/<id>/continue` | `{}` | `keep_going()` |

`python -m jev_mechanic.server --port N` starts the server. The flag `--fake` uses
`FakeJev` with random answers, for UI work without API calls.

## Scenarios (`data/scenarios.json`)

```json
[
  {
    "id": "golf_slow_crank",
    "title": "Slow crank on cold mornings",
    "report": "...",
    "expected": "flat_battery",
    "answers": {"q_key_turn": "it turns over really slowly", "q_voltage": "11.9 volts"}
  }
]
```

`answers` has a free-text answer for each node that the case can reach.
