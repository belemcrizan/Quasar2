"""World Bank Indicators API V2 client. Network is used only during sync."""

from __future__ import annotations

from dataclasses import dataclass
import json
import random
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_BASE = "https://api.worldbank.org/v2"
DEFAULT_USER_AGENT = "QUASAR2/0.2.0 research (+https://github.com/belemcrizan/Quasar2)"


@dataclass(frozen=True, slots=True)
class HttpResponse:
    url: str
    status: int
    body: bytes
    elapsed_ms: float


class WorldBankClient:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout_s: float = 30.0,
        max_retries: int = 4,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self._opener = opener or urlopen

    def build_url(self, path: str, params: dict[str, Any] | None = None) -> str:
        query = {"format": "json", **(params or {})}
        return f"{self.base_url}/{path.lstrip('/')}?{urlencode(query, doseq=True)}"

    def get(self, path: str, params: dict[str, Any] | None = None) -> HttpResponse:
        url = self.build_url(path, params)
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            started = time.perf_counter()
            request = Request(url, headers={"User-Agent": self.user_agent, "Accept": "application/json"})
            try:
                with self._opener(request, timeout=self.timeout_s) as response:
                    body = response.read()
                    status = int(getattr(response, "status", 200))
                    return HttpResponse(url, status, body, (time.perf_counter() - started) * 1000.0)
            except HTTPError as error:
                last_error = error
                if error.code < 500 and error.code != 429:
                    raise
            except (URLError, TimeoutError, OSError) as error:
                last_error = error
            if attempt < self.max_retries:
                delay = (2**attempt) * 0.4 + random.random() * 0.3
                time.sleep(delay)
        raise RuntimeError(f"World Bank request failed after retries: {url}") from last_error

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> tuple[HttpResponse, Any]:
        response = self.get(path, params)
        payload = json.loads(response.body.decode("utf-8"))
        return response, payload

    def paginate(self, path: str, params: dict[str, Any] | None = None) -> tuple[list[HttpResponse], list[Any]]:
        """Follow page metadata until all items are retrieved."""

        responses: list[HttpResponse] = []
        items: list[Any] = []
        page = 1
        pages = 1
        while page <= pages:
            merged = dict(params or {})
            merged.setdefault("per_page", 1000)
            merged["page"] = page
            response, payload = self.get_json(path, merged)
            responses.append(response)
            meta, rows = _split_wb_payload(payload)
            pages = int(meta.get("pages") or 1)
            items.extend(rows)
            page += 1
        return responses, items


def _split_wb_payload(payload: Any) -> tuple[dict[str, Any], list[Any]]:
    if isinstance(payload, list) and payload and isinstance(payload[0], dict) and "message" in payload[0]:
        message = payload[0]["message"]
        raise ValueError(f"World Bank API message: {message}")
    if isinstance(payload, list) and len(payload) >= 2 and isinstance(payload[0], dict):
        meta = payload[0]
        rows = payload[1] if isinstance(payload[1], list) else []
        if rows is None:
            rows = []
        return meta, rows
    if isinstance(payload, dict):
        return payload, list(payload.get("value") or [])
    raise ValueError(f"Unexpected World Bank JSON payload: {str(payload)[:300]}")
