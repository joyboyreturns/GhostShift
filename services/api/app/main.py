import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from app.api.routes import router
from app.api.simulation import router as simulation_router
from app.api.workspace import router as workspace_router
from app.db import engine
from app.public_demo import DemoGuard
from app.services.seed import seed
from app.services.workspaces import WorkspaceStore
from app.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = WorkspaceStore(settings) if settings.public_demo else None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # Public requests copy a clean, explicitly migrated template. No schema creation
        # or migrations occur in startup/request handlers.
        if store is None:
            with Session(engine) as session:
                seed(session)
            yield
            return
        with store.server_lease():
            await asyncio.to_thread(store.cleanup)

            async def retention() -> None:
                while True:
                    await asyncio.sleep(300)
                    try:
                        await asyncio.to_thread(store.cleanup)
                        store.maintenance_failed = False
                    except OSError as exc:
                        store.maintenance_failed = True
                        logging.getLogger("ghostshift.maintenance").error(
                            "Temporary workspace cleanup failed: %s", type(exc).__name__
                        )

            task = asyncio.create_task(retention())
            try:
                yield
            finally:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    application = FastAPI(
        title="GhostShift",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.public_demo else "/docs",
        redoc_url=None if settings.public_demo else "/redoc",
        openapi_url=None if settings.public_demo else "/openapi.json",
    )
    application.state.demo_store = store
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.origin]
        if settings.public_demo
        else os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    application.add_middleware(DemoGuard, settings=settings, store=store)
    application.add_exception_handler(HTTPException, http_error)
    application.add_exception_handler(RequestValidationError, validation_error)
    application.add_exception_handler(IntegrityError, conflict_error)
    application.include_router(router)
    application.include_router(simulation_router)
    application.include_router(workspace_router)
    return application


async def http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "error": {"code": str(exc.status_code), "message": str(exc.detail)},
        },
    )


async def validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = [{"location": list(e["loc"]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={
            "error": {"code": "validation_error", "message": "Invalid request", "details": details},
        },
    )


async def conflict_error(_: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": {"code": "conflict", "message": "Conflicting write; reload and retry"},
        },
    )


app = create_app()
