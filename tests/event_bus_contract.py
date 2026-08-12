import asyncio
import contextlib
from collections.abc import Awaitable, Callable

import pytest

from app.core.events import EventBus

TIMEOUT = 3
SILENCE_TIMEOUT = 0.5
ActiveChannels = Callable[[], Awaitable[list[str]]]


async def check_delivery(bus: EventBus) -> None:
    async with bus.subscribe("test:1") as stream:
        await bus.publish("test:1", "payload")
        message = await asyncio.wait_for(anext(stream), TIMEOUT)
    assert message == "payload"
    assert isinstance(message, str)


async def check_fanout(bus: EventBus) -> None:
    channel = "test:1"
    async with bus.subscribe(channel) as stream_1, bus.subscribe(channel) as stream_2:
        await bus.publish(channel, "payload")
        message_1 = await asyncio.wait_for(anext(stream_1), TIMEOUT)
        message_2 = await asyncio.wait_for(anext(stream_2), TIMEOUT)
    assert message_1 == message_2 == "payload"


async def check_channel_isolation(bus: EventBus) -> None:
    async with bus.subscribe("test:1") as stream_1, bus.subscribe("test:2") as stream_2:
        await bus.publish("test:2", "payload")
        message = await asyncio.wait_for(anext(stream_2), TIMEOUT)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(anext(stream_1), SILENCE_TIMEOUT)
    assert message == "payload"
    assert isinstance(message, str)


async def check_no_replay(bus: EventBus) -> None:
    await bus.publish("test:1", "payload")
    async with bus.subscribe("test:1") as stream:
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(anext(stream), SILENCE_TIMEOUT)


async def check_publish_without_subscribers(
    bus: EventBus,
    active: ActiveChannels
) -> None:
    await bus.publish("test:1", "payload")
    assert await active() == []


async def check_unsubscribe_on_exit(
    bus: EventBus,
    active: ActiveChannels
) -> None:
    async with bus.subscribe("test:1"):
        assert await active() == ["test:1"]
    assert await active() == []


async def _wait_subscribe(bus: EventBus, event: asyncio.Event) -> None:
    async with bus.subscribe("test:1") as stream:
        event.set()
        async for _ in stream:
            pass


async def check_unsubscribe_on_cancel(
    bus: EventBus,
    active: ActiveChannels
) -> None:
    event = asyncio.Event()
    task = asyncio.create_task(_wait_subscribe(bus, event))
    await event.wait()
    assert await active() == ["test:1"]
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.wait_for(task, TIMEOUT)
    assert await active() == []
