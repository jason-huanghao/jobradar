"""JobRadar — AI-powered job search agent.

Entry point for all CLI operations.

Usage:
  jobradar                        # full pipeline
  jobradar --update               # incremental: crawl + score new only
  jobradar --mode quick           # fast run (BA + Indeed only)
  jobradar --mode dry-run         # show queries, don't execute
  jobradar --setup                # interactive setup wizard
  jobradar --install-agent        # install daily 8am scheduler
  jobradar --uninstall-agent      # remove scheduler
  jobradar --show-digest          # print today's digest to terminal
  jobradar --generate-app COMPANY # generate cover letter for a company
  jobradar --mark-applied COMPANY # mark job as applied in Excel
  jobradar --explain COMPANY      # explain score for a job
  jobradar --feedback "AMD liked" # record preferences for future scoring
  jobradar --crawl-only           # crawl + merge into pool (no scoring)
  jobradar --score-only           # score unscored jobs + output
  jobradar --parse-cv-only        # CV → JSON only
  jobradar --rerun-scoring        # clear scores and re-score all
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from .agent_installer import install_agent, uninstall_agent
from .config import AppConfig, load_config
from .llm_env_probe import format_setup_guidance, probe_llm_env
from .cv_parser import parse_cv_to_profile, read_cv
from .deduplicator import Deduplicator
from .enricher import enrich_jobs
from .feedback import load_feedback_summary, record_feedback
from .llm_client import LLMClient
from .models import CandidateProfile, RawJob, ScoredJob, SearchQuery
from .notifications.email_notifier import EmailNotifier
from .outputs.application_gen import generate_application
from .outputs.digest_generator import generate_digest
from .outputs.excel_manager import write_excel
from .query_builder import build_queries
from .scorer import score_jobs
from .setup_wizard import run_setup
from .sources.arbeitsagentur import ArbeitsagenturSource
from .sources.bosszhipin import BossZhipinSource
from .sources.jobspy_adapter import JobSpySource
from .sources.lagou import LagouSource
from .sources.stepstone_scraper import StepStoneSource
from .sources.xing_adapter import XingSource
from .sources.zhilian import ZhilianSource

console = Console()

_ALL_SOURCES = [
    ArbeitsagenturSource(),
    JobSpySource(),
    StepStoneSource(),
    XingSource(),
    BossZhipinSource(),
    LagouSource(),
    ZhilianSource(),
]


# ── Logging ────────────────────────────────────────────────────────


def _setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


# ── Config discovery ───────────────────────────────────────────────


def find_config(cli_path: str | None = None) -> Path:
    candidates = [
        Path(cli_path) if cli_path else None,
        Path("config.yaml"),
        Path(__file__).parent.parent / "config.yaml",
        Path.home() / ".openclaw" / "jobradar" / "config.yaml",
    ]
    for p in candidates:
        if p and p.exists():
            return p
    raise FileNotFoundError(
        "config.yaml not found. Run 'jobradar --setup' to create one."
    )


# ═══════════════════════════════════════════════════════════════════
# Job Pool — persistent storage of all known jobs + scores
# ═══════════════════════════════════════════════════════════════════


class JobPool:
    """Persistent job pool: stores all known jobs keyed by URL."""

    def __init__(self, cache_dir: Path) -> None:
        self._path = cache_dir / "job_pool.json"
        self._pool: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._pool = json.loads(self._path.read_text(encoding="utf-8"))
                logging.getLogger(__name__).info(
                    "Loaded job pool: %d jobs (%d scored)",
                    len(self._pool),
                    sum(1 for v in self._pool.values() if v.get("scored")),
                )
            except Exception as e:
                logging.getLogger(__name__).warning("Failed to load job pool: %s", e)
                self._pool = {}

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._pool, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @property
    def total_count(self) -> int:
        return len(self._pool)

    @property
    def scored_count(self) -> int:
        return sum(1 for v in self._pool.values() if v.get("scored"))

    @property
    def unscored_count(self) -> int:
        return self.total_count - self.scored_count

    def merge_crawled(self, new_jobs: list[RawJob]) -> list[RawJob]:
        """Merge new jobs into pool. Returns truly new (not previously seen) jobs."""
        truly_new: list[RawJob] = []
        for job in new_jobs:
            key = job.dedup_key
            if key not in self._pool:
                self._pool[key] = {"job": job.model_dump(), "scored": None}
                truly_new.append(job)
        self.save()
        return truly_new

    def get_unscored_jobs(self) -> list[RawJob]:
        return [RawJob(**v["job"]) for v in self._pool.values() if not v.get("scored")]

    def save_scored(self, scored_jobs: list[ScoredJob]) -> None:
        for sj in scored_jobs:
            key = sj.job.dedup_key
            if key in self._pool:
                self._pool[key]["scored"] = sj.model_dump()
            else:
                self._pool[key] = {"job": sj.job.model_dump(), "scored": sj.model_dump()}
        self.save()

    def get_all_scored(self, max_age_days: int = 30) -> list[ScoredJob]:
        """Get all scored jobs, filtering out expired ones."""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        result: list[ScoredJob] = []
        for v in self._pool.values():
            if not v.get("scored"):
                continue
            sj = ScoredJob(**v["scored"])
            ref_date_str = sj.job.date_posted or sj.job.first_seen_at
            if ref_date_str:
                try:
                    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
                        try:
                            ref_date = datetime.strptime(ref_date_str[:19], fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        ref_date = None
                    if ref_date and ref_date < cutoff:
                        continue
                except Exception:
                    pass
            result.append(sj)
        return result

    def clear_scores(self) -> None:
        for v in self._pool.values():
            v["scored"] = None
        self.save()

    def remove_expired(self, max_age_days: int = 60) -> int:
        cutoff = datetime.now() - timedelta(days=max_age_days)
        to_remove = []
        for key, v in self._pool.items():
            ref = v["job"].get("date_posted") or v["job"].get("first_seen_at", "")
            if ref:
                try:
                    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
                        try:
                            ref_date = datetime.strptime(ref[:19], fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        continue
                    if ref_date < cutoff:
                        to_remove.append(key)
                except Exception:
                    continue
        for key in to_remove:
            del self._pool[key]
        if to_remove:
            self.save()
        return len(to_remove)

    def find_by_company(self, company: str) -> list[ScoredJob]:
        """Find scored jobs matching a company name (case-insensitive partial match)."""
        company_lower = company.lower()
        results = []
        for v in self._pool.values():
            if not v.get("scored"):
                continue
            sj = ScoredJob(**v["scored"])
            if company_lower in sj.job.company.lower():
                results.append(sj)
        return sorted(results, key=lambda s: s.score, reverse=True)

    def mark_applied(self, dedup_key: str) -> bool:
        """Mark a scored job as applied. Returns True if found and updated."""
        entry = self._pool.get(dedup_key)
        if not entry or not entry.get("scored"):
            return False
        # Deserialize → mutate proper fields → re-serialize
        sj = ScoredJob(**entry["scored"])
        sj.applied = True
        sj.applied_at = datetime.now().isoformat()
        entry["scored"] = sj.model_dump()
        self.save()
        return True


# ═══════════════════════════════════════════════════════════════════
# Core pipeline stages
# ═══════════════════════════════════════════════════════════════════


def _collect_jobs(queries: list[SearchQuery], config: AppConfig) -> list[RawJob]:
    all_jobs: list[RawJob] = []
    for source in _ALL_SOURCES:
        if not source.is_enabled(config):
            continue
        source_queries = [q for q in queries if q.source.startswith(source.name)]
        if not source_queries:
            source_queries = [
                q for q in queries
                if q.source.startswith("jobspy") and source.name == "jobspy"
            ]
            if not source_queries:
                continue

        console.print(f"\n[bold blue]🔍 {source.name}[/] — {len(source_queries)} queries")
        for query in source_queries:
            try:
                jobs = source.search(query, config)
                all_jobs.extend(jobs)
                console.print(f"  ✅ '{query.keyword}' in '{query.location}': {len(jobs)} jobs")
            except Exception as e:
                console.print(
                    f"  ❌ '{query.keyword}' in '{query.location}': {e}", style="red"
                )
    return all_jobs


def _parse_cv(
    config: AppConfig, llm: LLMClient, cache_dir: Path
) -> tuple[CandidateProfile, str]:
    cv_path = config.resolve_path(config.candidate.cv_path)
    cv_text = read_cv(cv_path)
    if config.candidate.profile_json_path:
        profile_path = config.resolve_path(config.candidate.profile_json_path)
        raw = json.loads(profile_path.read_text())
        profile = CandidateProfile(**raw)
    else:
        profile = parse_cv_to_profile(
            cv_text, llm, cache_dir=cache_dir,
            skip_if_unchanged=config.runtime.skip_unchanged_cv,
        )
    return profile, cv_text


def run_crawl(config: AppConfig) -> tuple[JobPool, list[RawJob]]:
    """Stage 1: Parse CV → build queries → search → deduplicate → merge into pool."""
    t_start = time.time()
    llm = LLMClient(config.llm.text)
    cache_dir = config.resolve_path(config.runtime.cache_dir)
    pool = JobPool(cache_dir)

    console.print("\n[bold green]📄 Step 1: Parse CV[/]")
    profile, cv_text = _parse_cv(config, llm, cache_dir)
    console.print(
        f"  ✅ {profile.personal.name} | "
        f"{len(profile.skills.technical)} skills | "
        f"{len(profile.experience)} experiences"
    )

    console.print("\n[bold green]🔎 Step 2: Build Search Queries[/]")
    queries = build_queries(profile, config)
    console.print(
        f"  ✅ {len(queries)} queries across "
        f"{len(set(q.source for q in queries))} sources"
    )

    if config.runtime.mode == "dry-run":
        console.print("\n[bold yellow]🏃 DRY RUN — queries generated, not executed[/]")
        for q in queries:
            console.print(f"  [{q.source}] '{q.keyword}' in '{q.location}' ({q.language})")
        return pool, []

    console.print("\n[bold green]🌐 Step 3: Search Job Platforms[/]")
    raw_jobs = _collect_jobs(queries, config)
    console.print(f"\n  📦 Total raw results: {len(raw_jobs)}")

    if not raw_jobs:
        console.print("\n[yellow]No jobs found. Check your config and API keys.[/]")
        return pool, []

    console.print("\n[bold green]🧹 Step 4: Deduplicate[/]")
    dedup = Deduplicator()
    unique_jobs = dedup.deduplicate(raw_jobs)
    console.print(
        f"  ✅ {len(unique_jobs)} unique "
        f"(removed {len(raw_jobs) - len(unique_jobs)} duplicates)"
    )

    console.print("\n[bold green]💾 Step 5: Merge into job pool[/]")
    pool_before = pool.total_count
    truly_new = pool.merge_crawled(unique_jobs)
    console.print(
        f"  ✅ Pool: {pool_before} → {pool.total_count} "
        f"(+{len(truly_new)} new, {pool.scored_count} scored)"
    )

    removed = pool.remove_expired(max_age_days=60)
    if removed:
        console.print(f"  🗑️  Removed {removed} expired jobs (>60 days)")

    elapsed = time.time() - t_start
    console.print(f"\n  ⏱️  Crawl: {elapsed:.1f}s")

    if truly_new:
        sources: dict[str, int] = {}
        for j in truly_new:
            sources[j.source] = sources.get(j.source, 0) + 1
        console.print("  📊 New jobs by source: " +
                       ", ".join(f"{k}({v})" for k, v in sorted(sources.items())))

    return pool, truly_new


def run_score(
    config: AppConfig,
    pool: JobPool | None = None,
    only_new: list[RawJob] | None = None,
) -> list[ScoredJob]:
    """Stage 2: Score unscored jobs → generate outputs. Returns newly scored jobs."""
    t_start = time.time()
    cache_dir = config.resolve_path(config.runtime.cache_dir)
    llm = LLMClient(config.llm.text)

    if pool is None:
        pool = JobPool(cache_dir)

    profile, cv_text = _parse_cv(config, llm, cache_dir)

    # Load feedback for scoring bias
    feedback_summary = load_feedback_summary(cache_dir)
    if feedback_summary:
        console.print("\n[dim]💭 Applying feedback preferences to scoring[/]")

    # Determine what to score
    if only_new is not None:
        to_score = only_new
        console.print(f"\n[bold green]🎯 Scoring {len(to_score)} NEW jobs[/]")
    else:
        to_score = pool.get_unscored_jobs()
        console.print(f"\n[bold green]🎯 Scoring {len(to_score)} unscored jobs[/]")

    newly_scored: list[ScoredJob] = []
    if not to_score:
        console.print("  ✅ Nothing new to score")
    else:
        enriched = enrich_jobs(to_score)

        def _checkpoint(scored_so_far: list[ScoredJob]) -> None:
            pool.save_scored(scored_so_far)

        newly_scored = score_jobs(
            enriched, profile, cv_text, llm,
            batch_size=config.scoring.batch_size,
            on_batch_done=_checkpoint,
            feedback_summary=feedback_summary,
        )
        pool.save_scored(newly_scored)
        console.print(f"  💾 Scored {len(newly_scored)} jobs")

    # Generate outputs from ALL active scored jobs
    console.print("\n[bold green]📊 Generating outputs[/]")
    max_age = config.search.max_days_old or 30
    all_scored = pool.get_all_scored(max_age_days=max_age)
    all_scored.sort(key=lambda s: s.avg_dimension_score, reverse=True)

    above_threshold = [s for s in all_scored if s.score >= config.scoring.min_score_digest]
    console.print(
        f"  {len(all_scored)} active scored jobs, "
        f"{len(above_threshold)} above threshold ({config.scoring.min_score_digest})"
    )

    output_dir = config.resolve_path(config.output.dir)

    if config.output.excel.enabled:
        excel_path = output_dir / config.output.excel.filename
        write_excel(all_scored, excel_path)
        console.print(f"  ✅ Excel: {excel_path}")

    digest_path = None
    if config.output.digest.get("enabled", True):
        digest_dir = output_dir / config.output.digest.get("dir", "digests")
        digest_path = generate_digest(
            all_scored, output_dir=digest_dir,
            min_score=config.scoring.min_score_digest,
        )
        if digest_path:
            console.print(f"  ✅ Digest: {digest_path}")

    if config.output.applications.get("enabled", True):
        app_dir = output_dir / config.output.applications.get("dir", "applications")
        app_jobs = [s for s in all_scored if s.score >= config.scoring.min_score_application]
        for sj in app_jobs[:5]:
            try:
                pkg = generate_application(sj, profile, cv_text, llm, app_dir)
                console.print(f"  ✅ App: {sj.job.company} → {pkg.name}")
            except Exception as e:
                console.print(f"  ❌ App gen failed for {sj.job.company}: {e}", style="red")

    elapsed = time.time() - t_start
    console.print(
        f"\n[bold green]🎉 Done![/] "
        f"Pool: {pool.total_count} total, {pool.scored_count} scored. "
        f"({elapsed:.1f}s)"
    )
    return newly_scored


def run_pipeline(config: AppConfig) -> None:
    """Full pipeline: crawl + score all unscored + output."""
    pool, _ = run_crawl(config)
    run_score(config, pool)


def run_update(config: AppConfig) -> None:
    """Incremental: crawl → score ONLY new jobs → output → send email."""
    pool, truly_new = run_crawl(config)
    if truly_new:
        newly_scored = run_score(config, pool, only_new=truly_new)
        _maybe_send_email(config, newly_scored, pool.total_count)
    else:
        console.print("\n[yellow]No new jobs found — regenerating outputs from pool[/]")
        run_score(config, pool, only_new=[])


def _maybe_send_email(
    config: AppConfig, new_scored: list[ScoredJob], total: int
) -> None:
    """Send email digest if configured."""
    notifier = EmailNotifier(config.notifications.email.model_dump())
    if notifier.send_digest(new_scored, total):
        console.print(f"\n  📧 Email digest sent to {config.notifications.email.to_addr}")


# ═══════════════════════════════════════════════════════════════════
# Conversational commands (for OpenClaw / Claude Code)
# ═══════════════════════════════════════════════════════════════════


def cmd_show_digest(config: AppConfig) -> None:
    """Print today's digest to stdout (for AI to read inline)."""
    from datetime import date
    output_dir = config.resolve_path(config.output.dir)
    digest_dir = output_dir / config.output.digest.get("dir", "digests")
    today = date.today().isoformat()

    # Try today first, then most recent
    candidates = [digest_dir / f"digest_{today}.md"]
    if digest_dir.exists():
        candidates += sorted(digest_dir.glob("digest_*.md"), reverse=True)[:3]

    for path in candidates:
        if path.exists():
            console.print(f"\n[dim]📋 Digest: {path}[/]\n")
            console.print(path.read_text(encoding="utf-8"))
            return

    console.print("[yellow]No digest found. Run 'jobradar --update' first.[/]")


