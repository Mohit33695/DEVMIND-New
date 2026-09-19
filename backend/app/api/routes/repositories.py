"""
Repository Upload & Validation API Routes.

Purpose:
Handles repository ZIP file uploads sent from the frontend Add Repository interface.
Validates file format, structure, and size constraints without executing code or persisting data.
"""

import zipfile
from typing import Optional
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from app.schemas.dependencies import RepositoryDependenciesResponse
from app.schemas.documentation import RepositoryDocumentationResponse
from app.schemas.quality import RepositoryQualityResponse
from app.schemas.scanner import RepositoryFileContentResponse, RepositoryScanResult
from app.schemas.search import RepositorySearchResponse
from app.schemas.symbols import RepositorySymbolsResponse
from app.services.dependency import CodeDependencyService
from app.services.documentation import RepositoryDocumentationService
from app.services.parser.service import CodeIntelligenceService
from app.services.quality import CodeQualityService
from app.services.scanner import RepositoryScanner
from app.services.search import CodeSearchService
from app.services.storage import (
    BinaryFileError,
    FileTooLargeError,
    RepositoryFileNotFoundError,
    RepositoryNotFoundError,
    RepositoryStorageService,
    ZipPathTraversalError,
)

router = APIRouter()

# 200 MB maximum upload limit (in bytes)
MAX_UPLOAD_SIZE_BYTES = 200 * 1024 * 1024


class RepositoryUploadResponse(BaseModel):
    filename: str
    size: int
    status: str
    message: str
    repo_id: Optional[str] = None
    scan_result: Optional[RepositoryScanResult] = None


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
    4. Safe zip extraction & repository storage without executing code
    5. Repository metadata scan

    Returns metadata, repo_id, and scan result summary.
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

    # 4. Safely store repository archive in managed storage
    try:
        repo_id, dest_dir = RepositoryStorageService.store_repository_zip(file.file)
        scan_result = RepositoryScanner.scan_extracted_directory(dest_dir)
    except ZipPathTraversalError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process and store repository archive: {str(exc)}",
        )

    return RepositoryUploadResponse(
        filename=filename,
        size=file_size,
        status="validated",
        message="Repository archive successfully uploaded, stored, and scanned.",
        repo_id=repo_id,
        scan_result=scan_result,
    )


@router.get(
    "/repositories/{repo_id}/files/content",
    response_model=RepositoryFileContentResponse,
    status_code=status.HTTP_200_OK,
)
async def get_repository_file_content(
    repo_id: str,
    path: str = Query(..., description="Relative file path within repository"),
) -> RepositoryFileContentResponse:
    """
    GET /api/repositories/{repo_id}/files/content?path=<relative-path>

    Retrieves text content for a file in a stored repository.
    Validates:
    1. Repository exists (404)
    2. File path exists inside repository (404)
    3. Path boundary safety / Zip Slip protection (400)
    4. Maximum file size cap of 2 MB (413)
    5. Text / UTF-8 encoding validation (400)

    Returns file metadata and text content without executing code.
    """
    try:
        return RepositoryStorageService.read_repository_file_content(repo_id, path)
    except RepositoryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except RepositoryFileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ZipPathTraversalError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except BinaryFileError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except FileTooLargeError as e:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading repository file content: {str(exc)}",
        )


@router.get(
    "/repositories/{repo_id}/symbols",
    response_model=RepositorySymbolsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_repository_symbols(repo_id: str) -> RepositorySymbolsResponse:
    """
    GET /api/repositories/{repo_id}/symbols

    Statically inspects stored repository Python (.py) files and extracts code symbols
    (functions, async functions, classes, methods, and imports) without executing code.

    Returns symbol metadata grouped by file.
    """
    try:
        return CodeIntelligenceService.extract_repository_symbols(repo_id)
    except RepositoryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting repository symbols: {str(exc)}",
        )


@router.get(
    "/repositories/{repo_id}/search",
    response_model=RepositorySearchResponse,
    status_code=status.HTTP_200_OK,
)
async def search_repository_code(
    repo_id: str,
    q: str = Query(..., min_length=1, description="Search query string"),
    case_sensitive: bool = Query(False, description="Case-sensitive search flag"),
    max_results: int = Query(100, ge=1, le=500, description="Maximum number of search results to return"),
    file_extension: Optional[str] = Query(None, description="Optional file extension filter"),
) -> RepositorySearchResponse:
    """
    GET /api/repositories/{repo_id}/search?q=<query>&case_sensitive=false&max_results=100&file_extension=.py

    Searches text files in a stored repository for lines matching the query string.
    """
    try:
        return CodeSearchService.search_repository(
            repo_id=repo_id,
            query=q,
            case_sensitive=case_sensitive,
            max_results=max_results,
            file_extension=file_extension,
        )
    except RepositoryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except (ValueError, ZipPathTraversalError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching repository code: {str(exc)}",
        )


@router.get(
    "/repositories/{repo_id}/dependencies",
    response_model=RepositoryDependenciesResponse,
    status_code=status.HTTP_200_OK,
)
async def get_repository_dependencies(repo_id: str) -> RepositoryDependenciesResponse:
    """
    GET /api/repositories/{repo_id}/dependencies

    Statically analyzes module dependencies across repository source files.
    Determines internal, external, and unresolved relationships, and detects circular cycles.
    """
    try:
        return CodeDependencyService.analyze_repository_dependencies(repo_id)
    except RepositoryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing repository dependencies: {str(exc)}",
        )


@router.get(
    "/repositories/{repo_id}/documentation",
    response_model=RepositoryDocumentationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_repository_documentation(repo_id: str) -> RepositoryDocumentationResponse:
    """
    GET /api/repositories/{repo_id}/documentation

    Aggregates repository scan data, symbol metadata, docstrings, dependency relationships,
    and README content into a deterministic repository documentation object.
    """
    try:
        return RepositoryDocumentationService.generate_documentation(repo_id)
    except RepositoryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating repository documentation: {str(exc)}",
        )


@router.get(
    "/repositories/{repo_id}/quality",
    response_model=RepositoryQualityResponse,
    status_code=status.HTTP_200_OK,
)
async def get_repository_quality(repo_id: str) -> RepositoryQualityResponse:
    """
    GET /api/repositories/{repo_id}/quality

    Statically evaluates codebase quality rules and metrics (long functions, excessive parameters,
    large classes, long files, missing docstrings, circular dependencies, unresolved imports).
    """
    try:
        return CodeQualityService.analyze_repository_quality(repo_id)
    except RepositoryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing repository quality: {str(exc)}",
        )


