"""Optional FastAPI app sharing the stdlib handler table."""

from typing import Any


def create_app() -> Any:
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import Response
        from starlette.concurrency import run_in_threadpool
    except ImportError as error:
        raise RuntimeError(
            "FastAPI extra not installed; use `quasar2 serve` stdlib server"
        ) from error

    from quasar2.observability import http
    import uuid

    app = FastAPI(title="QUASAR2 API", version="v1")

    @app.api_route("/{full_path:path}", methods=["GET", "POST"])
    async def catch_all(full_path: str, request: Request) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > http.MAX_BODY_BYTES:
                return Response(
                    content=b'{"error":"payload too large"}',
                    status_code=413,
                    media_type="application/json",
                    headers={"X-Request-ID": request_id},
                )
            body.extend(chunk)
        path = request.url.path
        if request.url.query:
            path = f"{path}?{request.url.query}"
        status, headers, payload = await run_in_threadpool(
            http.handle, request.method, path, bytes(body), request_id
        )
        media = headers.get("Content-Type", "application/json")
        return Response(content=payload, status_code=status, media_type=media, headers=headers)

    return app
