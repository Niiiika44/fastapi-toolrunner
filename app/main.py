from fastapi import FastAPI
from app.auth.routes import router as auth_router
from app.memory_allocator.routes import router as alloc_router
from app.core.config import settings
from app.core.logging_config import setup_logging


setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG
)

app.include_router(auth_router)
app.include_router(alloc_router)


@app.get("/health")
async def health_check():
    return {"message": "App is running!"}