def cmd_generate_app(company: str, config: AppConfig) -> None:
    """Generate application materials for a specific company."""
    cache_dir = config.resolve_path(config.runtime.cache_dir)
    pool = JobPool(cache_dir)
    matches = pool.find_by_company(company)

    if not matches:
        console.print(f"[yellow]No scored jobs found for company: '{company}'[/]")
        console.print("Run 'jobradar --update' first, or check company name spelling.")
        return

    sj = matches[0]
    console.print(
        f"\n  Found: [bold]{sj.job.title} @ {sj.job.company}[/] "
        f"(score: {sj.score:.1f})"
    )

    llm = LLMClient(config.llm.text)
    cv_path = config.resolve_path(config.candidate.cv_path)
    cv_text = read_cv(cv_path)
    profile, _ = _parse_cv(config, llm, cache_dir)

    output_dir = config.resolve_path(config.output.dir)
    app_dir = output_dir / config.output.applications.get("dir", "applications")
    pkg = generate_application(sj, profile, cv_text, llm, app_dir)

    console.print(f"\n  ✅ Application package: {pkg}")
    console.print(f"  📝 Cover letter: {pkg / 'cover_letter.md'}")
    console.print(f"  📌 CV highlights: {pkg / 'cv_highlights.md'}")


def cmd_mark_applied(company: str, config: AppConfig) -> None:
    """Mark a job as applied in the Excel tracker."""
    cache_dir = config.resolve_path(config.runtime.cache_dir)
    pool = JobPool(cache_dir)
    matches = pool.find_by_company(company)

    if not matches:
        console.print(f"[yellow]No scored jobs found for company: '{company}'[/]")
        return

    sj = matches[0]
    console.print(
        f"\n  Marking as applied: [bold]{sj.job.title} @ {sj.job.company}[/]"
    )

    # Use the public method — mutates the ScoredJob.applied / applied_at fields
    updated = pool.mark_applied(sj.job.dedup_key)
    if not updated:
        console.print(f"[yellow]  Could not update pool entry for '{company}'[/]")
        return

    # Re-generate Excel
    output_dir = config.resolve_path(config.output.dir)
    max_age = config.search.max_days_old or 30
    all_scored = pool.get_all_scored(max_age_days=max_age)
    excel_path = output_dir / config.output.excel.filename
    write_excel(all_scored, excel_path)
    console.print(f"  ✅ Excel updated: {excel_path}")

    # Record as feedback so future scoring deprioritises already-applied companies
    record_feedback([f"{sj.job.company} applied"], cache_dir)


