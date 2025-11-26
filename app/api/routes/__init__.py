from fastapi import APIRouter
from app.api.routes.upload import router as upload_router

router = APIRouter()
router.include_router(upload_router)
