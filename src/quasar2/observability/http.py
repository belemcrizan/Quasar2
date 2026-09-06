"""Stdlib HTTP API. Optional FastAPI wrapper uses the same handlers."""

from __future__ import annotations

import json
import logging
import math
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from quasar2.observability import (
    datasets_catalog,
    default_rescue_dir,
    list_runs,
    load_run,
    project_root,
)
from quasar2.observability.html import render_cockpit, render_demo_page
from quasar2.rescue.policy import action_registry
from quasar2.rescue.trace import runtime_only

MAX_BODY_BYTES = 32_000
_LOGGER = logging.getLogger(__name__)


class InvalidRequest(ValueError):
    """An invalid client field, distinct from an internal pipeline failure."""


def _reject_constant(value: str) -> None:
    raise InvalidRequest(f"Non-finite JSON constant: {value}")


def _object_body(body: bytes) -> dict[str, Any]:
    try:
        value = json.loads(body.decode("utf-8") or "{}", parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise InvalidRequest("invalid json") from error
    if not isinstance(value, dict):
        raise InvalidRequest("JSON body must be an object")
    return value


def _number(data: dict[str, Any], name: str, default: float, maximum: float | None = None) -> float:
    value = data.get(name, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidRequest(f"{name} must be a number")
    try:
        valid = math.isfinite(value) and value >= 0 and (maximum is None or value <= maximum)
    except OverflowError:
        valid = False
    if not valid:
        raise InvalidRequest(f"{name} is outside its finite, non-negative range")
    return float(value)


OPENAPI = {
    "openapi": "3.0.3",
    "info": {
        "title": "QUASAR2 API",
        "version": "v1",
        "description": "Runtime endpoints never return oracle fields.",
    },
    "paths": {
        "/health": {"get": {"summary": "liveness"}},
        "/ready": {"get": {"summary": "readiness"}},
        "/v1/decide": {"post": {"summary": "deployment-valid decision"}},
        "/v1/decision": {"post": {"summary": "alias of /v1/decide"}},
        "/v1/plan": {"post": {"summary": "horizon-2 plan from entropy/margin; no gold"}},
        "/v1/verify": {"post": {"summary": "independent structured VERIFY; zero retrieval"}},
        "/v1/fleet": {"get": {"summary": "simulated fleet allocation"}},
        "/v1/evidence/{trace_id}": {"get": {"summary": "runtime evidence ids only"}},
        "/v1/runs": {
            "get": {"summary": "list runs"},
            "post": {"summary": "record a client run id"},
        },
        "/v1/runs/{run_id}": {"get": {"summary": "run manifest without forcing oracle"}},
        "/v1/traces/{trace_id}": {"get": {"summary": "runtime trace"}},
        "/v1/metrics": {"get": {"summary": "aggregate metrics from artifacts"}},
        "/v1/claims": {"get": {"summary": "claim ledger from artifacts"}},
        "/v1/datasets": {"get": {"summary": "dataset maturity"}},
        "/v1/actions": {"get": {"summary": "action catalog"}},
    },
}


def _json(payload: Any, status: int = 200) -> tuple[int, dict[str, str], bytes]:
    body = json.dumps(payload, ensure_ascii=True, default=str, allow_nan=False).encode("utf-8")
    return status, {"Content-Type": "application/json; charset=utf-8"}, body


def handle(
    method: str, path: str, body: bytes, request_id: str
) -> tuple[int, dict[str, str], bytes]:
    parsed = urlparse(path)
    route = parsed.path.rstrip("/") or "/"
    headers_base = {"X-Request-ID": request_id}
    if len(body) > MAX_BODY_BYTES:
        status, headers, payload = _json({"error": "payload too large"}, 413)
        return status, {**headers, **headers_base}, payload
    try:
        if method == "GET" and route == "/health":
            status, headers, payload = _json({"status": "ok"})
        elif method == "GET" and route == "/ready":
            root = project_root()
            ready = (root / "configs" / "poc.yaml").exists()
            status, headers, payload = _json({"ready": ready}, 200 if ready else 503)
        elif method == "GET" and route in {"/", "/dashboard"}:
            html = render_cockpit()
            return (
                200,
                {**headers_base, "Content-Type": "text/html; charset=utf-8"},
                html.encode("utf-8"),
            )
        elif method == "GET" and route == "/demo":
            html = render_demo_page()
            return (
                200,
                {**headers_base, "Content-Type": "text/html; charset=utf-8"},
                html.encode("utf-8"),
            )
        elif method == "GET" and route in {"/docs", "/v1/openapi.json", "/openapi.json"}:
            status, headers, payload = _json(OPENAPI)
        elif method == "POST" and route in {"/v1/decide", "/v1/decision"}:
            data = _object_body(body)
            query = data.get("query", "")
            domain = data.get("domain", "astronomy")
            if not isinstance(domain, str) or not domain.strip() or len(domain) > 100:
                raise InvalidRequest("invalid domain")
            if not isinstance(query, str) or not query.strip() or len(query) > 4000:
                status, headers, payload = _json({"error": "invalid query"}, 400)
            else:
                from quasar2.observability.demo import decide_runtime

                result = decide_runtime(query, domain)
                status, headers, payload = _json(result)
        elif method == "GET" and route == "/v1/runs":
            status, headers, payload = _json({"runs": list_runs()})
        elif method == "POST" and route == "/v1/runs":
            data = _object_body(body)
            status, headers, payload = _json(
                {"run_id": data.get("run_id") or str(uuid.uuid4()), "accepted": True}
            )
        elif method == "GET" and route.startswith("/v1/runs/"):
            run_id = route.split("/")[-1]
            match = next((item for item in list_runs() if item["run_id"] == run_id), None)
            if not match:
                status, headers, payload = _json({"error": "not found"}, 404)
            else:
                from pathlib import Path

                loaded = load_run(Path(match["path"]))
                manifest = dict(loaded.get("manifest") or {})
                status, headers, payload = _json(
                    {
                        "run_id": run_id,
                        "gates": manifest.get("gates"),
                        "n": manifest.get("n_queries"),
                    }
                )
        elif method == "GET" and route.startswith("/v1/traces/"):
            trace_id = route.split("/")[-1]
            loaded = load_run(default_rescue_dir())
            traces = loaded.get("traces") or []
            found = next((item for item in traces if item.get("trace_id") == trace_id), None)
            if not found:
                status, headers, payload = _json({"error": "not found"}, 404)
            else:
                status, headers, payload = _json(runtime_only(found))
        elif method == "GET" and route == "/v1/metrics":
            loaded = load_run(default_rescue_dir())
            manifest = loaded.get("manifest") or {}
            status, headers, payload = _json(
                {
                    "available": loaded.get("available"),
                    "gates": manifest.get("gates"),
                    "confirmatory_metrics": manifest.get("confirmatory_metrics"),
                }
            )
        elif method == "GET" and route == "/v1/claims":
            loaded = load_run(default_rescue_dir())
            status, headers, payload = _json(
                {"claims": (loaded.get("manifest") or {}).get("claims")}
            )
        elif method == "GET" and route == "/v1/datasets":
            status, headers, payload = _json({"datasets": datasets_catalog()})
        elif method == "GET" and route == "/v1/actions":
            status, headers, payload = _json({"actions": action_registry()})
        elif method == "POST" and route == "/v1/plan":
            data = _object_body(body)
            from quasar2.aera.planner import plan_horizon2

            plan = plan_horizon2(
                entropy=_number(data, "entropy", 0.5, maximum=1.0),
                margin=_number(data, "margin", 0.2, maximum=1.0),
                actions=("ANSWER", "BM25", "DISCRIMINATIVE", "ANALYZE", "VERIFY", "DEFER"),
                remaining_budget=_number(data, "budget", 0.4),
                costs={
                    "ANSWER": 0.0,
                    "BM25": 0.10,
                    "DISCRIMINATIVE": 0.25,
                    "ANALYZE": 0.02,
                    "VERIFY": 0.12,
                    "DEFER": 0.05,
                },
            )
            slim = {k: v for k, v in plan.items() if k not in {"first", "second"}}
            status, headers, payload = _json(slim)
        elif method == "POST" and route == "/v1/verify":
            data = _object_body(body)
            from quasar2.aera.verify import verify_claim
            from dataclasses import asdict

            result = verify_claim(
                str(data.get("claim") or ""), predicted_id=str(data.get("predicted_id") or "")
            )
            status, headers, payload = _json(asdict(result))
        elif method == "GET" and route == "/v1/fleet":
            from quasar2.aera.fleet import AgentBid, allocate

            demo = allocate(
                (
                    AgentBid("demo-1", 0.6, 0.1, 1.0, 0.2, "t0"),
                    AgentBid("demo-2", 0.3, 0.2, 0.5, 0.2, "t1"),
                ),
                global_budget=0.4,
            )
            status, headers, payload = _json({"simulation": True, **demo})
        elif method == "GET" and route.startswith("/v1/evidence/"):
            trace_id = route.split("/")[-1]
            loaded = load_run(default_rescue_dir())
            traces = loaded.get("traces") or []
            found = next((item for item in traces if item.get("trace_id") == trace_id), None)
            if not found:
                status, headers, payload = _json({"error": "not found"}, 404)
            else:
                runtime = (found.get("trace") or {}).get("runtime") or {}
                status, headers, payload = _json(
                    {
                        "trace_id": trace_id,
                        "document_ids": (runtime.get("retrieval") or {}).get("document_ids")
                        or runtime.get("document_ids")
                        or [],
                    }
                )
        else:
            status, headers, payload = _json({"error": "not found"}, 404)
    except InvalidRequest as error:
        status, headers, payload = _json({"error": str(error)}, 400)
    except Exception:
        _LOGGER.exception("Request failed: %s", request_id)
        status, headers, payload = _json({"error": "internal server error"}, 500)
    headers.update(headers_base)
    return status, headers, payload


class QuasarHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    timeout = 10.0

    def _send(self, status: int, headers: dict[str, str], payload: bytes) -> None:
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _dispatch(self) -> None:
        request_id = self.headers.get("X-Request-ID") or str(uuid.uuid4())

        def reject(status: int, message: str) -> None:
            self.close_connection = True
            code, headers, payload = _json({"error": message}, status)
            self._send(code, {**headers, "X-Request-ID": request_id}, payload)

        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) > 1 or self.headers.get("Transfer-Encoding") is not None:
            reject(400, "unsupported request framing")
            return
        raw_length = lengths[0].strip() if lengths else "0"
        if not raw_length.isascii() or not raw_length.isdecimal():
            reject(400, "invalid content length")
            return
        # Avoid parsing an unbounded integer before checking the body limit.
        if len(raw_length.lstrip("0")) > 5:
            reject(413, "payload too large")
            return
        length = int(raw_length.lstrip("0") or "0")
        if length > MAX_BODY_BYTES:
            reject(413, "payload too large")
            return
        try:
            body = self.rfile.read(length) if length else b""
        except TimeoutError:
            reject(408, "request body timed out")
            return
        if len(body) != length:
            reject(400, "incomplete request body")
            return
        self._send(*handle(self.command, self.path, body, request_id))

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch()


def serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    httpd = ThreadingHTTPServer((host, port), QuasarHandler)
    print(
        json.dumps(
            {
                "serve": f"http://{host}:{port}",
                "health": "/health",
                "cockpit": "/",
                "openapi": "/v1/openapi.json",
            }
        )
    )
    httpd.serve_forever()
