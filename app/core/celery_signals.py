import uuid

from celery.signals import (
    before_task_publish,
    celeryd_init,
    setup_logging,
    task_postrun,
    task_prerun,
)
from kombu import Exchange, Queue

from app.core.context import NO_REQUEST_ID, request_id_var


@setup_logging.connect
def _configure_logging(**kwargs):
    from app.core.logging_config import setup_logging as app_setup_logging
    app_setup_logging()


@before_task_publish.connect
def _inject_request_id(headers=None, **kwargs):
    rid = request_id_var.get()
    if rid and rid != NO_REQUEST_ID and headers is not None:
        headers["request_id"] = rid


@task_prerun.connect
def _adopt_request_id(task=None, **kwargs):
    rid = task.request.get("request_id") if task else None
    request_id_var.set(rid or str(uuid.uuid4()))


@task_postrun.connect
def _clear_request_id(**kwargs):
    request_id_var.set(NO_REQUEST_ID)


@celeryd_init.connect
def _declare_dead_letter_queue(**kwargs):
    from app.core.celery_app import (
        DEAD_LETTER_EXCHANGE,
        DEAD_LETTER_QUEUE,
        DEAD_LETTER_ROUTING_KEY,
        celery_app,
    )
    with celery_app.connection_for_write() as conn:
        Queue(
            DEAD_LETTER_QUEUE,
            Exchange(DEAD_LETTER_EXCHANGE, type="direct"),
            routing_key=DEAD_LETTER_ROUTING_KEY,
            durable=True,
        ).declare(channel=conn.default_channel)
