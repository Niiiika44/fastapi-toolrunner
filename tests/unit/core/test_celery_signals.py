import uuid

import pytest

from app.core.celery_signals import (
    _adopt_request_id,
    _clear_request_id,
    _inject_request_id,
)
from app.core.context import NO_REQUEST_ID, request_id_var


class FakeTask:
    def __init__(self, headers: dict):
        self.request = headers


@pytest.fixture(autouse=True)
def isolated_request_id():
    token = request_id_var.set(NO_REQUEST_ID)
    yield
    request_id_var.reset(token)


def test_publish_outside_request_does_not_send_placeholder():
    headers = {}

    _inject_request_id(headers=headers)

    assert headers == {}


def test_publish_inside_request_sends_real_id():
    request_id_var.set("abc-123")
    headers = {}

    _inject_request_id(headers=headers)

    assert headers == {"request_id": "abc-123"}


def test_task_without_header_gets_fresh_id():
    _adopt_request_id(task=FakeTask({}))

    adopted = request_id_var.get()
    assert adopted != NO_REQUEST_ID
    assert uuid.UUID(adopted)


def test_task_adopts_incoming_id():
    _adopt_request_id(task=FakeTask({"request_id": "abc-123"}))

    assert request_id_var.get() == "abc-123"


def test_task_generated_id_is_inherited_by_published_children():
    _adopt_request_id(task=FakeTask({}))
    generated = request_id_var.get()

    child_headers = {}
    _inject_request_id(headers=child_headers)

    assert child_headers == {"request_id": generated}


def test_postrun_clears_request_id():
    request_id_var.set("abc-123")

    _clear_request_id()

    assert request_id_var.get() == NO_REQUEST_ID
