import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.auth.routes import router as auth_router
from app.core.config import get_settings
from app.core.context import request_id_var
from app.core.error_handler import create_exception_handlers
from app.core.events import (
    close_event_bus,
    create_redis_event_bus,
    init_event_bus,
)
from app.core.logging_config import setup_logging
from app.memory_allocator.routers.platforms_routes import router as platforms_router
from app.memory_allocator.routers.tags_routes import router as tags_router
from app.memory_allocator.routers.tests_routes import router as tests_router
from app.memory_allocator.routers.tests_ws_routes import router as ws_tests_router
from app.users.routes import router as users_router

setup_logging()

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        bus = create_redis_event_bus()
        init_event_bus(bus)
        try:
            await bus.ping()
            logger.info("app.event_bus_ready")
        except Exception as exc:
            logger.warning("app.event_bus_unavailable", extra={"error": str(exc)})
        yield
    finally:
        await close_event_bus()


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan
)

create_exception_handlers(app)

app.include_router(auth_router)
app.include_router(tests_router)
app.include_router(users_router)
app.include_router(platforms_router)
app.include_router(tags_router)
app.include_router(ws_tests_router)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health", tags=["infra"])
async def health_check() -> dict[str, str]:
    return {"message": "App is running!"}