def cmd_explain(company: str, config: AppConfig) -> None:
    """Print full scoring breakdown for a specific job."""
    cache_dir = config.resolve_path(config.runtime.cache_dir)
    pool = JobPool(cache_dir)
    matches = pool.find_by_company(company)

    if not matches:
        console.print(f"[yellow]No scored jobs found for company: '{company}'[/]")
        return

    sj = matches[0]
    console.print(f"\n[bold]📊 Score Breakdown: {sj.job.title} @ {sj.job.company}[/]")
    console.print(f"\n  Overall score: [bold]{sj.score:.1f}/10[/]")
    console.print(f"  Avg dimension: {sj.avg_dimension_score:.1f}/10")
    console.print(f"\n  Dimensions:")
    console.print(f"    Skills match:    {sj.breakdown.skills_match:.0f}/10")
    console.print(f"    Seniority fit:   {sj.breakdown.seniority_fit:.0f}/10")
    console.print(f"    Location fit:    {sj.breakdown.location_fit:.0f}/10")
    console.print(f"    Language fit:    {sj.breakdown.language_fit:.0f}/10")
    console.print(f"    Visa friendly:   {sj.breakdown.visa_friendly:.0f}/10")
    console.print(f"    Growth potential:{sj.breakdown.growth_potential:.0f}/10")
    console.print(f"\n  [bold]Reasoning:[/]\n  {sj.reasoning}")
    console.print(f"\n  [bold]Application angle:[/]\n  {sj.application_angle}")
    console.print(f"\n  🔗 {sj.job.url}")


