"""
Repository Upload & Validation API Routes.

Purpose:
Handles repository ZIP file uploads sent from the frontend Add Repository interface.
Validates file format, structure, and size constraints without executing code or persisting data.
"""

import zipfile
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

router = APIRouter()

# 200 MB maximum upload limit (in bytes)
MAX_UPLOAD_SIZE_BYTES = 200 * 1024 * 1024


class RepositoryUploadResponse(BaseModel):
    filename: str
    size: int
    status: str
    message: str


@router.post(
    "/repositories/upload",
    response_model=RepositoryUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_repository_zip(
    file: UploadFile = File(..., description="Compressed repository .zip archive file")
) -> RepositoryUploadResponse:
    """
    POST /api/repositories/upload

    Accepts a ZIP file via multipart/form-data upload.
    Validates:
    1. File extension is .zip
    2. File size does not exceed 200 MB
    3. Valid ZIP header structure via zipfile inspection

    Returns metadata and validation status without executing or persisting files.
    """
    filename = file.filename or "archive.zip"

    # 1. Validate file extension
    if not filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only compressed .zip repository archives are supported.",
        )

    # 2. Inspect file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if file_size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of 200 MB.",
        )

    # 3. Validate ZIP archive structure safely
    try:
        if not zipfile.is_zipfile(file.file):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is not a valid or uncorrupted .zip archive.",
            )
        file.file.seek(0)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to read or parse the uploaded .zip archive.",
        )

    return RepositoryUploadResponse(
        filename=filename,
        size=file_size,
        status="validated",
        message="Repository archive successfully uploaded and validated by the backend server.",
    )
