"""HTTP API and static files for the Jev mechanic demo."""

from __future__ import annotations

import argparse
import json
import re
import secrets
import threading
import traceback
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"
DEFAULT_FLOWCHART = ROOT / "data" / "flowchart.json"
DEFAULT_FLOWCHART_V2 = ROOT / "data" / "v2" / "flowchart.json"
SCENARIOS_PATH = ROOT / "data" / "scenarios.json"
CASES_V2_PATH = ROOT / "data" / "v2" / "cases.json"
V2_MODES = ("report", "case_file")
MAX_BODY_BYTES = 64 * 1024

SESSION_ROUTE = re.compile(r"^/api/sessions/([A-Za-z0-9_-]+)(?:/(answer|choose|accept|continue))?$")


class ApiError(Exception):
    def __init__(self, status: HTTPStatus, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class SessionEntry:
    def __init__(self, session):
        self.session = session
        self.lock = threading.Lock()


class App:
    """Hold the flowchart, the Jev client and the sessions of one server process."""

    def __init__(self, flowchart_path: Path, fake: bool, flowchart_v2_path: Path = DEFAULT_FLOWCHART_V2):
        self.flowchart_path = flowchart_path
        self.flowchart_v2_path = flowchart_v2_path
        self.fake = fake
        self.sessions: dict[str, SessionEntry] = {}
        self.sessions_lock = threading.Lock()
        self._chart = None
        self._model = None
        self._jev = None
        self._setup_lock = threading.Lock()

    def chart(self):
        with self._setup_lock:
            if self._chart is None:
                from jev_mechanic.flowchart import FlowchartError, load

                try:
                    self._chart = load(self.flowchart_path)
                except FileNotFoundError as error:
                    raise ApiError(HTTPStatus.INTERNAL_SERVER_ERROR, f"flowchart not found: {error.filename}") from error
                except FlowchartError as error:
                    raise ApiError(HTTPStatus.INTERNAL_SERVER_ERROR, f"flowchart is not valid: {error}") from error
            return self._chart

    def model(self):
        with self._setup_lock:
            if self._model is None:
                from jev_mechanic.flowchart import FlowchartError
                from jev_mechanic.v2.model import load

                try:
                    self._model = load(self.flowchart_v2_path)
                except FileNotFoundError as error:
                    raise ApiError(
                        HTTPStatus.INTERNAL_SERVER_ERROR, f"version 2 flowchart not found: {error.filename}"
                    ) from error
                except FlowchartError as error:
                    raise ApiError(HTTPStatus.INTERNAL_SERVER_ERROR, f"version 2 flowchart is not valid: {error}") from error
            return self._model

    def jev(self):
        with self._setup_lock:
            if self._jev is None:
                if self.fake:
                    from jev_mechanic.jev import FakeJev

                    self._jev = FakeJev()
                else:
                    from jev_mechanic.jev import LiveJev

                    self._jev = LiveJev()
            return self._jev

    def examples(self) -> list[dict]:
        if not SCENARIOS_PATH.exists():
            return []
        try:
            scenarios = json.loads(SCENARIOS_PATH.read_text())
        except json.JSONDecodeError as error:
            raise ApiError(HTTPStatus.INTERNAL_SERVER_ERROR, f"scenarios.json is not valid JSON: {error}") from error
        return [
            {"id": s.get("id"), "title": s.get("title"), "report": s.get("report")}
            for s in scenarios
            if isinstance(s, dict) and s.get("report")
        ]

    def cases(self) -> list[dict]:
        if not CASES_V2_PATH.exists():
            return []
        try:
            cases = json.loads(CASES_V2_PATH.read_text())
        except json.JSONDecodeError as error:
            raise ApiError(HTTPStatus.INTERNAL_SERVER_ERROR, f"cases.json is not valid JSON: {error}") from error
        keys = ("id", "title", "report", "case_file", "faults", "tags", "date")
        return [{key: c.get(key) for key in keys} for c in cases if isinstance(c, dict) and c.get("id")]

    def case(self, case_id: str) -> dict:
        for case in self.cases():
            if case["id"] == case_id:
                return case
        raise ApiError(HTTPStatus.NOT_FOUND, f"no version 2 case {case_id}")

    def create_session(self, body: dict) -> dict:
        options = {}
        for key in ("extra_questions", "independent_lane"):
            if key in body:
                if not isinstance(body[key], bool):
                    raise ApiError(HTTPStatus.BAD_REQUEST, f"'{key}' must be true or false")
                options[key] = body[key]
        version = body.get("version", 1)
        if version == 2:
            session = self._session_v2(body, options)
        elif version == 1:
            report = body.get("report")
            if not isinstance(report, str) or not report.strip():
                raise ApiError(HTTPStatus.BAD_REQUEST, "the body needs a non-empty 'report' string")
            from jev_mechanic.session import Session

            session = Session(self.chart(), self.jev(), report.strip(), **options)
        else:
            raise ApiError(HTTPStatus.BAD_REQUEST, "'version' must be 1 or 2")
        _run_jev(session.start)
        view = session.view()
        entry = SessionEntry(session)
        with self.sessions_lock:
            session_id = view.get("id")
            if not isinstance(session_id, str) or not session_id or session_id in self.sessions:
                session_id = _new_id(self.sessions)
            self.sessions[session_id] = entry
        view["id"] = session_id
        return view

    def _session_v2(self, body: dict, options: dict):
        mode = body.get("mode")
        if mode not in V2_MODES:
            raise ApiError(HTTPStatus.BAD_REQUEST, "'mode' must be 'report' or 'case_file'")
        case_id = body.get("case_id")
        if case_id is not None:
            if not isinstance(case_id, str) or not case_id:
                raise ApiError(HTTPStatus.BAD_REQUEST, "'case_id' must be a non-empty string")
            case = self.case(case_id)
            report, case_file, date = case.get("report"), case.get("case_file"), case.get("date")
        elif mode == "report":
            report, case_file, date = body.get("report"), None, None
        else:
            raise ApiError(HTTPStatus.BAD_REQUEST, "the mode 'case_file' needs a 'case_id'")
        if not isinstance(report, str) or not report.strip():
            raise ApiError(HTTPStatus.BAD_REQUEST, "the session needs a non-empty report")
        if mode == "case_file" and not isinstance(case_file, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, f"the case {case_id} has no case file")

        from jev_mechanic.v2.session import Session

        return Session(
            self.model(), self.jev(), mode, report.strip(), case_file=case_file, date=date, **options
        )

    def entry(self, session_id: str) -> SessionEntry:
        with self.sessions_lock:
            entry = self.sessions.get(session_id)
        if entry is None:
            raise ApiError(HTTPStatus.NOT_FOUND, f"no session {session_id}")
        return entry

    def act(self, session_id: str, action: str | None, body: dict) -> dict:
        entry = self.entry(session_id)
        with entry.lock:
            session = entry.session
            if action == "answer":
                text = body.get("text")
                if not isinstance(text, str) or not text.strip():
                    raise ApiError(HTTPStatus.BAD_REQUEST, "the body needs a non-empty 'text' string")
                _run_jev(lambda: session.answer(text.strip()))
            elif action == "choose":
                option = body.get("option")
                if not isinstance(option, str) or not option:
                    raise ApiError(HTTPStatus.BAD_REQUEST, "the body needs an 'option' string")
                _run_jev(lambda: session.choose(option))
            elif action == "accept":
                _run_jev(session.accept)
            elif action == "continue":
                _run_jev(session.keep_going)
            return _view(session, session_id)


def _new_id(existing: dict) -> str:
    while True:
        session_id = f"s_{secrets.token_hex(3)}"
        if session_id not in existing:
            return session_id


def _view(session, session_id: str) -> dict:
    view = session.view()
    view["id"] = session_id
    return view


def _run_jev(call) -> None:
    """Run one session action. A state error gives 400, and a failed Jev call gives 502."""
    from jev_mechanic.session import SessionError

    try:
        call()
    except ApiError:
        raise
    except SessionError as error:
        raise ApiError(HTTPStatus.BAD_REQUEST, str(error) or type(error).__name__) from error
    except Exception as error:
        traceback.print_exc()
        raise ApiError(HTTPStatus.BAD_GATEWAY, f"Jev call failed: {type(error).__name__}: {error}") from error


class Handler(SimpleHTTPRequestHandler):
    app: App

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:
        if urlsplit(self.path).path.startswith("/api/"):
            super().log_message(format, *args)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if not path.startswith("/api/"):
            super().do_GET()
            return
        self._handle(lambda: self._get(path))

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        self._handle(lambda: self._post(path))

    def _get(self, path: str):
        if path == "/api/examples":
            return self.app.examples()
        if path == "/api/v2/cases":
            return self.app.cases()
        match = SESSION_ROUTE.match(path)
        if match and match.group(2) is None:
            entry = self.app.entry(match.group(1))
            with entry.lock:
                return _view(entry.session, match.group(1))
        raise ApiError(HTTPStatus.NOT_FOUND, f"no route {path}")

    def _post(self, path: str):
        body = self._body()
        if path == "/api/sessions":
            return self.app.create_session(body)
        match = SESSION_ROUTE.match(path)
        if match and match.group(2) is not None:
            return self.app.act(match.group(1), match.group(2), body)
        raise ApiError(HTTPStatus.NOT_FOUND, f"no route {path}")

    def _body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError as error:
            raise ApiError(HTTPStatus.BAD_REQUEST, "bad Content-Length") from error
        if length > MAX_BODY_BYTES:
            raise ApiError(HTTPStatus.BAD_REQUEST, "the body is too large")
        raw = self.rfile.read(length) if length else b""
        if not raw.strip():
            return {}
        try:
            body = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ApiError(HTTPStatus.BAD_REQUEST, f"the body is not valid JSON: {error}") from error
        if not isinstance(body, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "the body must be a JSON object")
        return body

    def _handle(self, produce) -> None:
        try:
            payload = produce()
            status = HTTPStatus.OK
        except ApiError as error:
            payload, status = {"error": error.message}, error.status
        except Exception as error:
            traceback.print_exc()
            payload = {"error": f"{type(error).__name__}: {error}"}
            status = HTTPStatus.INTERNAL_SERVER_ERROR
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the Jev mechanic demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8780)
    parser.add_argument("--fake", action="store_true", help="use FakeJev with random answers, with no API calls")
    parser.add_argument("--flowchart", type=Path, default=DEFAULT_FLOWCHART)
    parser.add_argument("--flowchart-v2", type=Path, default=DEFAULT_FLOWCHART_V2)
    args = parser.parse_args()

    Handler.app = App(args.flowchart.resolve(), args.fake, args.flowchart_v2.resolve())
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.daemon_threads = True
    mode = "fake Jev" if args.fake else "live Jev"
    print(f"Jev mechanic demo ({mode}): http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
