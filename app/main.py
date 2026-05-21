from fastapi import FastAPI
from app.auth.routes import router as auth_router
from app.memory_allocator.routes import router as alloc_router
from app.users.routes import router as users_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.error_handler import domain_error_handler
from app.core.exceptions import DomainError


setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG
)

app.add_exception_handler(DomainError, domain_error_handler)

app.include_router(auth_router)
app.include_router(alloc_router)
app.include_router(users_router)


@app.get("/health")
async def health_check():
    return {"message": "App is running!"}
