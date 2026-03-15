"""Pipeline orchestrator — single entry point for all pipeline runs."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Literal

from sqlmodel import Session, select

from .config import AppConfig
from .llm.client import LLMClient
from .models.job import RawJob, ScoredJob
from .profile.ingestor import ingest
from .scoring.generator.cover_letter import generate_cover_letter
from .scoring.generator.cv_optimizer import optimize_cv
from .scoring.hard_filter import apply as hard_filter
from .scoring.scorer import score_jobs
from .sources.query_builder import build_queries
from .sources.registry import build_registry
from .storage.db import get_session, init_db
from .storage.models import ApplicationRecord, Job, PipelineRun, ScoredJobRecord
from .utils import profile_id as _profile_id

logger = logging.getLogger(__name__)
Mode = Literal["full", "quick", "score-only", "dry-run"]


@dataclass
class PipelineProgress:
    event: str
    data: dict = field(default_factory=dict)


@dataclass
class PipelineResult:
    run_id: int
    jobs_fetched: int
    jobs_new: int
    jobs_scored: int
    jobs_generated: int
    top_jobs: list[ScoredJob]
    status: str
    error: str = ""


class JobRadarPipeline:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.llm = LLMClient(config.llm.text)
        db_path = config.resolve_path(config.server.db_path)
        init_db(db_path)
        self._db_path = db_path
        self._registry = build_registry(config)

    def run(
        self,
        mode: Mode = "full",
        on_progress: Callable[[PipelineProgress], None] | None = None,
    ) -> PipelineResult:
        def emit(event: str, **data):
            if on_progress:
                on_progress(PipelineProgress(event=event, data=data))

        with next(get_session(self._db_path)) as session:
            run_record = PipelineRun(candidate_id="", mode=mode, started_at=datetime.utcnow())
            session.add(run_record)
            session.commit()
            session.refresh(run_record)
            run_id = run_record.id

            try:
                result = self._execute(mode, session, run_id, emit)
                run_record.status = "done"
                run_record.finished_at = datetime.utcnow()
                run_record.jobs_fetched = result.jobs_fetched
                run_record.jobs_new = result.jobs_new
                run_record.jobs_scored = result.jobs_scored
                run_record.jobs_generated = result.jobs_generated
                session.add(run_record)
                session.commit()
                emit("done", run_id=run_id,
                     jobs_fetched=result.jobs_fetched,
                     jobs_scored=result.jobs_scored,
                     jobs_generated=result.jobs_generated)
                return result
            except Exception as exc:
                logger.exception("Pipeline run %d failed", run_id)
                run_record.status = "failed"
                run_record.error = str(exc)
                run_record.finished_at = datetime.utcnow()
                session.add(run_record)
                session.commit()
                emit("error", message=str(exc))
                return PipelineResult(
                    run_id=run_id, jobs_fetched=0, jobs_new=0,
                    jobs_scored=0, jobs_generated=0, top_jobs=[],
                    status="failed", error=str(exc),
                )

    def _execute(self, mode: Mode, session: Session, run_id: int, emit: Callable) -> PipelineResult:
        cfg = self.config

        # dry-run: validate config + DB only — no LLM, no network
        if mode == "dry-run":
            emit("queries_built", count=0)
            return PipelineResult(run_id=run_id, jobs_fetched=0, jobs_new=0,
                                  jobs_scored=0, jobs_generated=0, top_jobs=[], status="done")

        # Step 1: Parse CV → profile
        cache_dir = cfg.resolve_path(cfg.server.cache_dir)
        cv_source = cfg.candidate.cv_url or cfg.candidate.cv_path
        profile = ingest(str(cfg.resolve_path(cv_source)), self.llm, cache_dir=cache_dir)
        emit("profile_done", name=profile.personal.name)

        # Step 2: Build search queries
        # quick mode: cap both query count AND per-source results
        quick_limit = cfg.search.quick_max_results if hasattr(cfg.search, 'quick_max_results') else 5
        max_results_override = quick_limit if mode == "quick" else None
        queries = build_queries(profile, cfg, max_results_override=max_results_override)
        if mode == "quick":
            queries = queries[:20]
        emit("queries_built", count=len(queries))

        since = datetime.utcnow() - timedelta(days=cfg.search.max_days_old)

        # Step 3: Fetch from all sources
        raw_jobs = self._registry.fetch_all(
            queries, cfg, since,
            on_source_done=lambda sid, n: emit("source_done", source=sid, count=n),
        )
        emit("fetch_done", total=len(raw_jobs))

        # Step 4: Persist new jobs
        existing_ids = set(session.exec(select(Job.id)).all())
        new_jobs = [j for j in raw_jobs if j.id not in existing_ids]
        for j in new_jobs:
            session.add(Job(
                id=j.id, source=j.source, title=j.title, company=j.company,
                location=j.location, description=j.description, url=j.url,
                date_posted=j.date_posted, job_type=j.job_type, salary=j.salary,
                remote=j.remote, raw_extra=json.dumps(j.raw_extra),
            ))
        session.commit()
        emit("db_saved", new=len(new_jobs))

        # Step 5: Hard filter
        if mode != "score-only":
            to_score, dropped = hard_filter(new_jobs, cfg)
        else:
            to_score = [_db_to_raw(j) for j in session.exec(select(Job)).all()]
            dropped = 0
        emit("filter_done", kept=len(to_score), dropped=dropped)

        # Step 6: LLM scoring (skip already-scored jobs)
        cand_id = _profile_id(profile)
        scored_ids = set(session.exec(
            select(ScoredJobRecord.job_id).where(ScoredJobRecord.candidate_id == cand_id)
        ).all())
        unscored = [j for j in to_score if j.id not in scored_ids]
        emit("scoring_start", total=len(unscored))

        scored_jobs = score_jobs(
            unscored, profile, self.llm,
            batch_size=cfg.scoring.batch_size,
            on_batch_done=lambda s: emit("score_progress", scored=len(s)),
        )
        for sj in scored_jobs:
            session.add(ScoredJobRecord(
                job_id=sj.job.id, candidate_id=cand_id,
                overall=sj.score,
                skills_match=sj.breakdown.skills_match,
                seniority_fit=sj.breakdown.seniority_fit,
                location_fit=sj.breakdown.location_fit,
                language_fit=sj.breakdown.language_fit,
                visa_friendly=sj.breakdown.visa_friendly,
                growth_potential=sj.breakdown.growth_potential,
                reasoning=sj.reasoning,
                application_angle=sj.application_angle,
            ))
        session.commit()

        # Step 7: Generate docs for top matches
        top = [sj for sj in scored_jobs if sj.score >= cfg.scoring.min_score_application]
        generated = 0
        for sj in top[:5]:
            cv_md, gaps = optimize_cv(sj.job, profile, self.llm)
            cl_md = generate_cover_letter(sj, profile, self.llm)
            session.add(ApplicationRecord(
                job_id=sj.job.id, candidate_id=cand_id,
                cv_optimized_md=cv_md, cover_letter_md=cl_md, gaps=json.dumps(gaps),
            ))
            sj.cv_optimized_md = cv_md
            sj.cover_letter_md = cl_md
            generated += 1
        session.commit()
        emit("gen_done", generated=generated)

        return PipelineResult(
            run_id=run_id, jobs_fetched=len(raw_jobs), jobs_new=len(new_jobs),
            jobs_scored=len(scored_jobs), jobs_generated=generated,
            top_jobs=scored_jobs[:20], status="done",
        )


def _db_to_raw(j: Job) -> RawJob:
    return RawJob(
        id=j.id, title=j.title, company=j.company, location=j.location,
        url=j.url, description=j.description, source=j.source,
        date_posted=j.date_posted, job_type=j.job_type, salary=j.salary,
        remote=j.remote, raw_extra=json.loads(j.raw_extra or "{}"),
    )
