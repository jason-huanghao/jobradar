"""User and folder management service for multi-user CV upload system."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid

logger = logging.getLogger(__name__)


class UserManager:
    """Manage user folders and job records."""

    def __init__(self, upload_dir: Path):
        """
        Initialize user manager.

        Args:
            upload_dir: Base directory for user data
        """
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        # Jobs storage
        self.jobs_file = upload_dir / "jobs.json"
        self._load_jobs()

    def _load_jobs(self) -> None:
        """Load jobs from persistent storage."""
        if self.jobs_file.exists():
            try:
                self.jobs = json.loads(self.jobs_file.read_text(encoding="utf-8"))
                logger.info(f"Loaded {len(self.jobs)} job records")
            except Exception as e:
                logger.error(f"Failed to load jobs: {e}")
                self.jobs = {}
        else:
            self.jobs = {}

    def _save_jobs(self) -> None:
        """Save jobs to persistent storage."""
        try:
            self.jobs_file.write_text(
                json.dumps(self.jobs, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save jobs: {e}")

    def ensure_user_folder(self, user_id: str) -> Path:
        """
        Ensure user folder exists and return path.

        Args:
            user_id: Sanitized user identifier

        Returns:
            Path to user folder
        """
        # Sanitize user ID for filesystem safety
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in "._-@")
        user_dir = self.upload_dir / safe_user_id

        user_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (user_dir / "digests").mkdir(exist_ok=True)

        logger.info(f"Ensured user folder: {user_dir}")
        return user_dir

    def get_user_folder(self, user_id: str) -> Path:
        """
        Get user folder path.

        Args:
            user_id: Sanitized user identifier

        Returns:
            Path to user folder
        """
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in "._-@")
        user_dir = self.upload_dir / safe_user_id

        if not user_dir.exists():
            raise FileNotFoundError(f"User folder not found: {user_id}")

        return user_dir

    def create_job_record(self, user_id: str, job_id: str, filename: str) -> None:
        """
        Create a new job record.

        Args:
            user_id: User identifier
            job_id: Unique job identifier
            filename: Original CV filename
        """
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in "._-@")

        self.jobs[job_id] = {
            "user_id": safe_user_id,
            "status": "processing",
            "progress": 0,
            "current_step": "uploaded",
            "error": None,
            "results": None,
            "filename": filename,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self._save_jobs()

        logger.info(f"Created job record: job_id={job_id}, user_id={user_id}")

    def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: int,
        current_step: str,
        error: Optional[str] = None,
        results: Optional[dict] = None,
    ) -> None:
        """
        Update job processing status.

        Args:
            job_id: Job identifier
            status: Current status (processing/completed/failed)
            progress: Progress percentage (0-100)
            current_step: Current processing step description
            error: Error message if failed
            results: Job results if completed
        """
        if job_id not in self.jobs:
            logger.warning(f"Job {job_id} not found, cannot update status")
            return

        self.jobs[job_id].update(
            {
                "status": status,
                "progress": progress,
                "current_step": current_step,
                "error": error,
                "results": results,
                "updated_at": datetime.now().isoformat(),
            }
        )
        self._save_jobs()

        logger.info(f"Updated job status: job_id={job_id}, status={status}, progress={progress}%")

    def get_job_status(self, job_id: str) -> Optional[dict]:
        """
        Get job status.

        Args:
            job_id: Job identifier

        Returns:
            Job status dictionary or None if not found
        """
        return self.jobs.get(job_id)

    def get_job_results(self, job_id: str) -> Optional[dict]:
        """
        Get job results.

        Args:
            job_id: Job identifier

        Returns:
            Results dictionary with jobs and summary
        """
        job_info = self.jobs.get(job_id)

        if not job_info:
            return None

        if job_info["status"] != "completed":
            return None

        results = job_info.get("results", {})

        # Load results from user folder if not in memory
        if not results.get("jobs"):
            user_id = job_info.get("user_id")
            user_dir = self.get_user_folder(user_id)

            # Load results from file
            results_file = user_dir / "results.json"
            if results_file.exists():
                try:
                    results = json.loads(results_file.read_text(encoding="utf-8"))
                    # Update in-memory cache
                    self.jobs[job_id]["results"] = results
                    self._save_jobs()
                except Exception as e:
                    logger.error(f"Failed to load results: {e}")

        return results

    def save_job_results(self, job_id: str, jobs: list, summary: dict) -> None:
        """
        Save job results to user folder.

        Args:
            job_id: Job identifier
            jobs: List of job results
            summary: Summary statistics
        """
        job_info = self.jobs.get(job_id)

        if not job_info:
            logger.warning(f"Job {job_id} not found, cannot save results")
            return

        user_id = job_info.get("user_id")
        user_dir = self.get_user_folder(user_id)

        # Save results as JSON
        results = {
            "jobs": jobs,
            "summary": summary,
            "saved_at": datetime.now().isoformat(),
        }

        results_file = user_dir / "results.json"
        results_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

        # Update job status
        self.update_job_status(
            job_id=job_id,
            status="completed",
            progress=100,
            current_step="completed",
            results=results,
        )

        logger.info(f"Saved results for job {job_id}: {len(jobs)} jobs")

    def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Clean up old job records.

        Args:
            days: Delete jobs older than this many days

        Returns:
            Number of jobs deleted
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0

        for job_id, job_info in list(self.jobs.items()):
            created_at = job_info.get("created_at", "")
            try:
                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                if created_dt < cutoff:
                    del self.jobs[job_id]
                    deleted += 1
            except Exception:
                pass  # Skip if date parsing fails

        if deleted > 0:
            self._save_jobs()
            logger.info(f"Cleaned up {deleted} old job records")

        return deleted
