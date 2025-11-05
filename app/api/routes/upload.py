from fastapi import APIRouter, UploadFile, File, HTTPException
from app.core.parser import parse_yaml, parse_json
from app.core.file_utils import detect_file_type
from app.core.base_classes import InputType
from app.core.thread_utils import run_in_thread


router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/")
async def upload(file: UploadFile = File(...)):
    """
    Upload a YAML or JSON file and parse it.
    Returns parsed data as JSON.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    decoded_content = content.decode("utf-8")
    filetype = detect_file_type(file.filename)

    match filetype:
        case InputType.YAML:
            data = await run_in_thread(parse_yaml, decoded_content)
        case InputType.JSON:
            data = await run_in_thread(parse_json, decoded_content)
        case _:
            raise HTTPException(status_code=400, detail="Unsupported file type")

    return {"data": data}
