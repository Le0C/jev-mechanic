"""Run the version 2 cases end to end in both evidence modes, and report set accuracy, cost and time."""

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

from ..harness import FALLBACK_ANSWER, MAX_TRIES_PER_NODE, _money, _percentile
from ..ledger import JEV_PRICE_PER_MTOK, OPUS5_INPUT_PRICE_PER_MTOK
from . import model as fm

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "data" / "v2" / "cases.json"
REPORTS = ROOT / "reports"
MAX_ACTIONS = 80
MODES = ("report", "case_file")


@dataclass
class CaseResult:
    id: str
    mode: str
    expected: list[str]
    tags: list[str]
    found: list[str] = field(default_factory=list)
    final_status: str | None = None
    true_positives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    exact: bool = False
    root_first_ok: bool | None = None
    independent: list[str] = field(default_factory=list)
    independent_precision: float = 0.0
    independent_recall: float = 0.0
    independent_exact: bool = False
    loops: int = 0
    user_answers: int = 0
    report_answers: int = 0
    confirms: int = 0
    reasks: int = 0
    unexplained: list[str] = field(default_factory=list)
    missing_answers: list[str] = field(default_factory=list)
    stuck: str | None = None
    error: str | None = None
    totals: dict = field(default_factory=dict)
    rows: list[dict] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)


def _set_scores(found: list[str], expected: list[str]) -> tuple[int, float, float]:
    tp = len(set(found) & set(expected))
    precision = tp / len(set(found)) if found else (1.0 if not expected else 0.0)
    recall = tp / len(set(expected)) if expected else 1.0
    return tp, precision, recall


def run_case(model: fm.FaultModel, jev, case: dict, mode: str, extra_questions: bool = True) -> CaseResult:
    """Drive one case through a version 2 session and return what happened."""
    from .session import Session

    result = CaseResult(case["id"], mode, list(case["faults"]), list(case.get("tags", [])))
    session = Session(
        model,
        jev,
        mode,
        case["report"],
        case_file=case.get("case_file"),
        date=case.get("date"),
        extra_questions=extra_questions,
        independent_lane=True,
    )
    tries: dict[str, int] = defaultdict(int)
    try:
        session.start()
        view = session.view()
        for _ in range(MAX_ACTIONS):
            status = view["status"]
            if status in ("complete", "specialist"):
                break
            if status == "flagged":
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
    except Exception as error:  # noqa: BLE001 - one failed case must not stop the run
        result.error = f"{type(error).__name__}: {error}"
        view = session.view()

    result.final_status = view["status"]
    result.found = [f["id"] for f in view.get("faults") or []]
    result.true_positives, result.precision, result.recall = _set_scores(result.found, result.expected)
    result.exact = set(result.found) == set(result.expected)
    if "cascade" in result.tags and result.exact:
        fix_order = [f["diagnosis"] for f in view.get("fix") or []]
        result.root_first_ok = fix_order == model.root_first(result.expected)
    result.independent = [f["id"] for f in (view.get("independent") or {}).get("faults") or []]
    _, result.independent_precision, result.independent_recall = _set_scores(result.independent, result.expected)
    result.independent_exact = set(result.independent) == set(result.expected)
    result.loops = (view.get("loop") or {}).get("index") or 0
    result.report_answers = sum(1 for s in view["steps"] if s.get("source") == "report")
    result.unexplained = [u["id"] for u in view.get("unexplained") or []]
    result.totals = view["ledger"]["totals"]
    result.rows = view["ledger"]["rows"]
    result.steps = view["steps"]
    return result


def summarize(results: list[CaseResult]) -> dict:
    """Return the accuracy totals and the request-time statistics for one mode."""
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
    cascades = [r for r in results if r.root_first_ok is not None]
    expected_total = sum(len(r.expected) for r in results)
    found_total = sum(len(r.found) for r in results)
    ind_found = sum(len(r.independent) for r in results)
    ind_tp = sum(len(set(r.independent) & set(r.expected)) for r in results)
    return {
        "cases": n,
        "exact": sum(r.exact for r in results),
        "precision": sum(r.true_positives for r in results) / found_total if found_total else 0.0,
        "recall": sum(r.true_positives for r in results) / expected_total if expected_total else 0.0,
        "root_first_ok": sum(bool(r.root_first_ok) for r in cascades),
        "cascades_scored": len(cascades),
        "independent_exact": sum(r.independent_exact for r in results),
        "independent_precision": ind_tp / ind_found if ind_found else 0.0,
        "independent_recall": ind_tp / expected_total if expected_total else 0.0,
        "user_answers": sum(r.user_answers for r in results),
        "report_answers": sum(r.report_answers for r in results),
        "errors": sum(r.error is not None for r in results),
        "totals": totals,
        "per_case": {k: (v / n if n else 0) for k, v in totals.items()},
        "request_times": times,
    }


