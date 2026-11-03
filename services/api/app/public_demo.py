"""Pure ASGI limits and anonymous workspace cookies. Request bodies are bounded before JSON parsing."""

import asyncio
import json
import sqlite3
import time
from collections import deque
from http.cookies import CookieError, SimpleCookie
from threading import Lock
from urllib.parse import urlsplit

from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.services.workspaces import WorkspaceStore
from app.settings import Settings


class RateLimits:
    def __init__(self) -> None:
        self.buckets: dict[tuple[str, str], deque[float]] = {}
        self.lock = Lock()

    def allow(self, identity: str, kind: str, limit: int, seconds: int) -> bool:
        now = time.monotonic()
        with self.lock:
            # Bound memory even when untrusted clients cycle IPs. Fail closed at capacity.
            if len(self.buckets) >= 10000:
                self.buckets = {
                    key: values
                    for key, values in self.buckets.items()
                    if values and values[-1] > now - 3600
                }
                if (identity, kind) not in self.buckets and len(self.buckets) >= 10000:
                    return False
            bucket = self.buckets.setdefault((identity, kind), deque())
            while bucket and bucket[0] <= now - seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True


class DemoGuard:
    def __init__(
        self, app: ASGIApp, settings: Settings, store: WorkspaceStore | None = None
    ) -> None:
        self.app, self.settings, self.store = app, settings, store
        self.limits = RateLimits()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            await self.app(scope, receive, send)
            return
        settings = self.settings
        headers = Headers(scope=scope)
        method = scope["method"]
        write = method in {"POST", "PUT", "PATCH", "DELETE"}
        new_cookie: str | None = None
        clear_cookie = False
        try:
            if settings.public_demo:
                if self.store is not None and self.store.maintenance_failed:
                    raise HTTPException(503, "Demo maintenance is unavailable. Try again shortly")
                try:
                    host = urlsplit("//" + headers.get("host", ""))
                    _port = host.port
                except ValueError as exc:
                    raise HTTPException(400, "Invalid Host header") from exc
                allowed = {urlsplit(settings.origin).hostname}
                if scope["path"] == "/api/health":
                    allowed.add("localhost")
                if host.hostname not in allowed or host.username or host.path:
                    raise HTTPException(400, "Host is not configured for this demo")
                if (
                    headers.get("origin") not in {None, settings.origin}
                    or headers.get("sec-fetch-site") == "cross-site"
                ):
                    raise HTTPException(
                        403, "This demo accepts requests only from its configured site"
                    )
                identity = (scope.get("client") or ("unknown", 0))[0]
                if scope["path"] != "/api/health" and method != "OPTIONS":
                    limit = settings.writes_per_minute if write else settings.reads_per_minute
                    if not self.limits.allow(identity, "write" if write else "read", limit, 60):
                        raise HTTPException(
                            429,
                            "Demo request limit reached. Wait a minute and retry",
                            headers={"Retry-After": "60"},
                        )
            declared = headers.get("content-length")
            if declared is not None:
                try:
                    size = int(declared)
                except ValueError as exc:
                    raise HTTPException(400, "Invalid Content-Length") from exc
                if size < 0:
                    raise HTTPException(400, "Invalid Content-Length")
                if size > settings.body_bytes:
                    raise HTTPException(
                        413, "Request is too large. Reduce the procedure or graph size"
                    )
            if write:
                if headers.get("content-type", "").split(";", 1)[0].lower() != "application/json":
                    raise HTTPException(415, "Send the request as application/json")
                body = bytearray()
                deadline = time.monotonic() + settings.body_timeout
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise HTTPException(408, "Request body took too long to arrive")
                    try:
                        message = await asyncio.wait_for(receive(), remaining)
                    except TimeoutError as exc:
                        raise HTTPException(408, "Request body took too long to arrive") from exc
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > settings.body_bytes:
                        raise HTTPException(
                            413, "Request is too large. Reduce the procedure or graph size"
                        )
                    if not message.get("more_body", False):
                        break
                depth, in_string, escaped = 0, False, False
                for byte in body:
                    if in_string:
                        if escaped:
                            escaped = False
                        elif byte == 92:
                            escaped = True
                        elif byte == 34:
                            in_string = False
                    elif byte == 34:
                        in_string = True
                    elif byte in (91, 123):
                        depth += 1
                        if depth > 64:
                            raise HTTPException(400, "JSON nesting exceeds the supported limit")
                    elif byte in (93, 125):
                        depth -= 1
                try:
                    parsed = json.loads(
                        body, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value))
                    )
                    json.dumps(parsed, ensure_ascii=False).encode("utf-8")
                except (ValueError, RecursionError, UnicodeError) as exc:
                    raise HTTPException(
                        400, "Request must contain valid, finite JSON and Unicode text"
                    ) from exc
                delivered = False
                original_receive = receive

                async def buffered_receive() -> Message:
                    nonlocal delivered
                    if not delivered:
                        delivered = True
                        return {"type": "http.request", "body": bytes(body), "more_body": False}
                    return await original_receive()

                receive = buffered_receive
            store = self.store
            if settings.public_demo and store is not None:
                scope.setdefault("state", {})["demo_store"] = store

                async def allocate() -> tuple[str, int]:
                    nonlocal new_cookie, clear_cookie
                    assert store is not None
                    client = (scope.get("client") or ("unknown", 0))[0]
                    if not self.limits.allow(
                        client, "new_workspace", settings.new_workspaces_per_hour, 3600
                    ):
                        raise HTTPException(
                            429,
                            "Too many new demo workspaces. Try again later",
                            headers={"Retry-After": "3600"},
                        )
                    try:
                        workspace = await run_in_threadpool(store.create)
                    except (OSError, sqlite3.Error) as exc:
                        raise HTTPException(
                            503, "Demo storage is temporarily unavailable. Try again later"
                        ) from exc
                    new_cookie = store.token(*workspace)
                    clear_cookie = False
                    scope["state"]["demo_workspace"] = workspace
                    return workspace

                if scope["path"] == "/api/demo/reset" and method == "POST":
                    # Only the validated reset handler may invoke this allocation. A GET
                    # or invalid body must never replace access to an existing workspace.
                    scope["state"]["reset_workspace"] = allocate
                elif scope["path"] != "/api/health" and method != "OPTIONS":
                    cookies: SimpleCookie = SimpleCookie()
                    try:
                        cookies.load(headers.get("cookie", ""))
                    except CookieError as exc:
                        clear_cookie = True
                        raise HTTPException(
                            400, "Invalid demo workspace cookie. Reload Explore demo"
                        ) from exc
                    cookie = cookies.get(settings.cookie_name)
                    workspace = None
                    if cookie:
                        try:
                            workspace = store.parse(cookie.value)
                        except HTTPException as exc:
                            clear_cookie = True
                            if exc.status_code != 410 or scope["path"] != "/api/demo":
                                raise
                    if workspace is not None and not store.path(*workspace).is_file():
                        clear_cookie = True
                        if scope["path"] != "/api/demo":
                            raise HTTPException(
                                410,
                                "This temporary workspace is unavailable. Open Explore demo to start again",
                            )
                        workspace = None
                    if workspace is None:
                        workspace = await allocate()
                    scope["state"]["demo_workspace"] = workspace
                else:
                    scope["state"]["demo_template"] = store.template

        except HTTPException as exc:
            response = JSONResponse(
                {"error": {"code": str(exc.status_code), "message": str(exc.detail)}},
                status_code=exc.status_code,
                headers=exc.headers,
            )
            if clear_cookie:
                response.delete_cookie(
                    settings.cookie_name,
                    secure=settings.cookie_secure,
                    httponly=True,
                    samesite="strict",
                )
            self._headers(response)
            await response(scope, receive, send)
            return

        async def guarded_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                outgoing = MutableHeaders(scope=message)
                outgoing["Cache-Control"] = "no-store"
                outgoing["X-Content-Type-Options"] = "nosniff"
                outgoing["Referrer-Policy"] = "no-referrer"
                if new_cookie is not None:
                    response = Response()
                    response.set_cookie(
                        settings.cookie_name,
                        new_cookie,
                        max_age=settings.ttl_seconds,
                        secure=settings.cookie_secure,
                        httponly=True,
                        samesite="strict",
                    )
                    outgoing.append("set-cookie", response.headers["set-cookie"])
            await send(message)

        await self.app(scope, receive, guarded_send)

    @staticmethod
    def _headers(response: Response) -> None:
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
