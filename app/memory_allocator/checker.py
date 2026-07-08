import asyncio
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from app.memory_allocator.models import TestCase


class CheckerOutput(BaseModel):
    """Доменная модель чекера"""
    valid: bool = Field(..., description="If test is valid")
    schema_valid: bool = Field(..., description="If test files are compatible with schema")
    errors: list = Field(default_factory=list, description="Validation errors")


class Checker(ABC):
    version: str

    @abstractmethod
    async def check(self, test: TestCase) -> CheckerOutput: ...


class MockChecker(Checker):
    version = "mock-1.0"

    def __init__(self, sleep_seconds: float = 5.0):
        self.sleep_seconds = sleep_seconds

    async def check(self, test: TestCase) -> CheckerOutput:
        await asyncio.sleep(self.sleep_seconds)
        return CheckerOutput(valid=True, schema_valid=True, errors=[])


def get_checker() -> Checker:
    return MockChecker(sleep_seconds=5)
