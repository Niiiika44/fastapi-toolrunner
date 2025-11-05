from fastapi import APIRouter
from app.api.routes.yaml_upload import router as yaml_router
from app.api.routes.process import router as process_router

router = APIRouter()
router.include_router(yaml_router)
router.include_router(process_router)
