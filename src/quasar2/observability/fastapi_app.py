"""Optional FastAPI app sharing the stdlib handler table."""

from __future__ import annotations

from typing import Any


def create_app() -> Any:
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse, Response
    except ImportError as error:
        raise RuntimeError("FastAPI extra not installed; use `quasar2 serve` stdlib server") from error

    from quasar2.observability.http import handle
    import uuid

    app = FastAPI(title="QUASAR2 API", version="v1")

    @app.api_route("/{full_path:path}", methods=["GET", "POST"])
    async def catch_all(full_path: str, request: Request) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        body = await request.body()
        path = request.url.path
        if request.url.query:
            path = f"{path}?{request.url.query}"
        status, headers, payload = handle(request.method, path, body, request_id)
        media = headers.get("Content-Type", "application/json")
        return Response(content=payload, status_code=status, media_type=media, headers=headers)

    return app
