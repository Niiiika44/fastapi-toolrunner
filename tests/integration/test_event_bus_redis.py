from collections.abc import AsyncGenerator, Awaitable, Callable, Generator

import pytest
import pytest_asyncio
from redis.asyncio import Redis
from testcontainers.redis import RedisContainer

from app.core.events import RedisEventBus
from tests.event_bus_contract import (
    check_channel_isolation,
    check_delivery,
    check_fanout,
    check_no_replay,
    check_publish_without_subscribers,
    check_unsubscribe_on_cancel,
    check_unsubscribe_on_exit,
)


@pytest.fixture(scope="session")
def redis_url() -> Generator[str, None, None]:
    with RedisContainer("redis:7-alpine") as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(6379)
        yield f"redis://{host}:{port}/0"


@pytest_asyncio.fixture
async def bus(redis_url: str) -> AsyncGenerator[RedisEventBus, None]:
    client = Redis.from_url(redis_url, decode_responses=True)
    b = RedisEventBus(client)
    yield b
    await b.close()


@pytest.fixture
def active_channels(redis_url: str) -> Callable[[], Awaitable[list[str]]]:
    async def _active() -> list[str]:
        client = Redis.from_url(redis_url, decode_responses=True)
        try:
            return await client.pubsub_channels(pattern="test:*")
        finally:
            await client.aclose()
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
