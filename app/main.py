from fastapi import FastAPI
from app.api.routes import router as api_router
from app.core.logging_config import setup_logging


setup_logging()

app = FastAPI(title="Corporate Integration App")

app.include_router(api_router)

@app.get("/health")
async def root():
    return {"message": "App is running!"}
