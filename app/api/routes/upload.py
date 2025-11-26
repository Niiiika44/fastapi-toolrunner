import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.parse_service import process_folder


router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/")
async def upload(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)) -> dict:
    """
    Upload and process a zip file containing test case data.

    :param file: Zip file to upload.
    :param db: Database session.
    :return: Dictionary with the ID and filename of the saved test case.
    """

    if not (file.filename and file.filename.endswith(".zip")):
        raise HTTPException(status_code=400, detail="Only zip files are allowed.")

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir, file.filename)
        with open(zip_path, "wb") as f:
            f.write(await file.read())

        extract_dir = Path(tmpdir, "extracted")
        extract_dir.mkdir()

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        module_ids = await process_folder(folder_path=extract_dir, db=db)
    return {"module_ids": module_ids, "filename": file.filename}
