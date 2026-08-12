from collections.abc import AsyncGenerator, Awaitable, Callable

import pytest
import pytest_asyncio

from app.core.events import InMemoryEventBus, close_event_bus, current_event_bus, init_event_bus
from tests.event_bus_contract import (
    check_channel_isolation,
    check_delivery,
    check_fanout,
    check_no_replay,
    check_publish_without_subscribers,
    check_unsubscribe_on_cancel,
    check_unsubscribe_on_exit,
)


@pytest_asyncio.fixture
async def bus() -> AsyncGenerator[InMemoryEventBus, None]:
    b = InMemoryEventBus()
    yield b
    await b.close()


@pytest_asyncio.fixture
async def reset_event_bus() -> AsyncGenerator[None, None]:
    yield
    await close_event_bus()


@pytest.fixture
def active_channels(bus) -> Callable[[], Awaitable[list[str]]]:
    async def _active() -> list[str]:
        return list(bus._subscribers)
    return _active


@pytest.mark.asyncio
async def test_delivery(bus):
    await check_delivery(bus)


@pytest.mark.asyncio
async def test_fanout(bus):
    await check_fanout(bus)


@pytest.mark.asyncio
async def test_channel_isolation(bus):
    await check_channel_isolation(bus)


@pytest.mark.asyncio
async def test_no_replay(bus):
    await check_no_replay(bus)


@pytest.mark.asyncio
async def test_publish_without_subscribers(bus, active_channels):
    await check_publish_without_subscribers(bus, active_channels)


@pytest.mark.asyncio
async def test_unsubscribe_on_exit(bus, active_channels):
    await check_unsubscribe_on_exit(bus, active_channels)


@pytest.mark.asyncio
async def test_unsubscribe_on_cancel(bus, active_channels):
    await check_unsubscribe_on_cancel(bus, active_channels)


@pytest.mark.asyncio
@pytest.mark.usefixtures("reset_event_bus")
async def test_uninitialized_event_bus():
    with pytest.raises(RuntimeError):
        current_event_bus()


@pytest.mark.asyncio
@pytest.mark.usefixtures("reset_event_bus")
async def test_initialized_event_bus_success(bus):
    init_event_bus(bus)
    assert current_event_bus() is bus


@pytest.mark.asyncio
@pytest.mark.usefixtures("reset_event_bus")
async def test_closed_event_bus(bus):
    init_event_bus(bus)
    await close_event_bus()
    with pytest.raises(RuntimeError):
        current_event_bus()
