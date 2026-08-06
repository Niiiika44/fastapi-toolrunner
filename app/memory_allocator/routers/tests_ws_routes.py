import asyncio
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.auth.access_token_encoder import get_token_expiry
from app.auth.dependencies import authenticate_user
from app.auth.exceptions import InvalidTokenError
from app.core.config import get_settings
from app.core.context import request_id_var
from app.core.dependencies import get_event_bus
from app.core.events import EventBus
from app.core.unit_of_work import UnitOfWork
from app.db.database import AsyncSessionLocal
from app.memory_allocator.exceptions import TestNotFoundError
from app.memory_allocator.notifications import get_channel_name
from app.memory_allocator.schemas import TestStatusEvent
from app.memory_allocator.services.testcase_service import TestcaseService
from app.users.exceptions import UserNotFoundError
from app.users.services import UserService

settings = get_settings()

router = APIRouter(prefix="/tests", tags=["tests"])

logger = logging.getLogger(__name__)

_connections: dict[UUID, int] = {}


class TooManyConnectionsError(Exception):
    def __init__(self, user_id: UUID, limit: int):
        self.user_id = user_id
        self.limit = limit
        super().__init__(
            f"User {user_id} exceeded the limit of {limit} websocket connections"
        )


@asynccontextmanager
async def take_slot(user_id: UUID) -> AsyncIterator[None]:
    """counter per process"""
    current = _connections.get(user_id, 0)
    limit = settings.WS_MAX_CONNECTIONS_PER_USER
    if current >= limit:
        raise TooManyConnectionsError(user_id, limit)
    _connections[user_id] = current + 1
    try:
        yield
    finally:
        remaining = _connections[user_id] - 1
        if remaining:
            _connections[user_id] = remaining
        else:
            _connections.pop(user_id, None)


def _extract_credentials(websocket: WebSocket) -> tuple[str | None, str | None]:
    subprotocols = websocket.scope["subprotocols"]
    echo = "bearer" if "bearer" in subprotocols else None
    header = websocket.headers.get("authorization")
    if header:
        parts = header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1], echo

    if len(subprotocols) == 2 and subprotocols[0] == "bearer":
        return subprotocols[1], echo

    return None, echo


async def _send_events(websocket: WebSocket, stream: AsyncIterator[str]) -> None:
    async for raw in stream:
        await websocket.send_text(raw)


async def _watch_disconnect(websocket: WebSocket) -> None:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            return


async def _sleep_until(expires_at: int) -> None:
    delay = expires_at - time.time()
    if delay > 0:
        await asyncio.sleep(delay)


async def _stream_until_disconnect(
    websocket: WebSocket,
    stream: AsyncIterator[str],
    expires_at: int | None
) -> int:
    send = asyncio.create_task(_send_events(websocket, stream))
    watch = asyncio.create_task(_watch_disconnect(websocket))

    tasks = {send, watch}

    if expires_at is not None:
        expiry = asyncio.create_task(_sleep_until(expires_at))
        tasks.add(expiry)
    else:
        expiry = None

    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    for task in done:
        task.result()

    return 4401 if (expires_at is not None and expiry in done) else 1000


@router.websocket("/{test_id}/status")
async def test_status_ws(
    websocket: WebSocket,
    test_id: int,
    bus: EventBus = Depends(get_event_bus),
) -> None:
    request_id = str(uuid4())
    request_id_var.set(request_id)
    token, echo = _extract_credentials(websocket)
    if token is None:
        await websocket.close(code=1008)
        logger.info("ws.rejected", extra={
            "test_id": test_id,
            "reason": "no token",
            "close_code": 1008
        })
        return
    try:
        async with AsyncSessionLocal() as session:
            uow = UnitOfWork(session)
            user = await authenticate_user(token, UserService(uow))
            try:
                test = await TestcaseService(uow).get_by_id(test_id)
            except TestNotFoundError:
                test = None
    except (InvalidTokenError, UserNotFoundError) as exc:
        await websocket.close(code=1008)
        logger.info("ws.rejected", extra={
            "test_id": test_id,
            "reason": str(exc),
            "close_code": 1008
        })
        return
    except Exception as exc:
        await websocket.close(code=1011)
        logger.exception("ws.internal_error", extra={
            "test_id": test_id,
            "reason": str(exc),
            "close_code": 1011})
        return
    await websocket.accept(subprotocol=echo)
    expires_at = get_token_expiry(token, settings.SECRET_KEY, settings.JWT_ALGORITHM)
    if test is None:
        await websocket.close(code=4404)
        logger.info("ws.rejected", extra={
            "test_id": test_id,
            "reason": "no test",
            "close_code": 4404
        })
        return
    logger.info("ws.connected", extra={
        "test_id": test_id,
        "user_id": str(user.id),
        "transport": "subprotocols" if echo else "authorization"
    })
    started_at = time.monotonic()
    close_code = 1000
    try:
        async with take_slot(user.id), bus.subscribe(get_channel_name(test.id)) as stream:
            snapshot = TestStatusEvent(
                test_id=test_id,
                status=test.status,
                error_message=test.error_message
            )
            await websocket.send_text(snapshot.model_dump_json())
            close_code = await _stream_until_disconnect(websocket, stream, expires_at)
            if close_code == 4401:
                logger.info("ws.token_expired", extra={
                    "test_id": test_id,
                    "user_id": str(user.id),
                    "close_code": 4401
                })
    except TooManyConnectionsError as exc:
        close_code = 1013
        logger.info("ws.rejected", extra={
            "test_id": test_id, "user_id": str(user.id),
            "reason": "too_many_connections",
            "limit": exc.limit,
            "close_code": 1013
        })
    except Exception as exc:
        close_code = 1011
        logger.warning("ws.stream_error", extra={
            "test_id": test_id,
            "user_id": str(user.id),
            "error": str(exc),
            "close_code": 1011,
        })
    finally:
        logger.info("ws.disconnected", extra={
            "test_id": test_id,
            "user_id": str(user.id),
            "duration_ms": round((time.monotonic() - started_at) * 1000),
            "close_code": close_code
        })
        try:
            await websocket.close(
                code=close_code,
                reason="token expired" if close_code == 4401 else None
            )
        except (RuntimeError, WebSocketDisconnect):
            pass
