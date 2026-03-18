"""Typer CLI — thin wrapper over the pipeline and API server."""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="jobradar", help="AI-powered job search agent", add_completion=False,
                  context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
console = Console()

# ── Supported LLM providers for init wizard ────────────────────────
_PROVIDERS = [
    # (display_name, env_var, base_url, default_model)
    ("Volcengine Ark (doubao)",  "ARK_API_KEY",       "https://ark.cn-beijing.volces.com/api/coding/v3", "doubao-seed-2.0-code"),
    ("Z.AI (Claude proxy)",      "ZAI_API_KEY",        "https://api.z.ai/v1",                            "claude-sonnet-4-20250514"),
    ("OpenAI",                   "OPENAI_API_KEY",     "https://api.openai.com/v1",                       "gpt-4o-mini"),
    ("DeepSeek",                 "DEEPSEEK_API_KEY",   "https://api.deepseek.com/v1",                     "deepseek-chat"),
    ("OpenRouter",               "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1",                    "anthropic/claude-3-5-haiku"),
    ("Anthropic",                "ANTHROPIC_API_KEY",  "https://api.anthropic.com/v1",                    "claude-sonnet-4-20250514"),
    ("Ollama (local)",           "",                   "http://localhost:11434/v1",                        "llama3.1"),
    ("LM Studio (local)",        "",                   "http://localhost:1234/v1",                         "loaded-model"),
]


# ── jobradar init ──────────────────────────────────────────────────

@app.command()
def init(
    cv: Optional[str] = typer.Option(
        None, "--cv",
        help="CV source: file path (.md/.pdf/.docx/.txt), URL, or '-' to paste text.",
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key",
        help="LLM API key as ENV_VAR=value, e.g. ARK_API_KEY=abc123",
    ),
    locations: Optional[str] = typer.Option(
        None, "--locations",
        help="Comma-separated search locations, e.g. 'Berlin,Hannover,Remote'",
    ),
    yes: bool = typer.Option(False, "-y", "--yes", help="Non-interactive: accept all defaults"),
):
    """Interactive setup wizard — configure LLM key, CV, and search locations.

    Can be called non-interactively:

        jobradar init --cv /path/to/cv.pdf --api-key ARK_API_KEY=xxx --locations "Berlin,Remote" -y
    """
    from shutil import copy

    console.print("")
    console.print("[bold cyan]⚡ JobRadar Setup Wizard[/bold cyan]")
    console.print("━" * 50)

    project_dir = _find_project_dir()
    console.print(f"[dim]Project dir: {project_dir}[/dim]")
    os.chdir(project_dir)

    # ── Step 1: config.yaml ────────────────────────────────────────
    cfg_path = project_dir / "config.yaml"
    if not cfg_path.exists():
        example = project_dir / "config.example.yaml"
        if example.exists():
            copy(example, cfg_path)
            console.print("✓ Created config.yaml from config.example.yaml")
        else:
            console.print("[yellow]⚠ config.example.yaml not found — creating minimal config.yaml[/yellow]")
            cfg_path.write_text(_MINIMAL_CONFIG)

    # ── Step 2: API key ────────────────────────────────────────────
    console.print("")
    console.print("[bold]Step 1/3 — LLM API Key[/bold]")
    resolved_key_line = _resolve_api_key(api_key, yes, project_dir)
    if resolved_key_line:
        _write_env(project_dir, resolved_key_line)

    # ── Step 3: CV file ────────────────────────────────────────────
    console.print("")
    console.print("[bold]Step 2/3 — Your CV[/bold]")
    cv_path_str = _resolve_cv(cv, yes, project_dir)
    if cv_path_str:
        _patch_config(cfg_path, "cv_path", cv_path_str)
        console.print(f"  ✓ CV set: [cyan]{cv_path_str}[/cyan]")

    # ── Step 4: Locations ──────────────────────────────────────────
    console.print("")
    console.print("[bold]Step 3/3 — Search Locations[/bold]")
    locs = _resolve_locations(locations, yes)
    if locs:
        _patch_config_locations(cfg_path, locs)
        console.print(f"  ✓ Locations: [cyan]{', '.join(locs)}[/cyan]")

    # ── Step 5: Health check ───────────────────────────────────────
    console.print("")
    console.print("━" * 50)
    console.print("[bold]Running health check…[/bold]")
    console.print("")
    ctx = typer.Context(health)
    health.callback(ctx) if hasattr(health, 'callback') else None

    # Call health directly
    _run_health_check(project_dir)

    console.print("")
    console.print("━" * 50)
    console.print("[bold green]✅ JobRadar is ready![/bold green]")
    console.print("")
    console.print("Quick start:")
    console.print("  [bold]jobradar update --mode quick --limit 5[/bold]   # fetch & score jobs")
    console.print("  [bold]jobradar web[/bold]                              # open dashboard")
    console.print("  [bold]jobradar status[/bold]                           # show DB stats")
    console.print("")


