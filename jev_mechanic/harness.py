"""Run the scripted scenarios end to end against Jev and write an accuracy, cost and time report."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from . import flowchart as fc
from .ledger import JEV_PRICE_PER_MTOK, OPUS5_INPUT_PRICE_PER_MTOK

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = ROOT / "data" / "scenarios.json"
REPORTS = ROOT / "reports"

# A user does not answer one node more than this number of times.
MAX_TRIES_PER_NODE = 2
MAX_ACTIONS = 40
FALLBACK_ANSWER = "Not sure, I did not check that."


@dataclass
class CaseResult:
    id: str
    variant: str
    expected: str
    final: str | None = None
    final_status: str | None = None
    correct: bool = False
    flag_step: int | None = None
    score_step: int | None = None
    final_score: float | None = None
    user_answers: int = 0
    report_answers: int = 0
    confirms: int = 0
    reasks: int = 0
    missing_answers: list[str] = field(default_factory=list)
    independent_final: str | None = None
    independent_score: float | None = None
    independent_flag_step: int | None = None
    independent_correct: bool = False
    lanes_agree: bool = False
    stuck: str | None = None
    error: str | None = None
    totals: dict = field(default_factory=dict)
    rows: list[dict] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)


def run_case(chart: fc.Flowchart, jev, case: dict, extra_questions: bool) -> CaseResult:
    """Drive one scenario through a session and return what happened."""
    from .session import Session

    variant = "fan-out on" if extra_questions else "fan-out off"
    result = CaseResult(case["id"], variant, case["expected"])
    session = Session(chart, jev, case["report"], extra_questions=extra_questions, independent_lane=True)
    tries: dict[str, int] = defaultdict(int)
    try:
        session.start()
        view = session.view()
        _track_independent(result, view, step=0)
        _track_scores(result, view, step=0)
        for _ in range(MAX_ACTIONS):
            status = view["status"]
            if status in ("diagnosed", "specialist"):
                break
            if status == "flagged":
                if result.flag_step is None:
                    result.flag_step = _last_step(view)
                session.accept()
            elif status == "confirm":
                result.confirms += 1
                best = max(view["confirm_options"], key=lambda o: o["probability"])
                session.choose(best["id"])
            elif status in ("asking", "reask"):
                node_id = view["current"]["node_id"]
                if status == "reask":
                    result.reasks += 1
                tries[node_id] += 1
                if tries[node_id] > MAX_TRIES_PER_NODE:
                    result.stuck = node_id
                    break
                text = case["answers"].get(node_id)
                if text is None:
                    result.missing_answers.append(node_id)
                    text = FALLBACK_ANSWER
                result.user_answers += 1
                session.answer(text)
            else:
                result.stuck = f"unknown status {status}"
                break
            view = session.view()
            _track_independent(result, view, step=_last_step(view))
            _track_scores(result, view, step=_last_step(view))
    except Exception as error:  # noqa: BLE001 - one failed case must not stop the run
        result.error = f"{type(error).__name__}: {error}"
        view = session.view()

    result.final_status = view["status"]
    if view.get("diagnosis"):
        result.final = view["diagnosis"]["id"]
    elif view["status"] == "specialist":
        result.final = fc.SPECIALIST
    result.correct = result.final == result.expected
    result.final_score = next((s["score"] for s in view["scores"] if s["id"] == result.final), None)
    result.report_answers = sum(1 for s in view["steps"] if s.get("source") == "report")
    top = (view.get("independent") or {}).get("top") or []
    if top:
        result.independent_final = top[0]["id"]
        result.independent_score = top[0]["score"]
        result.independent_correct = top[0]["id"] == result.expected
    result.lanes_agree = result.final == result.independent_final
    result.totals = view["ledger"]["totals"]
    result.rows = view["ledger"]["rows"]
    result.steps = view["steps"]
    return result


def _last_step(view: dict) -> int:
    return max((s["step"] for s in view["steps"]), default=0)


def _track_independent(result: CaseResult, view: dict, step: int) -> None:
    flag = (view.get("independent") or {}).get("flag")
    if flag and result.independent_flag_step is None:
        result.independent_flag_step = step


def _track_scores(result: CaseResult, view: dict, step: int) -> None:
    scores = view.get("scores") or []
    if scores and scores[0]["score"] > 0.9 and result.score_step is None:
        result.score_step = step


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return ordered[index]


def summarize(results: list[CaseResult]) -> dict:
    """Return the totals and the request-time statistics for one variant."""
    n = len(results)
    keys = ("requests", "input_tokens", "jev_cost", "opus5_cost", "compute_seconds", "wait_seconds")
    totals = {k: sum(r.totals.get(k, 0) for r in results) for k in keys}
    by_kind: dict[str, list[float]] = defaultdict(list)
    tokens_by_kind: dict[str, list[int]] = defaultdict(list)
    for r in results:
        for row in r.rows:
            by_kind[row["kind"]].append(row["seconds"])
            tokens_by_kind[row["kind"]].append(row["input_tokens"])
    times = {
        kind: {
            "count": len(v),
            "min": min(v),
            "median": statistics.median(v),
            "p95": _percentile(v, 0.95),
            "max": max(v),
            "mean_input_tokens": statistics.mean(tokens_by_kind[kind]),
        }
        for kind, v in sorted(by_kind.items())
    }
    return {
        "cases": n,
        "correct": sum(r.correct for r in results),
        "independent_correct": sum(r.independent_correct for r in results),
        "lanes_agree": sum(r.lanes_agree for r in results),
        "flagged": sum(r.flag_step is not None for r in results),
        "passed_09": sum(r.score_step is not None for r in results),
        "user_answers": sum(r.user_answers for r in results),
        "report_answers": sum(r.report_answers for r in results),
        "errors": sum(r.error is not None for r in results),
        "totals": totals,
        "per_session": {k: (v / n if n else 0) for k, v in totals.items()},
        "request_times": times,
    }


def _money(value: float) -> str:
    return f"${value:.6f}" if value < 0.01 else f"${value:.4f}"


def render_markdown(results: dict[str, list[CaseResult]], summaries: dict[str, dict], meta: dict) -> str:
    lines = [
        "# Harness report",
        "",
        f"Run at {meta['started']} on `{meta['model']}`, {meta['duration']:.0f} s. "
        f"Prices: Jev ${JEV_PRICE_PER_MTOK} and Opus 5 ${OPUS5_INPUT_PRICE_PER_MTOK:.2f} "
        "for each million input tokens.",
        "",
        "The Opus 5 column prices the Jev input tokens at the Opus 5 input price. "
        "It is a lower limit. It has no output tokens and no tokenizer difference.",
        "",
    ]
    for variant, summary in summaries.items():
        s, per = summary, summary["per_session"]
        lines += [
            f"## {variant}",
            "",
            "| Measure | Value |",
            "| --- | --- |",
            f"| Correct, flowchart lane | {s['correct']} / {s['cases']} |",
            f"| Correct, independent lane | {s['independent_correct']} / {s['cases']} |",
            f"| Lanes agree | {s['lanes_agree']} / {s['cases']} |",
            f"| Cases with a 0.9 flag before the leaf | {s['flagged']} / {s['cases']} |",
            f"| Cases where the flowchart score passed 0.9 | {s['passed_09']} / {s['cases']} |",
            f"| User answers, total | {s['user_answers']} |",
            f"| Answers from the report, total | {s['report_answers']} |",
            f"| Errors | {s['errors']} |",
            f"| Requests for each session | {per['requests']:.1f} |",
            f"| Input tokens for each session | {per['input_tokens']:.0f} |",
            f"| Jev cost for each session | {_money(per['jev_cost'])} |",
            f"| Opus 5 cost for each session, same tokens | {_money(per['opus5_cost'])} |",
            f"| Jev cost for 1,000 sessions | {_money(per['jev_cost'] * 1000)} |",
            f"| Opus 5 cost for 1,000 sessions | {_money(per['opus5_cost'] * 1000)} |",
            f"| Compute time for each session | {per['compute_seconds']:.2f} s |",
            f"| Wait time for each session | {per['wait_seconds']:.2f} s |",
            "",
            "| Kind | Requests | Mean input tokens | Min s | Median s | p95 s | Max s |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for kind, t in s["request_times"].items():
            lines.append(
                f"| {kind} | {t['count']} | {t['mean_input_tokens']:.0f} | {t['min']:.2f} | "
                f"{t['median']:.2f} | {t['p95']:.2f} | {t['max']:.2f} |"
            )
        lines += [
            "",
            "| Case | Expected | Flowchart (score) | 0.9 step | Independent | Ind. flag step | "
            "User / report answers | Confirm / reask | Tokens | Wait s | Note |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for r in results[variant]:
            mark = "ok" if r.correct else "WRONG"
            ind = f"{r.independent_final} ({r.independent_score:.2f})" if r.independent_final else "-"
            note = r.error or (f"stuck at {r.stuck}" if r.stuck else "")
            if r.missing_answers:
                note += f" no answer for {', '.join(r.missing_answers)}"
            score = f" ({r.final_score:.2f})" if r.final_score is not None else ""
            lines.append(
                f"| {r.id} | {r.expected} | {r.final}{score} {mark} | {r.score_step if r.score_step is not None else '-'} "
                f"| {ind} | {r.independent_flag_step if r.independent_flag_step is not None else '-'} "
                f"| {r.user_answers} / {r.report_answers} | {r.confirms} / {r.reasks} "
                f"| {r.totals.get('input_tokens', 0)} | {r.totals.get('wait_seconds', 0):.2f} | {note.strip()} |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fake", action="store_true", help="use FakeJev, with no API calls")
    parser.add_argument("--only", nargs="*", help="scenario ids to run")
    parser.add_argument("--variant", choices=["on", "off", "both"], default="both",
                        help="speculative fan-out in request B")
    parser.add_argument("--workers", type=int, default=1,
                        help="cases at the same time; more than 1 changes the request times")
    parser.add_argument("--flowchart", default=str(fc.DEFAULT_PATH))
    parser.add_argument("--scenarios", default=str(SCENARIOS))
    args = parser.parse_args()

    from .jev import FakeJev, LiveJev

    chart = fc.load(args.flowchart)
    cases = json.loads(Path(args.scenarios).read_text())
    if args.only:
        cases = [c for c in cases if c["id"] in args.only]
    variants = {"on": [True], "off": [False], "both": [True, False]}[args.variant]

    started = datetime.now()
    t0 = time.perf_counter()
    results: dict[str, list[CaseResult]] = {}
    for extra in variants:
        def one(case: dict, extra: bool = extra) -> CaseResult:
            jev = FakeJev(seed=hash(case["id"]) % 10_000) if args.fake else LiveJev()
            r = run_case(chart, jev, case, extra)
            print(f"  {r.variant:12} {r.id:32} {str(r.final):28} {'ok' if r.correct else 'WRONG'}"
                  f"  {r.totals.get('input_tokens', 0):6} tok  {r.totals.get('wait_seconds', 0):5.2f} s"
                  + (f"  {r.error}" if r.error else ""))
            return r
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            batch = list(pool.map(one, cases))
        results[batch[0].variant if batch else str(extra)] = batch

    summaries = {variant: summarize(rs) for variant, rs in results.items() if rs}
    models = {row["model"] for rs in results.values() for r in rs for row in r.rows}
    meta = {
        "started": started.isoformat(timespec="seconds"),
        "duration": time.perf_counter() - t0,
        "model": ", ".join(sorted(models)) or "none",
        "fake": args.fake,
        "workers": args.workers,
    }
    REPORTS.mkdir(exist_ok=True)
    stem = REPORTS / f"harness-{started:%Y%m%d-%H%M%S}{'-fake' if args.fake else ''}"
    stem.with_suffix(".md").write_text(render_markdown(results, summaries, meta))
    stem.with_suffix(".json").write_text(json.dumps(
        {"meta": meta, "summaries": summaries,
         "results": {v: [asdict(r) for r in rs] for v, rs in results.items()}},
        indent=2,
    ))
    for variant, s in summaries.items():
        per = s["per_session"]
        print(f"{variant}: {s['correct']}/{s['cases']} correct, independent {s['independent_correct']}/{s['cases']}, "
              f"{per['input_tokens']:.0f} tok/session, Jev {_money(per['jev_cost'])}, "
              f"Opus 5 {_money(per['opus5_cost'])}, wait {per['wait_seconds']:.2f} s/session")
    print(f"report: {stem.with_suffix('.md')}")


if __name__ == "__main__":
    main()
