"""Background job processor for handling CV uploads and running pipeline."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from ...config import AppConfig, load_config
from ...cv_parser import parse_cv_to_profile, read_cv
from ...deduplicator import Deduplicator
from ...enricher import enrich_jobs
from ...llm_client import LLMClient
from ...main import JobPool, _collect_jobs
from ...models import CandidateProfile, RawJob, ScoredJob
from ...outputs.excel_manager import write_excel
from ...outputs.chinese_excel_manager import write_chinese_excel
from ...query_builder import build_queries
from ...scorer import score_jobs
from .user_manager import UserManager

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


class JobProcessor:
    """Process uploaded CVs and run the full job search pipeline."""

    def __init__(self, config: AppConfig):
        """
        Initialize job processor.

        Args:
            config: Application configuration
        """
        self.config = config
        self.user_manager = UserManager(config.resolve_path(config.web.upload_dir))
        self.cache_dir = config.resolve_path(config.runtime.cache_dir)

    async def process_upload(self, user_id: str, job_id: str, cv_path: Path) -> None:
        """
        Process an uploaded CV through the full pipeline.

        Steps:
        1. Parse CV to profile
        2. Build queries
        3. Search all enabled sources
        4. Deduplicate jobs
        5. Score jobs (LLM)
        6. Generate English Excel
        7. Generate Chinese Excel
        8. Update status to completed
        """
        try:
            llm = LLMClient(self.config.llm.text)

            self.user_manager.update_job_status(
                job_id=job_id,
                status="processing",
                progress=10,
                current_step="Parsing CV",
            )

            profile = parse_cv_to_profile(read_cv(cv_path), llm, cache_dir=self.cache_dir)

            self.user_manager.update_job_status(
                job_id=job_id,
                status="processing",
                progress=30,
                current_step="Building search queries",
            )

            queries = build_queries(profile, self.config)

            self.user_manager.update_job_status(
                job_id=job_id,
                status="processing",
                progress=50,
                current_step="Searching job platforms",
            )

            raw_jobs = _collect_jobs(queries, self.config)

            if not raw_jobs:
                raise ValueError("No jobs found from any platform")

            self.user_manager.update_job_status(
                job_id=job_id,
                status="processing",
                progress=60,
                current_step="Deduplicating jobs",
            )

            dedup = Deduplicator()
            unique_jobs = dedup.deduplicate(raw_jobs)

            self.user_manager.update_job_status(
                job_id=job_id,
                status="processing",
                progress=70,
                current_step="Enriching job data",
            )

            enriched = enrich_jobs(unique_jobs)

            self.user_manager.update_job_status(
                job_id=job_id,
                status="processing",
                progress=80,
                current_step="Scoring jobs with LLM",
            )

            async def _checkpoint(scored_so_far: list[ScoredJob]) -> None:
                self.user_manager.save_job_results(job_id, scored_so_far, {})

            newly_scored = await score_jobs(
                enriched,
                profile,
                read_cv(cv_path),
                llm,
                batch_size=self.config.scoring.batch_size,
                on_batch_done=_checkpoint,
            )
            self.user_manager.save_job_results(
                job_id,
                newly_scored,
                {
                    "total_jobs": len(unique_jobs),
                    "scored_jobs": len(newly_scored),
                    "english_excel": "jobs_pipeline.xlsx",
                    "chinese_excel": "jobs_pipeline_cn.xlsx",
                },
            )

            # Get user directory for Excel output
            job_info = self.user_manager.get_job_status(job_id)
            user_id = job_info.get("user_id")
            user_dir = self.user_manager.get_user_folder(user_id)

            # Generate English Excel
            english_excel_path = user_dir / "jobs_pipeline.xlsx"
            write_excel(newly_scored, english_excel_path)

            # Generate Chinese Excel
            from ..translators.job_translator import JobTranslator
            translator = JobTranslator(self.config)
            chinese_excel_path = user_dir / "jobs_pipeline_cn.xlsx"
            write_chinese_excel(newly_scored, translator, chinese_excel_path)

            # Update job status
            self.user_manager.update_job_status(
                job_id=job_id,
                status="completed",
                progress=100,
                current_step="completed",
            )

            logger.info(f"Job {job_id} completed successfully: {len(newly_scored)} jobs scored")

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            self.user_manager.update_job_status(
                job_id=job_id,
                status="failed",
                progress=0,
                current_step="failed",
                error=str(e),
            )

    async def shutdown(self) -> None:
        """Cleanup resources on shutdown."""
        logger.info("JobProcessor shutdown complete")

    def save_job_results(self, job_id: str, scored_jobs: list[ScoredJob], summary: dict) -> None:
        """
        Save job results to user folder.

        This includes:
        - Generating English Excel
        - Generating Chinese Excel (if implemented)
        - Saving results JSON
        """
        from ..outputs.excel_manager import write_excel

        # Get user directory
        job_info = self.user_manager.get_job_status(job_id)
        user_id = job_info.get("user_id")
        user_dir = self.user_manager.get_user_folder(user_id)

        # Generate English Excel
        english_excel_path = user_dir / "jobs_pipeline.xlsx"
        write_excel(scored_jobs, english_excel_path)

        # Generate Chinese Excel
        translator = JobTranslator(self.config)
        chinese_excel_path = user_dir / "jobs_pipeline_cn.xlsx"
        write_chinese_excel(scored_jobs, translator, chinese_excel_path)

        logger.info(f"Results saved for job {job_id} in {user_dir}")