def _resolve_api_key(cli_key: Optional[str], yes: bool, project_dir: Path) -> Optional[str]:
    """Detect or prompt for LLM API key. Returns 'ENV_VAR=value' string or None."""

    # 1. CLI flag wins
    if cli_key:
        if "=" not in cli_key:
            console.print(f"[red]--api-key must be ENV_VAR=value, e.g. ARK_API_KEY=abc123[/red]")
            return None
        env_var, _, val = cli_key.partition("=")
        console.print(f"  ✓ Using provided key: [cyan]{env_var}[/cyan]")
        return cli_key

    # 2. Auto-detect from current environment
    for name, env_var, _, _ in _PROVIDERS:
        if not env_var:
            continue
        val = os.getenv(env_var, "").strip()
        if val and val not in ("your_volcengine_ark_key_here", "REPLACE_ME", ""):
            console.print(f"  ✓ Detected [cyan]{env_var}[/cyan] in environment → using [bold]{name}[/bold]")
            return f"{env_var}={val}"

    # 3. Check existing .env file
    env_file = project_dir / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            for _, env_var, _, _ in _PROVIDERS:
                if k == env_var and v and v not in ("your_volcengine_ark_key_here", "REPLACE_ME"):
                    console.print(f"  ✓ Found [cyan]{k}[/cyan] in .env file")
                    return None  # already in .env, no need to write again

    # 4. Interactive prompt
    if yes:
        console.print("  [yellow]⚠ No API key found — skipping (use --api-key to provide one)[/yellow]")
        return None

    console.print("  No LLM API key detected. Choose a provider:")
    console.print("")
    for i, (name, env_var, _, model) in enumerate(_PROVIDERS, 1):
        key_hint = f"  [{env_var}]" if env_var else "  [no key needed]"
        console.print(f"    [bold]{i}.[/bold] {name}{key_hint}")
    console.print("")

    choice = typer.prompt("  Enter number (or press Enter to skip)", default="")
    if not choice.strip():
        console.print("  [dim]Skipped — set your key in .env later[/dim]")
        return None

    try:
        idx = int(choice.strip()) - 1
        name, env_var, base_url, model = _PROVIDERS[idx]
    except (ValueError, IndexError):
        console.print("  [yellow]Invalid choice — skipped[/yellow]")
        return None

    if not env_var:
        # Local provider (Ollama / LM Studio) — no key needed
        console.print(f"  ✓ Using [bold]{name}[/bold] (no key required)")
        _patch_config_llm(project_dir / "config.yaml", name.lower().split()[0], base_url, model, "")
        return None

    key_val = typer.prompt(f"  Paste your {env_var}", hide_input=True)
    key_val = key_val.strip()
    if not key_val:
        console.print("  [dim]Skipped[/dim]")
        return None

    # Update config.yaml to match chosen provider
    _patch_config_llm(project_dir / "config.yaml",
                      name.lower().split()[0], base_url, model, env_var)
    console.print(f"  ✓ Key saved for [bold]{name}[/bold]")
    return f"{env_var}={key_val}"


