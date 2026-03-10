"""API endpoints for job status checking."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ...config import AppConfig, load_config
from ..services.user_manager import UserManager

router = APIRouter(tags=["Status"])
logger = logging.getLogger(__name__)


class JobStatusResponse(BaseModel):
    """Response model for job status."""

    job_id: str
    status: str  # processing | completed | failed
    progress: int = 0  # 0-100
    current_step: str = ""
    error: Optional[str] = None
    results: Optional[dict] = None
    timestamp: str


@router.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
    responses={
        200: {"model": JobStatusResponse},
        404: {"model": dict},
    },
)
async def get_job_status(
    job_id: str,
    config: AppConfig = Depends(load_config),
) -> JobStatusResponse:
    """
    Get current status of a background job processing.

    Response includes:
    - Current status (processing/completed/failed)
    - Progress percentage (0-100)
    - Current processing step
    - Error details (if failed)
    - Results (if completed)
    """
    user_manager = UserManager(config.resolve_path(config.web.upload_dir))

    try:
        # Get job status
        job_info = user_manager.get_job_status(job_id)

        if not job_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )

        logger.info(f"Status requested for job {job_id}: {job_info['status']}")

        return JobStatusResponse(**job_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve job status: {str(e)}",
        )
