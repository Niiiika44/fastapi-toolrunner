from fastapi import APIRouter, UploadFile, File
import yaml


router = APIRouter(prefix="/yaml", tags=["YAML"])

@router.post("/upload/")
async def upload_yaml(file: UploadFile = File(...)):
    contents = await file.read()
    data = yaml.load(contents, Loader=yaml.SafeLoader)
    return {"data": data}