def _resolve_cv(cli_cv: Optional[str], yes: bool, project_dir: Path) -> Optional[str]:
    """Resolve CV source. Returns the cv_path string to write to config."""

    if cli_cv:
        return _import_cv(cli_cv, project_dir)

    # Check if config already points to an existing file
    cfg_path = project_dir / "config.yaml"
    if cfg_path.exists():
        import re
        match = re.search(r'cv_path:\s*(.+)', cfg_path.read_text())
        if match:
            existing = (project_dir / match.group(1).strip().strip("\"'")).resolve()
            if existing.exists():
                console.print(f"  ✓ CV already configured: [cyan]{match.group(1).strip()}[/cyan]")
                return None  # already set and valid

    if yes:
        console.print("  [yellow]⚠ No CV provided — set candidate.cv_path in config.yaml[/yellow]")
        return None

    console.print("  Provide your CV (choose method):")
    console.print("    [bold]1.[/bold] File path or URL")
    console.print("    [bold]2.[/bold] Paste Markdown text")
    console.print("    [bold]3.[/bold] Skip for now")
    console.print("")

    choice = typer.prompt("  Enter number", default="3")

    if choice.strip() == "1":
        src = typer.prompt("  Path or URL").strip()
        return _import_cv(src, project_dir)

    elif choice.strip() == "2":
        console.print("  Paste your CV as Markdown. Enter a blank line then 'END' when done:")
        lines = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line.strip() == "END":
                break
            lines.append(line)
        cv_text = "\n".join(lines).strip()
        if cv_text:
            cv_dir = project_dir / "cv"
            cv_dir.mkdir(exist_ok=True)
            cv_file = cv_dir / "cv_current.md"
            cv_file.write_text(cv_text, encoding="utf-8")
            console.print(f"  ✓ CV saved to [cyan]cv/cv_current.md[/cyan] ({len(cv_text)} chars)")
            return "./cv/cv_current.md"
        else:
            console.print("  [dim]No text entered — skipped[/dim]")
            return None
    else:
        console.print("  [dim]Skipped — set candidate.cv_path in config.yaml later[/dim]")
        return None


def _import_cv(source: str, project_dir: Path) -> Optional[str]:
    """Copy/download a CV to cv/cv_current.{ext} and return the relative path."""
    import shutil
    from urllib.parse import urlparse

    cv_dir = project_dir / "cv"
    cv_dir.mkdir(exist_ok=True)

    source = source.strip()

    # URL
    if source.startswith("http://") or source.startswith("https://"):
        try:
            import httpx
            resp = httpx.get(source, follow_redirects=True, timeout=30)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            ext = ".pdf" if "pdf" in content_type else ".md"
            dest = cv_dir / f"cv_current{ext}"
            dest.write_bytes(resp.content)
            rel = f"./cv/cv_current{ext}"
            console.print(f"  ✓ Downloaded CV → [cyan]{rel}[/cyan]")
            return rel
        except Exception as e:
            console.print(f"  [red]Failed to download {source}: {e}[/red]")
            return None

    # stdin
    if source == "-":
        lines = sys.stdin.read()
        dest = cv_dir / "cv_current.md"
        dest.write_text(lines, encoding="utf-8")
        console.print(f"  ✓ CV read from stdin → [cyan]./cv/cv_current.md[/cyan]")
        return "./cv/cv_current.md"

    # Local file
    src_path = Path(source).expanduser().resolve()
    if not src_path.exists():
        console.print(f"  [red]File not found: {source}[/red]")
        return None

    ext = src_path.suffix.lower() or ".md"
    dest = cv_dir / f"cv_current{ext}"

    # If file is already inside project dir, use relative path
    try:
        rel = src_path.relative_to(project_dir)
        console.print(f"  ✓ CV already in project: [cyan]{rel}[/cyan]")
        return f"./{rel}"
    except ValueError:
        pass

    shutil.copy2(src_path, dest)
    console.print(f"  ✓ Copied {src_path.name} → [cyan]./cv/cv_current{ext}[/cyan]")
    return f"./cv/cv_current{ext}"


def _resolve_locations(cli_locs: Optional[str], yes: bool) -> Optional[list[str]]:
    if cli_locs:
        return [l.strip() for l in cli_locs.split(",") if l.strip()]
    if yes:
        return None
    locs = typer.prompt(
        "  Search locations (comma-separated, e.g. Berlin,Hannover,Remote)",
        default="Berlin,Remote",
    )
    return [l.strip() for l in locs.split(",") if l.strip()]


def _run_health_check(project_dir: Path) -> None:
    from ..config import load_config
    from ..llm.client import LLMClient
    from ..llm.env_probe import probe_llm_env

    os.chdir(project_dir)
    try:
        cfg = load_config()
    except Exception as e:
        console.print(f"  [yellow]⚠ Config load: {e}[/yellow]")
        return

    found, source = probe_llm_env(cfg.llm.text)
    if found:
        try:
            llm = LLMClient(cfg.llm.text)
            resp = llm.complete("Say OK in one word.", temperature=0.0)
            console.print(f"  [green]✓ LLM ({cfg.llm.text.model})[/green] ping OK")
        except Exception as e:
            console.print(f"  [yellow]⚠ LLM ping failed: {e}[/yellow]")
    else:
        console.print(f"  [yellow]⚠ No LLM key found — run [bold]jobradar init[/bold] to add one[/yellow]")

    cv_path = cfg.resolve_path(cfg.candidate.cv_path)
    if cv_path.exists():
        console.print(f"  [green]✓ CV found:[/green] {cfg.candidate.cv_path}")
    else:
        console.print(f"  [yellow]⚠ CV not found:[/yellow] {cfg.candidate.cv_path}")


