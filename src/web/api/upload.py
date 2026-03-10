"""API endpoints for CV upload."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from ...config import AppConfig, load_config
from ..services.user_manager import UserManager
from ..services.job_processor import JobProcessor

router = APIRouter(tags=["Upload"])
logger = logging.getLogger(__name__)


class UploadResponse(BaseModel):
    """Response model for CV upload."""

    job_id: str = Field(..., description="Unique job identifier for status polling")
    status: str = Field(..., description="Current status of the job")
    message: str = Field(..., description="Human-readable message")


class ValidationError(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")


@field_validator("user_id")
@classmethod
def validate_user_id(cls, v: str) -> str:
    """Validate and sanitize user ID."""
    if not v or not v.strip():
        raise ValueError("User ID cannot be empty")
    # Prevent path traversal
    if ".." in v or v.startswith("/") or v.startswith("\\"):
        raise ValueError("Invalid user ID")
    return v.strip()


@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={
        200: {"model": UploadResponse},
        400: {"model": ValidationError},
        413: {"model": ValidationError},
    },
)
async def upload_cv(
    file: UploadFile = File(
        ...,
        description="Markdown CV file",
        max_size=10 * 1024 * 1024,  # 10MB
    ),
    user_id: str = Form(..., description="User identifier (email or username)"),
    config: AppConfig = Depends(load_config),
) -> UploadResponse:
    """
    Upload CV file and trigger processing.

    Validates:
    - File is markdown format
    - File size <= 10MB
    - User ID is valid

    Process:
    1. Save CV to user folder
    2. Create job record
    3. Trigger background processing
    4. Return job ID for status polling
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith((".md", ".markdown")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .md and .markdown files are supported",
        )

    # Get job processor (initialized in app.py)
    from ..app import job_processor

    if not job_processor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Job processor not initialized",
        )

    user_manager = UserManager(config.resolve_path(config.web.upload_dir))

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    try:
        # Create user directory if needed
        user_dir = user_manager.ensure_user_folder(user_id)

        # Save CV file
        cv_path = user_dir / "cv.md"
        content = await file.read()
        cv_path.write_text(content, encoding="utf-8")

        # Create job status record
        user_manager.create_job_record(user_id, job_id, filename=file.filename)

        # Trigger background processing
        asyncio.create_task(job_processor.process_upload(user_id, job_id, cv_path))

        logger.info(
            f"CV uploaded successfully: user={user_id}, job_id={job_id}, file={file.filename}"
        )

        return UploadResponse(
            job_id=job_id,
            status="processing",
            message="CV uploaded successfully. Processing has started.",
        )

    except Exception as e:
        logger.error(f"CV upload failed for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload CV: {str(e)}",
        )
