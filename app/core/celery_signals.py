import uuid

from celery.signals import before_task_publish, setup_logging, task_postrun, task_prerun

from app.core.context import request_id_var


@setup_logging.connect
def _configure_logging(**kwargs):
    from app.core.logging_config import setup_logging as app_setup_logging
    app_setup_logging()


@before_task_publish.connect
def _inject_request_id(headers=None, **kwargs):
    rid = request_id_var.get()
    if rid and headers is not None:
        headers["request_id"] = rid


@task_prerun.connect
def _adopt_request_id(task=None, **kwargs):
    rid = task.request.get("request_id") if task else None
    request_id_var.set(rid or str(uuid.uuid4()))


@task_postrun.connect
def _clear_request_id(**kwargs):
    request_id_var.set("-")