def _write_env(project_dir: Path, key_line: str) -> None:
    env_file = project_dir / ".env"
    if env_file.exists():
        existing = env_file.read_text()
        k = key_line.split("=")[0]
        # Replace existing key or append
        lines = [l for l in existing.splitlines() if not l.startswith(k)]
        lines.append(key_line)
        env_file.write_text("\n".join(lines) + "\n")
    else:
        env_file.write_text(key_line + "\n")


def _patch_config(cfg_path: Path, key: str, value: str) -> None:
    import re
    txt = cfg_path.read_text()
    txt = re.sub(rf'{key}:.*', f'{key}: {value}', txt)
    cfg_path.write_text(txt)


def _patch_config_locations(cfg_path: Path, locs: list[str]) -> None:
    import re
    txt = cfg_path.read_text()
    new_locs = "\n".join(f"    - {l}" for l in locs)
    txt = re.sub(
        r'locations:\s*\n(\s+-[^\n]*\n)+',
        f'locations:\n{new_locs}\n',
        txt,
    )
    cfg_path.write_text(txt)


def _patch_config_llm(cfg_path: Path, provider: str, base_url: str,
                       model: str, api_key_env: str) -> None:
    import re
    txt = cfg_path.read_text()
    txt = re.sub(r'provider:.*', f'provider: {provider}', txt)
    txt = re.sub(r'model:.*doubao.*|model:.*claude.*|model:.*gpt.*|model:.*deepseek.*',
                 f'model: {model}', txt)
    txt = re.sub(r'base_url:.*', f'base_url: {base_url}', txt)
    if api_key_env:
        txt = re.sub(r'api_key_env:.*', f'api_key_env: {api_key_env}', txt)
    cfg_path.write_text(txt)


def _find_project_dir() -> Path:
    """Find the project root (containing config.example.yaml or pyproject.toml)."""
    # 1. JOBRADAR_DIR env var
    env_dir = os.getenv("JOBRADAR_DIR", "")
    if env_dir and Path(env_dir).exists():
        return Path(env_dir).resolve()

    # 2. Walk up from cwd
    here = Path.cwd()
    for parent in [here, *here.parents]:
        if (parent / "config.example.yaml").exists():
            return parent.resolve()
        if (parent / "pyproject.toml").exists():
            content = (parent / "pyproject.toml").read_text()
            if "openclaw-jobradar" in content:
                return parent.resolve()

    # 3. ~/.jobradar default
    default = Path.home() / ".jobradar"
    if default.exists():
        return default.resolve()

    return here.resolve()


_MINIMAL_CONFIG = """\
candidate:
  cv: ""

search:
  locations: []
  max_results_per_source: 20
  max_days_old: 14
  exclude_keywords:
    - Praktikum
    - Werkstudent
    - internship
    - Ausbildung

scoring:
  min_score_digest: 6.0
  min_score_application: 7.0
  auto_apply_min_score: 7.5
  batch_size: 5

sources:
  arbeitsagentur:
    enabled: true
  jobspy:
    enabled: true
    boards: [indeed, google]
    country: germany
  stepstone:
    enabled: true
  xing:
    enabled: true
  bosszhipin:
    enabled: false
  lagou:
    enabled: false
  zhilian:
    enabled: false

server:
  host: 127.0.0.1
  port: 7842
"""


# ── jobradar web ───────────────────────────────────────────────────

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


# ── jobradar update ────────────────────────────────────────────────

