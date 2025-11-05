from fastapi import APIRouter, UploadFile, File
import yaml
# from app.core.processor import MockTool


router = APIRouter(prefix="/process", tags=['Process'])


@router.post("/")
async def upload_yaml(file: UploadFile = File(...)):
    contents = await file.read()
    data = yaml.load(contents, Loader=yaml.SafeLoader)
    # tool = MockTool()
    # result = tool.run(data)
    result = "result"
    return {"input": data, "output": result}