import logging.config

from app.core.config import settings
from app.core.context import request_id_var


class ContextFilter(logging.Filter):
    def filter(self, record):
        record.environment = settings.ENVIRONMENT
        record.request_id = request_id_var.get()
        return True


IS_DEV = settings.ENVIRONMENT == "dev"

if IS_DEV:
    LOG_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "context": {"()": "app.core.logging_config.ContextFilter"}
        },
        "formatters": {
            "text": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s | "
                "%(message)s | %(request_id)s"
            }
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "text",
                "filters": ["context"],
                "stream": "ext://sys.stdout"
            }
        },
        "root": {"handlers": ["default"], "level": "INFO"}
    }
else:
    LOG_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "context": {"()": "app.core.logging_config.ContextFilter"}
        },
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(environment)s %(levelname)s "
                "%(name)s %(funcName)s %(message)s %(processName)s %(request_id)s"
            }
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "filters": ["context"],
                "stream": "ext://sys.stdout"
            }
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False}
        },
        "root": {"handlers": ["default"], "level": "INFO"}
    }


def setup_logging():
    logging.config.dictConfig(LOG_CONFIG)