@app.command()
def update(
    mode: str = typer.Option("full", help="full | quick | score-only | dry-run"),
    cv: Optional[str] = typer.Option(
        None, "--cv",
        help="CV source: file path (.md/.pdf/.docx/.txt) or URL. Overrides config.",
    ),
    config: Optional[Path] = typer.Option(None, "--config", help="Path to config.yaml"),
    limit: Optional[int] = typer.Option(
        None, "--limit",
        help="Max results per source per query (e.g. --limit 3 for quick tests).",
    ),
):
    """Fetch and score jobs (run this daily).

    Quick smoke test:  jobradar update --mode quick --limit 3
    """
    from ..config import load_config
    from ..llm.env_probe import probe_llm_env
    from ..pipeline import JobRadarPipeline

    cfg = load_config(config, cv_override=cv)

    if limit is not None:
        cfg.search.quick_max_results = limit
        cfg.search.max_results_per_source = limit

    found, source = probe_llm_env(cfg.llm.text)
    if not found:
        console.print("[red]No LLM configured.[/red]")
        console.print("Run [bold]jobradar init[/bold] to set up your API key.")
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


# ── jobradar status ────────────────────────────────────────────────

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


# ── jobradar health ────────────────────────────────────────────────

@app.command()
def health():
    """Check LLM connectivity, CV file, and config validity."""
    from ..config import load_config
    from ..llm.client import LLMClient
    from ..llm.env_probe import probe_llm_env

    cfg = load_config()

    found, source = probe_llm_env(cfg.llm.text)
    if not found:
        console.print(f"[red]✗ LLM not configured.[/red] {source}")
        console.print("  Run [bold]jobradar init[/bold] to set up your API key.")
        raise typer.Exit(1)

    console.print(f"[dim]LLM source: {source}[/dim]")
    try:
        llm = LLMClient(cfg.llm.text)
        resp = llm.complete("Say OK in one word.", temperature=0.0)
        console.print(f"[green]✓ LLM ping OK[/green] ({cfg.llm.text.model}) → {resp!r}")
    except Exception as e:
        console.print(f"[red]✗ LLM ping failed: {e}[/red]")
        raise typer.Exit(1)

    cv_source = cfg.candidate.effective_cv()
    if cv_source and not cv_source.startswith("http"):
        cv_path = cfg.resolve_path(cv_source)
        if cv_path.exists():
            console.print(f"[green]✓ CV found:[/green] {cv_source}")
        else:
            console.print(f"[yellow]⚠ CV not found:[/yellow] {cv_source}")
            console.print("  Run [bold]jobradar init[/bold] to provide your CV.")
    elif cv_source.startswith("http"):
        console.print(f"[green]✓ CV URL:[/green] {cv_source}")
    else:
        console.print("[yellow]⚠ No CV configured.[/yellow]")
        console.print("  Run [bold]jobradar init[/bold] to provide your CV.")

    cache_dir = cfg.resolve_path(cfg.server.cache_dir)
    profile_cache = cache_dir / "candidate_profile.json"
    if profile_cache.exists():
        console.print(f"[green]✓ Cached profile:[/green] {profile_cache}")
    else:
        console.print("[dim]  No cached profile yet (created on first run)[/dim]")


# ── jobradar report ───────────────────────────────────────────────

@app.command()
def report(
    publish: bool = typer.Option(False, "--publish", help="Push to GitHub Pages and print URL"),
    min_score: float = typer.Option(0.0, "--min-score", help="Only include jobs above this score"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open report in browser"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Custom output path"),
):
    """Generate a self-contained HTML report of all scored jobs.

    Opens instantly in any browser — no server needed.

        jobradar report                  # generate + open locally
        jobradar report --publish        # generate + push to GitHub Pages
        jobradar report --min-score 7    # only include score >= 7
    """
    import webbrowser
    from datetime import datetime
    from ..config import load_config
    from ..report.generator import generate_report, jobs_from_db

    cfg = load_config()
    db_path = cfg.resolve_path(cfg.server.db_path)

    if not db_path.exists():
        console.print("[yellow]⚠ No database found — run [bold]jobradar run[/bold] first.[/yellow]")
        raise typer.Exit(1)

    console.print("[dim]Loading jobs from database…[/dim]")
    jobs = jobs_from_db(db_path, min_score=min_score)

    if not jobs:
        console.print(f"[yellow]No scored jobs found (min_score={min_score}).[/yellow]")
        console.print("Run [bold]jobradar run[/bold] to fetch and score jobs first.")
        raise typer.Exit(1)

    console.print(f"[dim]Generating report for {len(jobs)} jobs…[/dim]")
    report_path = generate_report(
        jobs,
        profile_name=_get_profile_name(cfg),
        generated_at=datetime.utcnow(),
        output_path=output,
    )
    console.print(f"[green]✓ Report generated:[/green] {report_path}")

    if publish:
        console.print("[dim]Publishing to GitHub Pages…[/dim]")
        try:
            from ..report.publisher import publish_to_github_pages
            from ..config import _find_config
            repo_dir = _find_config().parent
            url = publish_to_github_pages(report_path, repo_dir=repo_dir)
            console.print(f"[bold green]✓ Published:[/bold green] {url}")
            console.print(f"\n  Share this URL: [cyan]{url}[/cyan]")
        except Exception as e:
            console.print(f"[red]✗ Publish failed: {e}[/red]")
            console.print("  Ensure GitHub Pages is enabled on the gh-pages branch.")
            console.print("  Local report still available at: " + str(report_path))

    elif open_browser:
        webbrowser.open(report_path.as_uri())


