import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from app.core.config import get_settings

settings = get_settings()


class EventBus(ABC):
    @abstractmethod
    async def publish(self, channel: str, payload: str) -> None: ...

    @abstractmethod
    def subscribe(self, channel: str) -> AbstractAsyncContextManager[AsyncIterator[str]]: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def ping(self) -> None: ...


class RedisEventBus(EventBus):
    def __init__(self, client: Redis):
        self._client = client

    async def publish(self, channel: str, payload: str) -> None:
        await self._client.publish(channel, payload)

    @asynccontextmanager
    async def subscribe(self, channel: str) -> AsyncIterator[AsyncIterator[str]]:
        pubsub = self._client.pubsub(ignore_subscribe_messages=True)
        await pubsub.subscribe(channel)
        try:
            yield self._messages(pubsub)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    async def _messages(self, pubsub: PubSub) -> AsyncIterator[str]:
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield message["data"]

    async def close(self) -> None:
        await self._client.aclose()

    async def ping(self) -> None:
        await self._client.ping()


class InMemoryEventBus(EventBus):
    def __init__(self):
        self._subscribers: dict[str, set[asyncio.Queue[str]]] = {}

    async def publish(self, channel: str, payload: str) -> None:
        for queue in list(self._subscribers.get(channel, ())):
            queue.put_nowait(payload)

    @asynccontextmanager
    async def subscribe(self, channel: str) -> AsyncIterator[AsyncIterator[str]]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._subscribers.setdefault(channel, set()).add(queue)
        try:
            yield self._messages(queue)
        finally:
            subscribers = self._subscribers.get(channel, set())
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop(channel, None)

    async def _messages(self, queue: asyncio.Queue[str]) -> AsyncIterator[str]:
        while True:
            yield await queue.get()

    async def close(self) -> None:
        self._subscribers.clear()

    async def ping(self) -> None:
        pass


class _EventBusHolder:
    bus: EventBus | None = None


_holder = _EventBusHolder()


def create_redis_event_bus() -> RedisEventBus:
    client = Redis.from_url(settings.REDIS_URL, decode_responses=True, health_check_interval=30)
    bus = RedisEventBus(client)
    return bus


def init_event_bus(bus: EventBus) -> None:
    _holder.bus = bus


async def close_event_bus() -> None:
    if _holder.bus is not None:
        await _holder.bus.close()
        _holder.bus = None


def current_event_bus() -> EventBus:
    if _holder.bus is None:
        raise RuntimeError("Event bus is not initialized")
    return _holder.bus


@asynccontextmanager
async def build_event_bus() -> AsyncIterator[EventBus]:
    bus = create_redis_event_bus()
    try:
        yield bus
    finally:
        await bus.close()
