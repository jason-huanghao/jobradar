"""Typer CLI — thin wrapper over the pipeline and API server."""

from __future__ import annotations

import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="jobradar", help="AI-powered job search agent", add_completion=False)
console = Console()


@app.command()
def web(
    port: Optional[int] = typer.Option(None, help="Override config server.port"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser"),
):
    """Start the web dashboard."""
    try:
        import uvicorn
    except ImportError:
        console.print("[red]uvicorn not installed. Run: pip install 'openclaw-jobradar[web]'[/red]")
        raise typer.Exit(1)

    from ..config import load_config
    cfg = load_config()
    if port:
        cfg.server.port = port

    url = f"http://{cfg.server.host}:{cfg.server.port}"
    console.print(f"[bold green]⚡ JobRadar[/bold green] → {url}")

    if not no_browser and cfg.server.open_browser:
        webbrowser.open(url)

    from ..api.main import create_app
    uvicorn.run(create_app(cfg), host=cfg.server.host, port=cfg.server.port, log_level="warning")


@app.command()
def update(
    mode: str = typer.Option("full", help="full | quick | score-only | dry-run"),
    config: Optional[Path] = typer.Option(None, "--config", help="Path to config.yaml"),
    limit: Optional[int] = typer.Option(
        None, "--limit",
        help="Max results per source per query (overrides config). Useful for quick tests.",
    ),
):
    """Fetch and score jobs (run this daily).

    Use --mode quick --limit 3 for a fast smoke test (few jobs, fast scoring).
    """
    from ..config import load_config
    from ..llm.env_probe import probe_llm_env
    from ..pipeline import JobRadarPipeline

    cfg = load_config(config)

    # --limit flag overrides quick_max_results and max_results_per_source
    if limit is not None:
        cfg.search.quick_max_results = limit
        cfg.search.max_results_per_source = limit

    found, source = probe_llm_env(cfg.llm.text)
    if not found:
        console.print(f"[red]No LLM configured.[/red] {source}")
        console.print("Set an API key in [cyan].env[/cyan] — e.g. ARK_API_KEY=your_key")
        raise typer.Exit(1)

    console.print(f"[dim]LLM: {cfg.llm.text.model} via {source}[/dim]")
    if limit:
        console.print(f"[dim]Limit: {limit} results per source per query[/dim]")
    console.print(f"[bold]Running pipeline[/bold] (mode={mode})…")

    def on_progress(event):
        msgs = {
            "profile_done":   f"✓ Profile: {event.data.get('name')}",
            "queries_built":  f"  Queries built: {event.data.get('count')}",
            "source_done":    f"  {event.data.get('source')}: {event.data.get('count')} jobs",
            "fetch_done":     f"→ Fetched: {event.data.get('total')} total",
            "filter_done":    f"→ Filter: {event.data.get('kept')} kept, {event.data.get('dropped')} dropped",
            "scoring_start":  f"  Scoring {event.data.get('total')} jobs…",
            "score_progress": f"  Scored {event.data.get('scored')}…",
            "gen_done":       f"✨ Generated {event.data.get('generated')} applications",
            "done":           (f"[green]✅ Done — fetched: {event.data.get('jobs_fetched')}, "
                               f"scored: {event.data.get('jobs_scored')}, "
                               f"generated: {event.data.get('jobs_generated')}[/green]"),
            "error":          f"[red]✗ {event.data.get('message')}[/red]",
        }
        msg = msgs.get(event.event)
        if msg:
            console.print(msg)

    pipeline = JobRadarPipeline(cfg)
    result = pipeline.run(mode=mode, on_progress=on_progress)

    if result.status == "failed":
        console.print(f"[red]Pipeline failed: {result.error}[/red]")
        raise typer.Exit(1)


@app.command()
def status():
    """Show DB stats and pipeline status."""
    from ..config import load_config
    from ..storage.db import get_session, init_db
    from ..storage.models import Job, ScoredJobRecord
    from sqlmodel import func, select

    cfg = load_config()
    db_path = cfg.resolve_path(cfg.server.db_path)
    init_db(db_path)

    with next(get_session(db_path)) as session:
        job_count   = session.exec(select(func.count(Job.id))).one()
        score_count = session.exec(select(func.count(ScoredJobRecord.job_id))).one()

    table = Table(show_header=False)
    table.add_column(style="dim")
    table.add_column(style="bold green")
    table.add_row("Jobs in DB",  str(job_count))
    table.add_row("Scored jobs", str(score_count))
    table.add_row("DB path",     str(db_path))
    console.print(table)


@app.command()
def health():
    """Check LLM connectivity and config validity."""
    from ..config import load_config
    from ..llm.client import LLMClient
    from ..llm.env_probe import probe_llm_env

    cfg = load_config()

    # Check LLM
    found, source = probe_llm_env(cfg.llm.text)
    if not found:
        console.print(f"[red]✗ LLM not configured.[/red] {source}")
        raise typer.Exit(1)

    console.print(f"[dim]LLM source: {source}[/dim]")
    try:
        llm = LLMClient(cfg.llm.text)
        resp = llm.complete("Say OK in one word.", temperature=0.0)
        console.print(f"[green]✓ LLM ping OK[/green] — response: {resp!r}")
    except Exception as e:
        console.print(f"[red]✗ LLM ping failed: {e}[/red]")
        raise typer.Exit(1)

    # Check CV
    cv_path = cfg.resolve_path(cfg.candidate.cv_path)
    if cv_path.exists():
        console.print(f"[green]✓ CV found:[/green] {cv_path}")
    else:
        console.print(f"[yellow]⚠ CV not found:[/yellow] {cv_path}")
        console.print("  Set candidate.cv_path in config.yaml")

    # Check cache
    cache_dir = cfg.resolve_path(cfg.server.cache_dir)
    profile_cache = cache_dir / "candidate_profile.json"
    if profile_cache.exists():
        console.print(f"[green]✓ Cached profile:[/green] {profile_cache}")
    else:
        console.print(f"[dim]  No cached profile yet (will be created on first run)[/dim]")


@app.command()
def setup():
    """Copy config.example.yaml → config.yaml if missing."""
    console.print("[bold]JobRadar Setup[/bold]")
    cfg_path = Path("config.yaml")
    if not cfg_path.exists():
        from shutil import copy
        example = Path(__file__).parent.parent.parent.parent / "config.example.yaml"
        if example.exists():
            copy(example, cfg_path)
            console.print(f"[green]✓ Created config.yaml[/green]")
        else:
            console.print("[yellow]config.example.yaml not found — please create config.yaml manually.[/yellow]")
    else:
        console.print("[dim]config.yaml already exists.[/dim]")
    console.print("\nNext steps:")
    console.print("  1. Edit [cyan]config.yaml[/cyan] — set candidate.cv_path and search.locations")
    console.print("  2. Set LLM key in [cyan].env[/cyan] — e.g. ARK_API_KEY=your_key")
    console.print("  3. Run [bold]jobradar health[/bold] to verify")
    console.print("  4. Run [bold]jobradar update --mode quick --limit 3[/bold] for a quick test")


@app.command("install-agent")
def install_agent():
    """Install a launchd agent to run jobradar update daily at 08:00 (macOS)."""
    import plistlib
    jobradar_bin = subprocess.run(
        ["which", "jobradar"], capture_output=True, text=True
    ).stdout.strip() or str(Path(sys.executable).parent / "jobradar")

    plist = {
        "Label": "com.jobradar.update",
        "ProgramArguments": [jobradar_bin, "update", "--mode", "quick"],
        "StartCalendarInterval": {"Hour": 8, "Minute": 0},
        "StandardOutPath": str(Path.home() / "Library/Logs/jobradar.log"),
        "StandardErrorPath": str(Path.home() / "Library/Logs/jobradar.err"),
        "RunAtLoad": False,
    }
    agents_dir = Path.home() / "Library/LaunchAgents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    plist_path = agents_dir / "com.jobradar.update.plist"
    with open(plist_path, "wb") as f:
        plistlib.dump(plist, f)

    subprocess.run(["launchctl", "load", str(plist_path)], capture_output=True)
    console.print(f"[green]✓ Installed launchd agent:[/green] {plist_path}")
    console.print("  Runs daily at 08:00 — logs → ~/Library/Logs/jobradar.log")


def main():
    app()