def _get_profile_name(cfg) -> str:
    """Try to get candidate name from cached profile YAML or config."""
    try:
        profile_yaml = Path(cfg.candidate.profile_yaml)
        if profile_yaml.exists():
            import yaml as _yaml
            data = _yaml.safe_load(profile_yaml.read_text()) or {}
            return data.get("personal", {}).get("name", "")
    except Exception:
        pass
    return ""



@app.command()
def setup():
    """Copy config.example.yaml → config.yaml if missing (non-interactive)."""
    from shutil import copy
    console.print("[bold]JobRadar Setup[/bold]")
    cfg_path = Path("config.yaml")
    if not cfg_path.exists():
        example = Path(__file__).parent.parent.parent.parent / "config.example.yaml"
        if example.exists():
            copy(example, cfg_path)
            console.print("[green]✓ Created config.yaml[/green]")
        else:
            console.print("[yellow]config.example.yaml not found — run jobradar init[/yellow]")
    else:
        console.print("[dim]config.yaml already exists.[/dim]")
    console.print("\nFor guided setup, run: [bold]jobradar init[/bold]")


# ── jobradar install-agent ─────────────────────────────────────────

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


# ── jobradar apply ────────────────────────────────────────────────

@app.command()
def apply(
    min_score: float = typer.Option(7.5, "--min-score", "-s",
                                    help="Only apply to jobs at or above this score"),
    dry_run: bool = typer.Option(False, "--dry-run",
                                 help="Preview — no actual submissions"),
    auto: bool = typer.Option(False, "--auto",
                              help="Apply without confirmation prompts"),
    limit: Optional[int] = typer.Option(None, "--limit",
                                        help="Max applications this run"),
    platforms: Optional[str] = typer.Option(None, "--platforms",
                                            help="Comma-separated: bosszhipin,linkedin"),
):
    """Apply to top-scored jobs automatically.

        jobradar apply                       # interactive confirm each
        jobradar apply --auto                # autonomous above 7.5
        jobradar apply --auto --min-score 8  # only best matches
        jobradar apply --dry-run             # preview without submitting
    """
    from ..config import load_config
    from ..apply.engine import run_apply

    cfg = load_config()
    db_path = cfg.resolve_path(cfg.server.db_path)

    if not db_path.exists():
        console.print("[yellow]No database — run [bold]jobradar run[/bold] first.[/yellow]")
        raise typer.Exit(1)

    platform_list = (
        [p.strip() for p in platforms.split(",") if p.strip()]
        if platforms else ["bosszhipin", "linkedin"]
    )
    daily_cap = limit or 50

    if dry_run:
        console.print("[dim]Dry-run mode — no actual submissions[/dim]")
    console.print(
        f"[bold]Apply:[/bold] min_score={min_score} "
        f"platforms={platform_list}{' [dry-run]' if dry_run else ''}"
    )

    def on_result(r):
        icons = {"applied": "✅", "skipped": "⏭ ", "failed": "❌",
                 "blocked": "🚫", "dry_run": "👁 "}
        icon = icons.get(r.status.value, "?")
        console.print(f"  {icon} {r.title} @ {r.company} — {r.message}")

    session = run_apply(
        db_path=db_path,
        min_score=min_score,
        dry_run=dry_run,
        confirm_each=not auto and not dry_run,
        daily_limit=daily_cap,
        platforms=platform_list,
        on_result=on_result,
    )

    console.print(f"\n[bold green]Done.[/bold green] {session.summary}")
    if session.applied:
        console.print(f"  Applied to {len(session.applied)} job(s) today.")


def main():
    app()


# ── jobradar run (alias for update) ───────────────────────────────
app.command("run")(update.callback if hasattr(update, "callback") else update)
