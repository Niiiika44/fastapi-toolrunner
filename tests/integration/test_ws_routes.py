import contextlib
import json

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from app.core.config import get_settings
from app.main import app
from app.memory_allocator.enums import TestStatus
from app.memory_allocator.notifications import get_channel_name
from app.memory_allocator.schemas import TestStatusEvent
from tests.factories import make_user


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("ws_bus", "ws_session")
@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({}, id="no-token"),
        pytest.param({"Authorization": "Bearer garbage"}, id="broken-token"),
        pytest.param({"Authorization": "Basic garbage"}, id="wrong-scheme"),
    ],
)
async def test_ws_rejects_bad_credentials(headers):
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/tests/999999/status", headers=headers):
            pass

    assert exc_info.value.code == 1008


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("ws_bus", "ws_session")
async def test_ws_rejects_unknown_test(alembic_uow, auth_headers):
    user = make_user()
    alembic_uow.users.add(user)
    await alembic_uow.commit()

    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/tests/999999/status", headers=auth_headers(user)
        ) as ws:
            ws.receive_text()

    assert exc_info.value.code == 4404


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("ws_bus", "ws_session")
async def test_ws_sends_snapshot(parsed_test, auth_headers):
    user, test = parsed_test

    client = TestClient(app)

    with client.websocket_connect(
        f"/tests/{test.id}/status", headers=auth_headers(user)
    ) as ws:
        message = json.loads(ws.receive_text())

    assert message["event"] == "test.status"
    assert message["test_id"] == test.id
    assert message["status"] == "parsed"
    assert message["error_message"] is None
    assert message["ts"] is not None


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("ws_session")
async def test_ws_delivers_live_event(ws_bus, parsed_test, auth_headers):
    user, test = parsed_test

    client = TestClient(app)

    with client.websocket_connect(
        f"/tests/{test.id}/status", headers=auth_headers(user)
    ) as ws:
        ws.receive_text()

        event = TestStatusEvent(
            test_id=test.id, status=TestStatus.ERROR, error_message="boom"
        )
        await ws_bus.publish(get_channel_name(test.id), event.model_dump_json())

        message = json.loads(ws.receive_text())

    assert message["event"] == "test.status"
    assert message["test_id"] == test.id
    assert message["status"] == "error"
    assert message["error_message"] == "boom"
    assert message["ts"] is not None


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("ws_bus", "ws_session")
async def test_ws_limits_connections_per_user(parsed_test, auth_headers):
    user, test = parsed_test

    path = f"/tests/{test.id}/status"
    headers = auth_headers(user)
    limit = get_settings().WS_MAX_CONNECTIONS_PER_USER
    client = TestClient(app)

    with contextlib.ExitStack() as stack:
        for _ in range(limit):
            ws = stack.enter_context(client.websocket_connect(path, headers=headers))
            ws.receive_text()

        with pytest.raises(WebSocketDisconnect) as exc_info:
            extra = stack.enter_context(client.websocket_connect(path, headers=headers))
            extra.receive_text()

    assert exc_info.value.code == 1013

    with client.websocket_connect(path, headers=headers) as ws:
        ws.receive_text()
