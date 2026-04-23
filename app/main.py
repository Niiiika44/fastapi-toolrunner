from fastapi import FastAPI
from app.api.routes import router as api_router
from app.core.config import settings
from app.core.logging_config import setup_logging


setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG
)

app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {"message": "App is running!"}