# ═══════════════════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(
        description="JobRadar — AI-powered job search agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  jobradar --setup                   Interactive setup wizard
  jobradar --mode quick              Fast test run (2 sources)
  jobradar --update                  Daily incremental update
  jobradar --show-digest             Print today's top jobs
  jobradar --generate-app AMD        Cover letter for AMD job
  jobradar --mark-applied SAP        Mark SAP job as applied
  jobradar --explain Databricks      Show score breakdown
  jobradar --feedback "AMD liked"    Record job preference
  jobradar --install-agent           Set up daily 8am automation
        """,
    )

    # Setup / agent
    parser.add_argument("--setup", action="store_true", help="Run interactive setup wizard")
    parser.add_argument("--install-agent", action="store_true", help="Install daily scheduler")
    parser.add_argument("--uninstall-agent", action="store_true", help="Remove daily scheduler")
    parser.add_argument("--agent-hour", type=int, default=8, help="Hour to run agent (default: 8)")

    # Pipeline modes
    parser.add_argument("--config", type=str, help="Path to config.yaml")
    parser.add_argument(
        "--mode", choices=["full", "quick", "dry-run"], default=None,
        help="Run mode (overrides config.yaml)",
    )
    parser.add_argument("--crawl-only", action="store_true", help="Crawl only (no scoring)")
    parser.add_argument("--score-only", action="store_true", help="Score unscored jobs + output")
    parser.add_argument("--update", action="store_true", help="Incremental update (new jobs only)")
    parser.add_argument("--parse-cv-only", action="store_true", help="Parse CV → JSON and exit")
    parser.add_argument("--rerun-scoring", action="store_true", help="Clear scores and re-score all")

    # Conversational commands
    parser.add_argument("--show-digest", action="store_true", help="Print today's digest")
    parser.add_argument("--generate-app", metavar="COMPANY", help="Generate cover letter for company")
    parser.add_argument("--mark-applied", metavar="COMPANY", help="Mark job as applied")
    parser.add_argument("--explain", metavar="COMPANY", help="Show score breakdown for company")
    parser.add_argument(
        "--feedback", nargs="+", metavar="ENTRY",
        help='Record preferences: "AMD liked" "SAP not_interested"',
    )

    args = parser.parse_args()

    # ── Setup wizard (no config needed) ──
    if args.setup:
        project_root = Path(__file__).parent.parent
        run_setup(project_root)
        return

    # ── Agent installer (no config needed) ──
    if args.install_agent:
        install_agent(run_hour=args.agent_hour)
        return
    if args.uninstall_agent:
        uninstall_agent()
        return

    # ── Load config for all other commands ──
    try:
        config_path = find_config(args.config)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/]")
        console.print("Run [bold]jobradar --setup[/] to create a config file.")
        return

    config = load_config(config_path)

    # ── LLM availability check ──
    _llm_ok, _llm_source = probe_llm_env(config.llm.text)
    if not _llm_ok:
        # Check if the command even needs an LLM
        _no_llm_cmds = {"show_digest", "mark_applied", "install_agent",
                        "uninstall_agent", "feedback"}
        _needs_llm = not any(
            getattr(args, cmd, False) for cmd in _no_llm_cmds
        )
        if _needs_llm:
            console.print(format_setup_guidance())
            console.print("[bold red]Aborted:[/] configure an LLM API key first.")
            return
    else:
        console.print(
            f"[dim]🤖 LLM: [bold]{config.llm.text.model}[/] "
            f"via {_llm_source}[/]"
        )

    if args.mode:
        config.runtime.mode = args.mode

    if config.runtime.mode == "quick":
        config.sources.stepstone.enabled = False
        config.sources.linkedin.enabled = False
        config.sources.xing.enabled = False
        config.sources.scrapegraph.enabled = False
        config.sources.apify.enabled = False

    _setup_logging(config.runtime.log_level)

    # ── Conversational commands ──
    if args.show_digest:
        cmd_show_digest(config)
        return

    if args.generate_app:
        cmd_generate_app(args.generate_app, config)
        return

    if args.mark_applied:
        cmd_mark_applied(args.mark_applied, config)
        return

    if args.explain:
        cmd_explain(args.explain, config)
        return

    if args.feedback:
        cache_dir = config.resolve_path(config.runtime.cache_dir)
        record_feedback(args.feedback, cache_dir)
        return

    # ── Pipeline commands ──
    if args.rerun_scoring:
        cache_dir = config.resolve_path(config.runtime.cache_dir)
        pool = JobPool(cache_dir)
        pool.clear_scores()
        console.print(f"[yellow]Cleared scores for {pool.total_count} jobs — will re-score all[/]")

    if args.parse_cv_only:
        llm = LLMClient(config.llm.text)
        cv_text = read_cv(config.resolve_path(config.candidate.cv_path))
        cache_dir = config.resolve_path(config.runtime.cache_dir)
        profile = parse_cv_to_profile(cv_text, llm, cache_dir=cache_dir, skip_if_unchanged=False)
        console.print_json(profile.model_dump_json(indent=2))
    elif args.crawl_only:
        run_crawl(config)
    elif args.score_only:
        run_score(config)
    elif args.update:
        run_update(config)
    else:
        run_pipeline(config)


if __name__ == "__main__":
    main()
