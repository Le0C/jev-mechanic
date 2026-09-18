"""Run one triage session in the terminal: `python -m jev_mechanic.cli [--fake] [--v2]`."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import flowchart
from .jev import FakeJev, LiveJev
from .session import CONFIRM, DIAGNOSED, FLAGGED, SPECIALIST_STATUS, Session, SessionError

DEFAULT_CASES = Path(__file__).resolve().parent.parent / "data" / "v2" / "cases.json"


def _bar(score: float, width: int = 20) -> str:
    return "#" * round(score * width)


def show(view: dict) -> None:
    """Print a short form of the session view."""
    print(f"\n--- {view['id']}  status: {view['status']}")
    triage = view["triage"]
    if triage:
        print(f"triage: {triage['system']} (confidence {triage['confidence']:.2f})")
        for sid, p in sorted(triage["probabilities"].items(), key=lambda x: -x[1]):
            print(f"  {sid:<24} {p:5.2f} {_bar(p)}")
    for step in view["steps"]:
        print(
            f"  step {step['step']} [{step['source']}] {step['node_id']}: "
            f"{step['answer_text']!r} -> {step['option']} "
            f"(confidence {step['confidence']:.2f}, {step['outcome']})"
        )
    print("flowchart scores:")
    for s in view["scores"]:
        print(f"  {s['label']:<32} {s['score']:5.2f} {_bar(s['score'])}")
    ind = view["independent"]
    if ind["enabled"]:
        print("independent lane:")
        for s in ind["top"]:
            print(f"  {s['label']:<32} {s['score']:5.2f} {_bar(s['score'])}")
        if ind["flag"]:
            print(f"  flag: {ind['flag']['label']} ({ind['flag']['score']:.2f})")
    totals = view["ledger"]["totals"]
    print(
        f"ledger: {totals['requests']} requests, {totals['input_tokens']} input tokens, "
        f"Jev ${totals['jev_cost']:.6f}, Opus 5 ${totals['opus5_cost']:.4f}, "
        f"compute {totals['compute_seconds']:.2f} s, wait {totals['wait_seconds']:.2f} s"
    )
    if view["flag"]:
        print(f"FLAG: {view['flag']['label']} ({view['flag']['score']:.2f})")
    if view["diagnosis"]:
        d = view["diagnosis"]
        print(f"DIAGNOSIS: {d['label']}. {d['description']}")
        for i, line in enumerate(d["fix"], 1):
            print(f"  [ ] {i}. {line}")
    if view["status"] == SPECIALIST_STATUS:
        print("Refer the car to a specialist.")
    current = view["current"]
    if current and view["status"] not in (FLAGGED,):
        print(f"\nQ: {current['question']}")
        for o in current["options"]:
            print(f"   - {o['id']}: {o['text']}")


def _read(prompt: str) -> str:
    text = input(prompt).strip()
    while not text:
        text = input(prompt).strip()
    return text


def run(session: Session, as_json: bool = False, printer=show, done=(DIAGNOSED, SPECIALIST_STATUS)) -> None:
    """Start the session and read each answer from the terminal until a result."""

    def output() -> None:
        view = session.view()
        print(json.dumps(view, indent=2)) if as_json else printer(view)

    session.start()
    output()
    while session.status not in done:
        try:
            if session.status == FLAGGED:
                reply = _read("accept the flag? [y = accept, n = continue]: ").lower()
                session.accept() if reply.startswith("y") else session.keep_going()
            elif session.status == CONFIRM:
                options = session.view()["confirm_options"]
                for i, o in enumerate(options, 1):
                    print(f"  {i}. {o['text']} ({o['probability']:.2f})")
                reply = _read("select a number, or type a new answer: ")
                if reply.isdigit() and 1 <= int(reply) <= len(options):
                    session.choose(options[int(reply) - 1]["id"])
                else:
                    session.answer(reply)
            else:
                session.answer(_read("answer: "))
        except SessionError as error:
            print(f"error: {error}")
        output()


def show_v2(view: dict) -> None:
    """Print a short form of a version 2 session view."""
    print(f"\n--- {view['id']}  version 2  mode: {view['mode']}  status: {view['status']}")
    for r in view["evidence"]["removed"]:
        print(f"  removed from {r['source']}: {r['reason']}")
    print("symptoms:")
    for s in view["symptoms"]:
        mark = "x" if s["present"] else " "
        by = f" <- {s['explained_by']}" if s["explained_by"] else ""
        print(f"  [{mark}] {s['label']:<32} {s['probability'] or 0:5.2f}{by}")
    print("components:")
    for c in view["components"]:
        score = "" if c["score"] is None else f" score {c['score']:.2f}"
        print(f"  {c['label']:<32} {c['probability'] or 0:5.2f} {c['state']}{score}")
    loop = view["loop"]
    if loop["component"]:
        print(f"loop {loop['index']}: {loop['component']}")
    for step in view["steps"]:
        print(
            f"  loop {step['loop']} step {step['step']} [{step['source']}] {step['node_id']}: "
            f"{step['answer_text']!r} -> {step['option']} "
            f"(confidence {step['confidence']:.2f}, {step['outcome']})"
        )
    if view["branch_scores"]:
        print("branch scores:")
        for s in view["branch_scores"]:
            print(f"  {s['label']:<32} {s['score']:5.2f} {_bar(s['score'])}")
    ind = view["independent"]
    if ind["enabled"]:
        print("independent lane:")
        for s in ind["top"]:
            print(f"  {s['label']:<32} {s['score']:5.2f} {_bar(s['score'])}")
    totals = view["ledger"]["totals"]
    print(
        f"ledger: {totals['requests']} requests, {totals['input_tokens']} input tokens, "
        f"Jev ${totals['jev_cost']:.6f}, Opus 5 ${totals['opus5_cost']:.4f}, "
        f"compute {totals['compute_seconds']:.2f} s, wait {totals['wait_seconds']:.2f} s"
    )
    for f in view["faults"]:
        print(f"FAULT {f['loop']}: {f['label']} ({f['score']:.2f}), explains {', '.join(f['explains']) or 'no new symptom'}")
    if view["status"] in ("complete", SPECIALIST_STATUS):
        for item in view["fix"]:
            print(f"FIX {item['label']}:")
            for i, line in enumerate(item["steps"], 1):
                print(f"  [ ] {i}. {line}")
        for s in view["unexplained"]:
            print(f"UNEXPLAINED: {s['label']}")
        if view["status"] == SPECIALIST_STATUS:
            print("Refer the car to a specialist.")
    if view["flag"]:
        print(f"FLAG: {view['flag']['label']} ({view['flag']['score']:.2f})")
    current = view["current"]
    if current and view["status"] != FLAGGED:
        print(f"\nQ: {current['question']}")
        for o in current["options"]:
            print(f"   - {o['id']}: {o['text']}")


def run_v2(args) -> None:
    """Build a version 2 session from the arguments and run it."""
    from .v2 import model as v2_model
    from .v2.session import Session as SessionV2

    fault_model = v2_model.load(args.chart or v2_model.DEFAULT_PATH)
    report, case_file, date = args.report, None, None
    if args.case:
        cases = {c["id"]: c for c in json.loads(Path(args.cases).read_text())}
        if args.case not in cases:
            raise SystemExit(f"unknown case {args.case!r}, known cases: {', '.join(cases)}")
        case = cases[args.case]
        report, case_file, date = case["report"], case["case_file"], case.get("date")
    elif args.mode == "case_file":
        raise SystemExit("--mode case_file needs --case")
    jev = FakeJev(seed=args.seed) if args.fake else LiveJev()
    session = SessionV2(
        fault_model,
        jev,
        args.mode,
        report or _read("customer report: "),
        case_file=case_file,
        date=date,
        extra_questions=not args.no_extra,
        independent_lane=not args.no_independent,
    )
    run(session, as_json=args.json, printer=show_v2, done=("complete", SPECIALIST_STATUS))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fake", action="store_true", help="use FakeJev, with no API calls")
    parser.add_argument("--seed", type=int, default=None, help="random seed for --fake")
    parser.add_argument("--chart", default=None, help="flowchart JSON file (the default depends on the version)")
    parser.add_argument("--report", help="the customer report (the default is to read it from the terminal)")
    parser.add_argument("--no-extra", action="store_true", help="do not send extra_ questions")
    parser.add_argument("--no-independent", action="store_true", help="do not run the independent lane")
    parser.add_argument("--json", action="store_true", help="print the full view as JSON")
    parser.add_argument("--v2", action="store_true", help="run a version 2 session (1 to 3 faults)")
    parser.add_argument("--mode", choices=("report", "case_file"), default="report", help="version 2 evidence")
    parser.add_argument("--case", help="version 2 case id: take the report, case file and date from the case")
    parser.add_argument("--cases", default=str(DEFAULT_CASES), help="version 2 cases JSON file")
    args = parser.parse_args()

    if args.v2:
        try:
            run_v2(args)
        except (KeyboardInterrupt, EOFError):
            print("\nstopped")
        return

    chart = flowchart.load(args.chart or flowchart.DEFAULT_PATH)
    jev = FakeJev(seed=args.seed) if args.fake else LiveJev()
    report = args.report or _read("customer report: ")
    session = Session(
        chart,
        jev,
        report,
        extra_questions=not args.no_extra,
        independent_lane=not args.no_independent,
    )
    try:
        run(session, as_json=args.json)
    except (KeyboardInterrupt, EOFError):
        print("\nstopped")


if __name__ == "__main__":
    main()