def render_markdown(results: dict[str, list[CaseResult]], summaries: dict[str, dict], meta: dict) -> str:
    lines = [
        "# Version 2 harness report",
        "",
        f"Run at {meta['started']} on `{meta['model']}`, {meta['duration']:.0f} s, "
        f"{meta['workers']} case(s) at the same time. Prices: Jev ${JEV_PRICE_PER_MTOK} and "
        f"Opus 5 ${OPUS5_INPUT_PRICE_PER_MTOK:.2f} for each million input tokens.",
        "",
        "The Opus 5 column prices the Jev input tokens at the Opus 5 input price. "
        "It is a lower limit. It has no output tokens and no tokenizer difference.",
        "",
    ]
    for mode, s in summaries.items():
        per = s["per_case"]
        lines += [
            f"## Mode: {mode}",
            "",
            "| Measure | Value |",
            "| --- | --- |",
            f"| Exact fault set, loop | {s['exact']} / {s['cases']} |",
            f"| Fault precision, loop | {s['precision']:.2f} |",
            f"| Fault recall, loop | {s['recall']:.2f} |",
            f"| Cascade fix order root first | {s['root_first_ok']} / {s['cascades_scored']} |",
            f"| Exact fault set, independent lane | {s['independent_exact']} / {s['cases']} |",
            f"| Fault precision, independent lane | {s['independent_precision']:.2f} |",
            f"| Fault recall, independent lane | {s['independent_recall']:.2f} |",
            f"| User answers, total | {s['user_answers']} |",
            f"| Answers from the evidence, total | {s['report_answers']} |",
            f"| Errors | {s['errors']} |",
            f"| Requests for each case | {per['requests']:.1f} |",
            f"| Input tokens for each case | {per['input_tokens']:.0f} |",
            f"| Jev cost for each case | {_money(per['jev_cost'])} |",
            f"| Opus 5 cost for each case, same tokens | {_money(per['opus5_cost'])} |",
            f"| Jev cost for 1,000 cases | {_money(per['jev_cost'] * 1000)} |",
            f"| Opus 5 cost for 1,000 cases | {_money(per['opus5_cost'] * 1000)} |",
            f"| Compute time for each case | {per['compute_seconds']:.2f} s |",
            f"| Wait time for each case | {per['wait_seconds']:.2f} s |",
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
            "| Case | Tags | Expected | Found (loop) | Independent | Loops | User / evidence answers "
            "| Confirm / reask | Tokens | Wait s | Note |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for r in results[mode]:
            mark = "ok" if r.exact else "WRONG"
            note = r.error or (f"stuck at {r.stuck}" if r.stuck else "")
            if r.root_first_ok is False:
                note += " fix order wrong"
            if r.unexplained:
                note += f" unexplained: {', '.join(r.unexplained)}"
            if r.missing_answers:
                note += f" no answer for {', '.join(r.missing_answers)}"
            lines.append(
                f"| {r.id} | {', '.join(r.tags)} | {', '.join(r.expected)} | {', '.join(r.found) or '-'} {mark} "
                f"| {', '.join(r.independent) or '-'} {'ok' if r.independent_exact else 'WRONG'} | {r.loops} "
                f"| {r.user_answers} / {r.report_answers} | {r.confirms} / {r.reasks} "
                f"| {r.totals.get('input_tokens', 0)} | {r.totals.get('wait_seconds', 0):.2f} | {note.strip()} |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fake", action="store_true", help="use FakeJev, with no API calls")
    parser.add_argument("--only", nargs="*", help="case ids to run")
    parser.add_argument("--mode", choices=[*MODES, "both"], default="both")
    parser.add_argument("--no-extra", action="store_true", help="turn off the extra_ questions in request B")
    parser.add_argument("--workers", type=int, default=1,
                        help="cases at the same time; more than 1 changes the request times")
    parser.add_argument("--flowchart", default=str(fm.DEFAULT_PATH))
    parser.add_argument("--cases", default=str(CASES))
    args = parser.parse_args()

    from ..jev import FakeJev, LiveJev

    model = fm.load(args.flowchart)
    cases = json.loads(Path(args.cases).read_text())
    if args.only:
        cases = [c for c in cases if c["id"] in args.only]
    modes = MODES if args.mode == "both" else (args.mode,)

    started = datetime.now()
    t0 = time.perf_counter()
    results: dict[str, list[CaseResult]] = {}
    for mode in modes:
        def one(case: dict, mode: str = mode) -> CaseResult:
            jev = FakeJev(seed=hash(case["id"]) % 10_000) if args.fake else LiveJev()
            r = run_case(model, jev, case, mode, extra_questions=not args.no_extra)
            print(f"  {mode:9} {r.id:34} {'ok' if r.exact else 'WRONG':5} found={','.join(r.found) or '-':40} "
                  f"ind={','.join(r.independent) or '-':30} {r.totals.get('input_tokens', 0):7} tok "
                  f"{r.totals.get('wait_seconds', 0):5.2f} s" + (f"  {r.error}" if r.error else ""))
            return r
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            results[mode] = list(pool.map(one, cases))

    summaries = {mode: summarize(rs) for mode, rs in results.items() if rs}
    models = {row["model"] for rs in results.values() for r in rs for row in r.rows}
    meta = {
        "started": started.isoformat(timespec="seconds"),
        "duration": time.perf_counter() - t0,
        "model": ", ".join(sorted(models)) or "none",
        "fake": args.fake,
        "workers": args.workers,
    }
    REPORTS.mkdir(exist_ok=True)
    stem = REPORTS / f"v2-harness-{started:%Y%m%d-%H%M%S}{'-fake' if args.fake else ''}"
    stem.with_suffix(".md").write_text(render_markdown(results, summaries, meta))
    stem.with_suffix(".json").write_text(json.dumps(
        {"meta": meta, "summaries": summaries,
         "results": {m: [asdict(r) for r in rs] for m, rs in results.items()}},
        indent=2,
    ))
    for mode, s in summaries.items():
        per = s["per_case"]
        print(f"{mode}: exact {s['exact']}/{s['cases']}, P {s['precision']:.2f} R {s['recall']:.2f}, "
              f"independent exact {s['independent_exact']}/{s['cases']}, {per['input_tokens']:.0f} tok/case, "
              f"Jev {_money(per['jev_cost'])}, Opus 5 {_money(per['opus5_cost'])}, wait {per['wait_seconds']:.2f} s/case")
    print(f"report: {stem.with_suffix('.md')}")


if __name__ == "__main__":
    main()
