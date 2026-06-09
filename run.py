import uvicorn

from app.core.config import settings
from app.core.logging_config import LOG_CONFIG

if __name__ == "__main__":
    run_kwargs = {
        "host": "0.0.0.0",
        "port": 8000,
        "reload": settings.DEBUG
    }
    if settings.ENVIRONMENT != "dev":
        run_kwargs["log_config"] = LOG_CONFIG
    uvicorn.run("app.main:app", **run_kwargs)
