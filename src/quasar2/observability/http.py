"""Stdlib HTTP API. Optional FastAPI wrapper uses the same handlers."""

from __future__ import annotations

import json
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from quasar2.observability import datasets_catalog, default_rescue_dir, list_runs, load_run, project_root
from quasar2.observability.html import render_cockpit, render_demo_page
from quasar2.rescue.policy import action_registry
from quasar2.rescue.trace import runtime_only

OPENAPI = {
    "openapi": "3.0.3",
    "info": {"title": "QUASAR2 API", "version": "v1", "description": "Runtime endpoints never return oracle fields."},
    "paths": {
        "/health": {"get": {"summary": "liveness"}},
        "/ready": {"get": {"summary": "readiness"}},
        "/v1/decide": {"post": {"summary": "deployment-valid decision"}},
        "/v1/runs": {"get": {"summary": "list runs"}, "post": {"summary": "record a client run id"}},
        "/v1/runs/{run_id}": {"get": {"summary": "run manifest without forcing oracle"}},
        "/v1/traces/{trace_id}": {"get": {"summary": "runtime trace"}},
        "/v1/metrics": {"get": {"summary": "aggregate metrics from artifacts"}},
        "/v1/claims": {"get": {"summary": "claim ledger from artifacts"}},
        "/v1/datasets": {"get": {"summary": "dataset maturity"}},
        "/v1/actions": {"get": {"summary": "action catalog"}},
    },
}


def _json(payload: Any, status: int = 200) -> tuple[int, dict[str, str], bytes]:
    body = json.dumps(payload, ensure_ascii=True, default=str).encode("utf-8")
    return status, {"Content-Type": "application/json; charset=utf-8"}, body


def handle(method: str, path: str, body: bytes, request_id: str) -> tuple[int, dict[str, str], bytes]:
    parsed = urlparse(path)
    route = parsed.path.rstrip("/") or "/"
    headers_base = {"X-Request-ID": request_id}
    try:
        if method == "GET" and route == "/health":
            status, headers, payload = _json({"status": "ok"})
        elif method == "GET" and route == "/ready":
            root = project_root()
            ready = (root / "configs" / "poc.yaml").exists()
            status, headers, payload = _json({"ready": ready}, 200 if ready else 503)
        elif method == "GET" and route in {"/", "/dashboard"}:
            html = render_cockpit()
            return 200, {**headers_base, "Content-Type": "text/html; charset=utf-8"}, html.encode("utf-8")
        elif method == "GET" and route == "/demo":
            html = render_demo_page()
            return 200, {**headers_base, "Content-Type": "text/html; charset=utf-8"}, html.encode("utf-8")
        elif method == "GET" and route in {"/docs", "/v1/openapi.json", "/openapi.json"}:
            status, headers, payload = _json(OPENAPI)
        elif method == "POST" and route == "/v1/decide":
            data = json.loads(body.decode("utf-8") or "{}")
            query = str(data.get("query") or "")
            domain = str(data.get("domain") or "astronomy")
            if not query or len(query) > 4000:
                status, headers, payload = _json({"error": "invalid query"}, 400)
            else:
                from quasar2.observability.demo import decide_runtime

                result = decide_runtime(query, domain)
                status, headers, payload = _json(result)
        elif method == "GET" and route == "/v1/runs":
            status, headers, payload = _json({"runs": list_runs()})
        elif method == "POST" and route == "/v1/runs":
            data = json.loads(body.decode("utf-8") or "{}")
            status, headers, payload = _json({"run_id": data.get("run_id") or str(uuid.uuid4()), "accepted": True})
        elif method == "GET" and route.startswith("/v1/runs/"):
            run_id = route.split("/")[-1]
            match = next((item for item in list_runs() if item["run_id"] == run_id), None)
            if not match:
                status, headers, payload = _json({"error": "not found"}, 404)
            else:
                from pathlib import Path

                loaded = load_run(Path(match["path"]))
                manifest = dict(loaded.get("manifest") or {})
                status, headers, payload = _json({"run_id": run_id, "gates": manifest.get("gates"), "n": manifest.get("n_queries")})
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
            status, headers, payload = _json({"claims": (loaded.get("manifest") or {}).get("claims")})
        elif method == "GET" and route == "/v1/datasets":
            status, headers, payload = _json({"datasets": datasets_catalog()})
        elif method == "GET" and route == "/v1/actions":
            status, headers, payload = _json({"actions": action_registry()})
        else:
            status, headers, payload = _json({"error": "not found"}, 404)
    except json.JSONDecodeError:
        status, headers, payload = _json({"error": "invalid json"}, 400)
    except Exception as error:  # pragma: no cover - surfaced to client
        status, headers, payload = _json({"error": str(error)}, 500)
    headers.update(headers_base)
    return status, headers, payload


class QuasarHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _dispatch(self) -> None:
        request_id = self.headers.get("X-Request-ID") or str(uuid.uuid4())
        length = int(self.headers.get("Content-Length") or 0)
        if length > 32_000:
            self.send_response(413)
            self.send_header("X-Request-ID", request_id)
            self.end_headers()
            self.wfile.write(b'{"error":"payload too large"}')
            return
        body = self.rfile.read(length) if length else b""
        status, headers, payload = handle(self.command, self.path, body, request_id)
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch()


def serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    httpd = ThreadingHTTPServer((host, port), QuasarHandler)
    print(json.dumps({"serve": f"http://{host}:{port}", "health": "/health", "cockpit": "/", "openapi": "/v1/openapi.json"}))
    httpd.serve_forever()
