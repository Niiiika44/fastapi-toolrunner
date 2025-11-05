from fastapi import APIRouter
from app.api.routes.upload import router as upload_router
from app.api.routes.process import router as process_router

router = APIRouter()
router.include_router(upload_router)
router.include_router(process_router)
