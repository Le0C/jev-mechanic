# Benchmark run, 2026-09-18

Jev ran each scripted case with no person in the loop. The harness gives the canned
answer of the case to each question that the app asks. All requests went to
`jev-1.13.0`, one case after the next.

| File | Content |
| --- | --- |
| `v1-single-fault.md`, `.json` | Version 1: 15 single-fault cases, with the `extra_` questions on and off |
| `v2-multi-fault.md`, `.json` | Version 2: 20 cases with 1 to 3 faults, from the typed report and from the case file |

Commands:

```bash
.venv/bin/python -m jev_mechanic.harness       # version 1
.venv/bin/python -m jev_mechanic.v2.harness    # version 2
```

## Version 1, single fault

| Measure | Extra questions on | Extra questions off |
| --- | --- | --- |
| Correct, flowchart lane | 13 / 15 | 13 / 15 |
| Correct, independent lane | 15 / 15 | 15 / 15 |
| Requests for each session | 5.9 | 6.0 |
| Input tokens for each session | 18,828 | 18,066 |
| Jev cost for each session | $0.00079 | $0.00076 |
| Compute time for each session | 3.1 s | 3.3 s |
| Wait time for each session | 1.8 s | 1.9 s |

| Request | Mean input tokens | Median time | p95 time |
| --- | --- | --- | --- |
| A, triage | 10,400 | 1.03 s | 1.10 s |
| B, answer | 1,158 | 0.34 s | 0.50 s |
| C, independent lane | 2,110 | 0.34 s | 0.79 s |

The flowchart lane fails two cases:

- `yaris_hunting_idle`. The vague answer maps to "not sure", and the flowchart then
  passes the vacuum-leak leaf and ends at the specialist.
- `megane_motorway_hot`. Jev returns `reask` twice on the scripted answer at
  `q_co_top_hose`, and the harness stops the case. A person can give a clearer answer
  there.

## Version 2, 1 to 3 faults

| Measure | Typed report | Case file |
| --- | --- | --- |
| Exact fault set, loop | 8 / 20 | 11 / 20 |
| Fault precision, loop | 0.83 | 0.91 |
| Fault recall, loop | 0.64 | 0.79 |
| Exact fault set, independent lane | 8 / 20 | 14 / 20 |
| Fault precision, independent lane | 0.74 | 0.88 |
| Fault recall, independent lane | 0.74 | 0.95 |
| Requests for each case | 11.8 | 7.5 |
| Input tokens for each case | 60,378 | 56,695 |
| Jev cost for each case | $0.0025 | $0.0024 |
| Compute time for each case | 5.7 s | 4.5 s |
| Wait time for each case | 3.5 s | 2.9 s |

| Request (case file) | Mean input tokens | Median time | p95 time |
| --- | --- | --- | --- |
| E, evidence (68 symptoms, 16 components) | 18,122 | 1.26 s | 1.62 s |
| A, branch | 5,344 | 0.33 s | 0.66 s |
| B, answer | 1,877 | 0.31 s | 0.45 s |
| C, independent lane (44 diagnoses) | 8,848 | 0.39 s | 1.05 s |

Notes on version 2:

- The case file gives better results than the typed report in both lanes. It also needs
  fewer requests, because it answers more flowchart questions before the user does.
- In each mode, 6 of the 20 cases end early for a reason in the script, before the loop
  can finish:
  - The loop visits a component for which the case has no canned answers.
  - Jev returns `reask` twice on a canned answer, at `q_wp_symptom` or at
    `q_sta_symptom`.

  A person in the app answers those questions, so these cases give a lower limit for
  the loop.
- The other 14 cases end normally. In those cases, the loop finds the exact fault set
  8 times with the typed report, and 11 times with the case file.
- The independent lane reads the whole case at each step. In the case-file mode, it
  finds the exact fault set more often than the loop, but it gives no fix path.

## Cost in comparison with Opus 5

The report files price the Jev input tokens at the Opus 5 input price, $5.00 for each
million tokens. On that basis, one version 2 case costs $0.28 to $0.30 with Opus 5.
The same case costs $0.0024 to $0.0025 with Jev. The Opus 5 figure is a lower limit,
because it leaves out the output tokens and any thinking.
