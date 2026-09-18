# Jev mechanic demo

A car workshop triage demo on TypeSafe Jev. The app takes a customer report, triages
it, follows a diagnostic flowchart and gives a fix checklist. Jev reads the report and
each free-text answer. Code follows the flowchart and computes the diagnosis scores. A
second, independent lane asks Jev for the diagnosis from the whole case at each step.
The app records the tokens, the cost and the time of each Jev call.

`CONTRACTS.md` and `CONTRACTS_V2.md` give the module interfaces.

## Run it

```bash
uv sync                                        # Python 3.11, typesafe-sdk 0.6.0, pytest
export TYPESAFE_API_KEY=...                    # the SDK reads it
.venv/bin/python -m jev_mechanic.server --port 8780
```

Open `http://127.0.0.1:8780`. Select an example report or type one.

Other entry points:

| Command | What it does |
| --- | --- |
| `.venv/bin/python -m jev_mechanic.server --fake` | UI with random answers and no API calls |
| `http://127.0.0.1:8780/?mock=1` | UI from `static/mock-view.json`, no server calls |
| `.venv/bin/python -m jev_mechanic.cli` | One live session in the terminal |
| `.venv/bin/python -m jev_mechanic.harness` | The 15 scenarios, live, with the fan-out on and off |
| `.venv/bin/python -m jev_mechanic.flowchart` | Validate `data/flowchart.json` |
| `.venv/bin/python -m pytest -q` | 90 tests, with no API calls |

The `pyproject.toml` file sets PyPI as the index. If your uv configuration adds a
private index, run `UV_INDEX= uv sync`.

## Files

| Path | Content |
| --- | --- |
| `data/flowchart.json` | 5 systems, 25 diagnoses, 39 question nodes, fix steps |
| `data/scenarios.json` | 15 scripted cases, with a free-text answer for each node |
| `jev_mechanic/flowchart.py` | Load, validate and draw the flowchart (Mermaid) |
| `jev_mechanic/questions.py` | The Jev requests A (triage), B (answer) and C (independent lane) |
| `jev_mechanic/scoring.py` | The soft-evidence Bayes update |
| `jev_mechanic/session.py` | Session state, confidence rules, the view for the UI |
| `jev_mechanic/ledger.py` | Tokens, Jev cost, Opus 5 cost and time for each request |
| `jev_mechanic/jev.py` | `LiveJev` (the SDK) and `FakeJev` (tests) |
| `jev_mechanic/server.py` | Standard library HTTP server and JSON API |
| `jev_mechanic/harness.py` | Scenario runs and the report in `reports/` |
| `static/` | The web UI |

## Measured results (2026-09-18, `jev-1.13.0`)

The harness writes its reports to `reports/`, which git does not track. This run has
15 cases for each variant, and it sends the cases one after the next.

| Measure | Fan-out on | Fan-out off |
| --- | --- | --- |
| Correct, flowchart lane | 14 / 15 | 14 / 15 |
| Correct, independent lane | 14 / 15 | 14 / 15 |
| Flowchart score passed 0.9 | 14 / 15 | 14 / 15 |
| User answers, total | 29 | 28 |
| Answers from the report, total | 14 | 14 |
| Requests for each session | 5.9 | 5.9 |
| Input tokens for each session | 18,638 | 17,665 |
| Jev cost for each session | $0.00078 | $0.00074 |
| Opus 5 cost for each session, same tokens | $0.093 | $0.088 |
| Jev cost for 1,000 sessions | $0.78 | $0.74 |
| Opus 5 cost for 1,000 sessions | $93 | $88 |
| Compute time for each session | 3.2 s | 3.2 s |
| Wait time for each session | 1.8 s | 1.8 s |

Request times with the fan-out on:

| Kind | Mean input tokens | Median | p95 | Max |
| --- | --- | --- | --- | --- |
| A, triage with 39 speculative questions | 10,400 | 1.09 s | 1.24 s | 1.28 s |
| B, answer interpretation | 1,158 | 0.33 s | 0.39 s | 0.42 s |
| C, independent lane | 2,045 | 0.36 s | 0.86 s | 1.55 s |

Notes on the results:

- Request A uses 10,400 tokens, five times the first estimate. The 39 `pre_`
  questions carry structured criteria. They answered 14 of the 43 questions from the
  report, so the user typed 29 answers in place of 43.
- The `extra_` questions in request B add approximately 1,000 tokens to a session. In
  these scenarios, they save no user answers, because each canned answer holds one fact.
- The flowchart lane never shows the 0.9 flag before the leaf. The branches are two or
  three questions deep, so the score passes 0.9 at the leaf step itself.
- The independent lane passes 0.9 earlier, often at step 0 or 1. It is correct in 14
  cases, but it has no flowchart and no fix path.
- The Opus 5 cost prices the Jev input tokens at $5.00 for each million. It is a lower
  limit, because it has no output tokens, no thinking and no tokenizer difference.

## The two cases that fail

- `yaris_hunting_idle` (flowchart lane). The mechanic answers the vacuum-leak question
  with "might be something, might not". Jev maps that answer to `not_sure` at 0.99,
  which is correct. The flowchart then continues past the vacuum-leak leaf and ends at
  `specialist`. The independent lane gives `vacuum_leak` at 0.84.
- `golf_slow_crank` (independent lane). The lane gives `starter_motor` at 0.36. The
  flowchart lane gives `flat_battery` at 0.94, which is correct. In the run before this
  one, the same lane gave `flat_battery` at 0.30 for the same state.
