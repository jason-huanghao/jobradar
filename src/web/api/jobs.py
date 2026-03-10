"""API endpoints for job results retrieval."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ...config import AppConfig, load_config
from ..services.user_manager import UserManager

router = APIRouter(tags=["Jobs"])
logger = logging.getLogger(__name__)


class JobResult(BaseModel):
    """Individual job result."""

    title: str
    title_cn: Optional[str] = None
    company: str
    location: str
    source: str
    score: float
    url: str


class JobResultsResponse(BaseModel):
    """Response model for job results."""

    job_id: str
    status: str
    jobs: list[JobResult] = []
    summary: dict = {}


@router.get(
    "/jobs/{job_id}",
    response_model=JobResultsResponse,
    responses={
        200: {"model": JobResultsResponse},
        404: {"model": dict},
    },
)
async def get_job_results(
    job_id: str,
    config: AppConfig = Depends(load_config),
) -> JobResultsResponse:
    """
    Get processed job results.

    Returns:
    - List of scored jobs
    - Summary statistics
    - Links to Excel files (if available)
    """
    user_manager = UserManager(config.resolve_path(config.web.upload_dir))

    try:
        # Get job info
        job_info = user_manager.get_job_status(job_id)

        if not job_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )

        if job_info["status"] != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job {job_id} is still {job_info['status']}",
            )

        # Get results
        results = user_manager.get_job_results(job_id)

        logger.info(f"Results retrieved for job {job_id}: {len(results.get('jobs', []))} jobs")

        return JobResultsResponse(
            job_id=job_id,
            status=job_info["status"],
            jobs=results.get("jobs", []),
            summary=results.get("summary", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get results for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve job results: {str(e)}",
        )


@router.get(
    "/download/{job_id}/{filename}",
    responses={
        200: {"description": "Excel file download"},
        404: {"model": dict},
    },
)
async def download_excel(
    job_id: str,
    filename: str,
    config: AppConfig = Depends(load_config),
):
    """
    Download generated Excel file.

    Supported filenames:
    - jobs_pipeline.xlsx (English version)
    - jobs_pipeline_cn.xlsx (Chinese version)
    """
    user_manager = UserManager(config.resolve_path(config.web.upload_dir))

    try:
        # Get job info
        job_info = user_manager.get_job_status(job_id)

        if not job_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )

        if job_info["status"] != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job {job_id} is still {job_info['status']}",
            )

        # Get user ID from job info
        user_id = job_info.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User ID not found in job record",
            )

        # Validate filename
        allowed_files = ["jobs_pipeline.xlsx", "jobs_pipeline_cn.xlsx"]
        if filename not in allowed_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid filename. Allowed: {', '.join(allowed_files)}",
            )

        # Construct file path
        user_dir = user_manager.get_user_folder(user_id)
        file_path = user_dir / filename

        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File {filename} not found",
            )

        logger.info(f"File download requested: job_id={job_id}, file={filename}")

        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}",
        )
