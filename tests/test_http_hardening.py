import json
import socket
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from quasar2.observability.http import QuasarHandler, handle


class HttpValidation(unittest.TestCase):
    def test_invalid_payloads_are_client_errors(self):
        for body in (b"[]", b"null", b"3", b'"text"', b"{", b"\xff", b'{"entropy":NaN}'):
            with self.subTest(body=body):
                status, headers, _ = handle("POST", "/v1/plan", body, "test")
                self.assertEqual(status, 400)
                self.assertEqual(headers["X-Request-ID"], "test")

    def test_zero_values_are_preserved(self):
        with patch("quasar2.aera.planner.plan_horizon2", return_value={}) as planner:
            self.assertEqual(
                handle("POST", "/v1/plan", b'{"entropy":0,"margin":0,"budget":0}', "id")[0], 200
            )
        self.assertEqual(planner.call_args.kwargs["remaining_budget"], 0)
        self.assertEqual(planner.call_args.kwargs["entropy"], 0)
        self.assertEqual(planner.call_args.kwargs["margin"], 0)

    def test_invalid_plan_fields_are_rejected(self):
        for data in (
            {"budget": -1},
            {"margin": 2},
            {"entropy": -1},
            {"budget": True},
            {"entropy": "bad"},
            {"budget": None},
            {"budget": 1e309},
        ):
            with self.subTest(data=data):
                self.assertEqual(
                    handle("POST", "/v1/plan", json.dumps(data).encode(), "id")[0], 400
                )

    def test_decision_requires_nonempty_string(self):
        for query in ("   ", 123, ["star"], {}, "x" * 4001):
            with self.subTest(query=query):
                self.assertEqual(
                    handle("POST", "/v1/decide", json.dumps({"query": query}).encode(), "id")[0],
                    400,
                )

    def test_handle_enforces_body_limit(self):
        self.assertEqual(handle("POST", "/v1/runs", b" " * 32001, "id")[0], 413)

    def test_internal_errors_are_not_exposed(self):
        with patch(
            "quasar2.observability.http.list_runs", side_effect=RuntimeError("/private/file secret")
        ):
            status, _, body = handle("GET", "/v1/runs", b"", "id")
        self.assertEqual(status, 500)
        self.assertNotIn(b"secret", body)


class StdlibWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), QuasarHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, headers):
        with socket.create_connection(self.server.server_address, timeout=2) as connection:
            connection.sendall(
                b"POST /v1/runs HTTP/1.0\r\nHost: localhost\r\n" + headers + b"\r\n\r\n"
            )
            connection.shutdown(socket.SHUT_WR)
            chunks = []
            while True:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
        return b"".join(chunks)

    def test_invalid_framing_is_rejected(self):
        for headers in (
            b"Content-Length: -1",
            b"Content-Length: invalid",
            b"Content-Length: 0\r\nContent-Length: 1",
            b"Transfer-Encoding: chunked",
            b"Content-Length: 5",
        ):
            with self.subTest(headers=headers):
                self.assertIn(b" 400 ", self.request(headers).split(b"\r\n", 1)[0])

    def test_oversize_framing_is_rejected(self):
        response = self.request(b"Content-Length: 32001")
        self.assertIn(b" 413 ", response.split(b"\r\n", 1)[0])
        self.assertIn(b"Content-Type: application/json", response)


class FastApiParity(unittest.TestCase):
    def setUp(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("optional FastAPI/httpx not installed")
        from quasar2.observability.fastapi_app import create_app

        self.client = TestClient(create_app())
        self.addCleanup(self.client.close)

    def test_health_accepts_injected_request(self):
        response = self.client.get("/health", headers={"X-Request-ID": "test"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Request-ID"], "test")

    def test_limits_and_validation_match_stdlib(self):
        self.assertEqual(self.client.post("/v1/plan", json=[]).status_code, 400)
        self.assertEqual(self.client.post("/v1/runs", content=b" " * 32001).status_code, 413)

    def test_runtime_work_uses_worker_thread(self):
        with patch(
            "quasar2.observability.http.handle",
            side_effect=lambda *a: (
                200,
                {"Content-Type": "application/json"},
                json.dumps({"thread": threading.current_thread().name}).encode(),
            ),
        ):
            response = self.client.get("/health")
        self.assertIn("worker", response.json()["thread"].lower())
