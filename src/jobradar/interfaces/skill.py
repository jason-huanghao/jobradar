"""OpenClaw skill handler — wraps JobRadar API for use as an OpenClaw skill.

Entry point: jobradar.interfaces.skill:run_skill
Called by OpenClaw as: run_skill(tool_name, params_json)

Design principles:
- Never raises — always returns a valid JSON string.
- If not configured → returns setup instructions with a 'setup' tool the agent can call.
- 'setup' tool works without a running server — configures key + CV in-process.
- Auto-detects API keys from OpenClaw environment before asking the user.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import re
import time
from pathlib import Path
from typing import Any

import httpx

_SERVER_PROC: subprocess.Popen | None = None

# All env vars that might carry an LLM key (checked in priority order)
_ALL_KEY_VARS = [
    "OPENCLAW_API_KEY",   # OpenClaw's own key — can be reused via proxy
    "ARK_API_KEY",
    "ZAI_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "DEEPSEEK_API_KEY",
    "OPENROUTER_API_KEY",
]

# Provider table: (env_var, base_url, model)
_PROVIDER_MAP = {
    "OPENCLAW_API_KEY":   ("https://api.z.ai/v1",                            "claude-sonnet-4-20250514"),
    "ARK_API_KEY":        ("https://ark.cn-beijing.volces.com/api/coding/v3", "doubao-seed-2.0-code"),
    "ZAI_API_KEY":        ("https://api.z.ai/v1",                            "claude-sonnet-4-20250514"),
    "OPENAI_API_KEY":     ("https://api.openai.com/v1",                       "gpt-4o-mini"),
    "ANTHROPIC_API_KEY":  ("https://api.anthropic.com/v1",                    "claude-sonnet-4-20250514"),
    "DEEPSEEK_API_KEY":   ("https://api.deepseek.com/v1",                     "deepseek-chat"),
    "OPENROUTER_API_KEY": ("https://openrouter.ai/api/v1",                    "anthropic/claude-3-5-haiku"),
}


# Default: Germany-wide search — covers all major cities
_DEFAULT_LOCATIONS = [
    "Berlin", "Hamburg", "Munich", "Frankfurt", "Hannover",
    "Cologne", "Stuttgart", "Leipzig", "Dresden", "Nuremberg",
    "Remote",
]

# ── Project directory resolution ───────────────────────────────────

def _find_project_dir() -> Path | None:
    """Find the JobRadar project directory."""
    # 1. Explicit env var (set by install.sh)
    env_dir = os.getenv("JOBRADAR_DIR", "").strip()
    if env_dir and Path(env_dir).exists():
        return Path(env_dir).resolve()

    # 2. Walk up from cwd
    here = Path.cwd()
    for parent in [here, *here.parents]:
        if (parent / "config.example.yaml").exists():
            return parent.resolve()
        if (parent / "pyproject.toml").exists():
            if "openclaw-jobradar" in (parent / "pyproject.toml").read_text():
                return parent.resolve()

    return None


# ── Configuration check ────────────────────────────────────────────

def _detect_api_key() -> tuple[str | None, str | None, str | None]:
    """Return (env_var, base_url, model) for first detected key, or (None,None,None)."""
    # Check environment first
    for var in _ALL_KEY_VARS:
        val = os.getenv(var, "").strip()
        if val and val not in ("your_key_here", "REPLACE_ME", ""):
            base_url, model = _PROVIDER_MAP.get(var, (None, None))
            if base_url:
                return var, base_url, model

    # Check .env files
    for search_dir in [Path.cwd(), Path(os.environ.get("JOBRADAR_DIR", Path.cwd()))]:
        env_file = search_dir / ".env"
        if not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if k in _PROVIDER_MAP and v and v not in ("your_key_here", "REPLACE_ME"):
                base_url, model = _PROVIDER_MAP[k]
                # Export so load_config() finds it
                os.environ[k] = v
                return k, base_url, model
    return None, None, None


def _is_configured() -> tuple[bool, str]:
    """Check minimum config (key + CV). Returns (ok, message)."""
    project_dir = _find_project_dir()
    if project_dir is None:
        return False, (
            "JobRadar not installed. Install with:\n"
            "bash <(curl -fsSL https://raw.githubusercontent.com/jason-huanghao/jobradar/main/install.sh)\n"
            "Or call the 'setup' tool to configure interactively."
        )

    # Check API key
    var, _, _ = _detect_api_key()
    if not var:
        return False, (
            "No LLM API key found.\n"
            "Call the 'setup' tool with your api_key parameter, e.g.:\n"
            '  setup({"api_key": "ARK_API_KEY=your_key_here"})\n'
            "Or run: jobradar init"
        )

    # Check CV
    cfg_path = project_dir / "config.yaml"
    if cfg_path.exists():
        cfg_txt = cfg_path.read_text()
        m = re.search(r'^\s*cv:\s*(.+)', cfg_txt, re.MULTILINE) or \
            re.search(r'^\s*cv_path:\s*(.+)', cfg_txt, re.MULTILINE)
        if m:
            cv_val = m.group(1).strip().strip("\"'")
            if cv_val.startswith("http"):
                pass  # URL — always ok
            else:
                cv_abs = (project_dir / cv_val).resolve()
                if not cv_abs.exists():
                    return False, (
                        f"CV file not found: {cv_val}\n"
                        "Call the 'setup' tool with cv_path or cv_content parameter."
                    )

    return True, "ok"


def _not_configured_response(message: str) -> str:
    return json.dumps({
        "status": "needs_setup",
        "message": message,
        "next_step": (
            "Call the 'setup' tool to configure JobRadar. "
            "Example: setup({\"api_key\": \"ARK_API_KEY=xxx\", \"cv_path\": \"/path/to/cv.pdf\"})"
        ),
        "setup_command": "jobradar init",
        "install_url": "https://github.com/jason-huanghao/jobradar",
    }, ensure_ascii=False, indent=2)



# ── Setup tool (no server needed) ─────────────────────────────────

def _handle_setup(params: dict) -> str:
    """Configure JobRadar with minimal user interaction.

    Agent flow:
    1. Call setup({}) FIRST — returns detected config + prompt_for_user to show user
    2. Show user the prompt_for_user string (one message — not multiple questions)
    3. Apply any changes the user requests in a single follow-up call
    4. Once configured=True, call run_pipeline({"mode": "quick"})

    Parameters (all optional):
        check_only: bool  — report state only, no writes (default: False)
        api_key: str      — "ENV_VAR=value", e.g. "ARK_API_KEY=abc123"
        cv_path: str      — local path (.md/.pdf/.docx/.txt) or URL (GitHub blob URLs supported)
        cv_content: str   — raw CV text pasted directly
        locations: str    — comma-separated e.g. "Berlin,Hamburg,Remote"
                           default: Germany-wide (all major cities + Remote)
    """
    project_dir = _find_project_dir()
    if project_dir is None:
        # Use agents skills dir if available, else create in ~/.openclaw/skills
        candidates = [
            Path.home() / ".agents" / "skills" / "jobradar",
            Path.home() / ".openclaw" / "skills" / "jobradar",
        ]
        project_dir = next((p for p in candidates if p.exists()), candidates[0])
        project_dir.mkdir(parents=True, exist_ok=True)

    check_only = params.get("check_only", False)
    cfg_path = project_dir / "config.yaml"

    # ── Detect current state ───────────────────────────────────────
    var, base_url, model = _detect_api_key()

    current_cv = None
    cv_exists = False
    if cfg_path.exists():
        cfg_txt = cfg_path.read_text()
        # Support both new `cv:` and legacy `cv_path:` keys
        m = re.search(r'^\s*cv:\s*(.+)', cfg_txt, re.MULTILINE) or \
            re.search(r'^\s*cv_path:\s*(.+)', cfg_txt, re.MULTILINE)
        if m:
            current_cv = m.group(1).strip().strip("\'\"")
            if current_cv and not current_cv.startswith("http"):
                cv_abs = (project_dir / current_cv).resolve()
                cv_exists = cv_abs.exists()
            elif current_cv.startswith("http"):
                cv_exists = True  # treat URL as always present

    current_locs = []
    if cfg_path.exists():
        cfg_content = cfg_path.read_text()
        # Extract only the locations block (between 'locations:' and the next top-level key)
        loc_block = re.search(r'locations:\s*\n((?:    - [^\n]+\n)*)', cfg_content)
        if loc_block:
            current_locs = re.findall(r'    - (.+)', loc_block.group(1))

    # Build human-readable summary
    detected = {
        "api_key": f"{var} (auto-detected from environment)" if var else "not found",
        "cv": (f"{current_cv} ({'found' if cv_exists else 'FILE MISSING'})"
               if current_cv else "not configured"),
        "locations": ", ".join(current_locs) if current_locs else "not configured",
        "project_dir": str(project_dir),
    }

    missing = []
    if not var:
        missing.append("api_key")
    if not cv_exists:
        missing.append("cv")

    # ── Build prompt_for_user — one message the agent shows user ──
    if not missing:
        prompt_for_user = (
            f"JobRadar is ready!\n"
            f"\u2022 API Key: {detected['api_key']}\n"
            f"\u2022 CV: {detected['cv']}\n"
            f"\u2022 Locations: {detected['locations']}\n"
            f"\nWould you like to change anything, or shall I run a quick job search now?"
        )
    elif missing == ["cv"]:
        prompt_for_user = (
            f"Almost ready! API key detected automatically ({var}).\n"
            f"Just need your CV. Please provide:\n"
            f"\u2022 A file path: /path/to/cv.pdf (or .md, .docx, .txt)\n"
            f"\u2022 A URL: https://github.com/.../cv.md\n"
            f"\u2022 Paste your CV text directly"
        )
    elif missing == ["api_key"]:
        prompt_for_user = (
            f"Almost ready! CV found: {current_cv}\n"
            f"Just need an LLM API key:\n"
            f"\u2022 Volcengine Ark: ARK_API_KEY=your_key\n"
            f"\u2022 Z.AI (Claude): ZAI_API_KEY=your_key\n"
            f"\u2022 OpenAI: OPENAI_API_KEY=your_key"
        )
    else:
        prompt_for_user = (
            "Quick setup needed:\n"
            "1. Your CV (file path, URL, or paste text)\n"
            "2. An LLM API key (ARK_API_KEY, ZAI_API_KEY, OPENAI_API_KEY, etc.)\n"
            "Reply with both and I'll configure everything at once."
        )

    if check_only:
        return json.dumps({
            "status": "configured" if not missing else "needs_setup",
            "detected": detected,
            "missing": missing,
            "prompt_for_user": prompt_for_user,
        }, ensure_ascii=False, indent=2)

    # ── Apply changes ──────────────────────────────────────────────
    results: dict = {"project_dir": str(project_dir), "detected": detected}

    # Ensure config.yaml exists
    if not cfg_path.exists():
        example = project_dir / "config.example.yaml"
        if example.exists():
            import shutil as _shutil
            _shutil.copy(example, cfg_path)
        else:
            cfg_path.write_text(_MINIMAL_CONFIG)
        results["config"] = "created"

    # API key
    if "api_key" in params:
        raw_key = params["api_key"].strip()
        if "=" in raw_key:
            env_var, _, val = raw_key.partition("=")
            env_var, val = env_var.strip(), val.strip()
            env_file = project_dir / ".env"
            existing = env_file.read_text().splitlines() if env_file.exists() else []
            lines = [l for l in existing if not l.startswith(env_var)]
            lines.append(f"{env_var}={val}")
            env_file.write_text("\n".join(lines) + "\n")
            os.environ[env_var] = val
            var, _, _ = _detect_api_key()
            if env_var in _PROVIDER_MAP:
                base_url_p, model_p = _PROVIDER_MAP[env_var]
                txt2 = cfg_path.read_text()
                txt2 = re.sub(r'api_key_env:.*', f'api_key_env: {env_var}', txt2)
                txt2 = re.sub(r'base_url: https?://\S+', f'base_url: {base_url_p}', txt2)
                cfg_path.write_text(txt2)
            results["api_key"] = f"{env_var} saved"
    elif var:
        results["api_key"] = f"{var} auto-detected"

    # CV
    cv_dir = project_dir / "cv"
    cv_dir.mkdir(exist_ok=True)

    if "cv_content" in params:
        cv_text = params["cv_content"].strip()
        dest = cv_dir / "cv_current.md"
        dest.write_text(cv_text, encoding="utf-8")
        txt2 = cfg_path.read_text()
        txt2 = re.sub(r'^\s*cv_path:.*', 'candidate:\n  cv: ./cv/cv_current.md', txt2, flags=re.MULTILINE)
        txt2 = re.sub(r'^\s*cv:\s*.*', '  cv: ./cv/cv_current.md', txt2, flags=re.MULTILINE)
        cfg_path.write_text(txt2)
        results["cv"] = f"saved from text ({len(cv_text)} chars)"
        cv_exists = True

    elif "cv_path" in params:
        src = params["cv_path"].strip()
        # Convert GitHub blob URL to raw
        if "github.com" in src and "/blob/" in src:
            src = src.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        if src.startswith("http"):
            try:
                resp = httpx.get(src, follow_redirects=True, timeout=30)
                resp.raise_for_status()
                ext = ".pdf" if "pdf" in resp.headers.get("content-type", "") else ".md"
                dest = cv_dir / f"cv_current{ext}"
                dest.write_bytes(resp.content)
                txt2 = cfg_path.read_text()
                txt2 = re.sub(r'^\s*(cv|cv_path):.*', f'  cv: ./cv/cv_current{ext}', txt2, flags=re.MULTILINE)
                cfg_path.write_text(txt2)
                results["cv"] = f"downloaded → cv/cv_current{ext}"
                cv_exists = True
            except Exception as e:
                results["cv_error"] = str(e)
        else:
            src_path = Path(src).expanduser().resolve()
            if src_path.exists():
                import shutil as _shutil
                ext = src_path.suffix.lower() or ".md"
                dest = cv_dir / f"cv_current{ext}"
                try:
                    rel = str(src_path.relative_to(project_dir))
                    results["cv"] = f"in project: ./{rel}"
                except ValueError:
                    _shutil.copy2(src_path, dest)
                    results["cv"] = f"copied → cv/cv_current{ext}"
                txt2 = cfg_path.read_text()
                cv_rel = f"./cv/cv_current{ext}"
                txt2 = re.sub(r'^\s*(cv|cv_path):.*', f'  cv: {cv_rel}', txt2, flags=re.MULTILINE)
                cfg_path.write_text(txt2)
                cv_exists = True
            else:
                results["cv_error"] = f"not found: {src}"

    # Locations
    if "locations" in params:
        locs = [l.strip() for l in params["locations"].split(",") if l.strip()]
        new_locs = "\n".join(f"    - {l}" for l in locs)
        txt2 = cfg_path.read_text()
        txt2 = re.sub(r'locations:\s*\n(\s+-[^\n]*\n)+', f'locations:\n{new_locs}\n', txt2)
        cfg_path.write_text(txt2)
        results["locations"] = locs
    else:
        # Apply Germany-wide defaults unless already set to real cities
        # Use scoped regex to read ONLY the locations block (not exclude_keywords)
        txt2 = cfg_path.read_text()
        loc_block_m = re.search(r'locations:\s*\n((?:    - [^\n]+\n)*)', txt2)
        current_loc_list = re.findall(r'    - (.+)', loc_block_m.group(1)) if loc_block_m else []
        # Apply defaults if empty or only has the placeholder "Germany"
        if not current_loc_list or current_loc_list == ["Germany"]:
            new_locs = "\n".join(f"    - {l}" for l in _DEFAULT_LOCATIONS)
            txt2 = re.sub(r'locations:\s*\n((?:    - [^\n]+\n)*)',
                          f'locations:\n{new_locs}\n', txt2)
            cfg_path.write_text(txt2)
            results["locations"] = _DEFAULT_LOCATIONS
        else:
            results["locations"] = current_loc_list

    # Always read back final locations from config to ensure result is accurate
    try:
        cfg_content = cfg_path.read_text()
        loc_block = re.search(r'locations:\s*\n((?:    - [^\n]+\n)*)', cfg_content)
        if loc_block:
            final_locs = re.findall(r'    - (.+)', loc_block.group(1))
            if final_locs:
                results["locations"] = final_locs  # always overwrite with ground truth
    except Exception:
        pass

    # ── Final status ───────────────────────────────────────────────
    var2, _, _ = _detect_api_key()
    cv_m = re.search(r'^\s*cv:\s*(.+)', cfg_path.read_text(), re.MULTILINE) or \
           re.search(r'^\s*cv_path:\s*(.+)', cfg_path.read_text(), re.MULTILINE)
    cv_final_ok = False
    if cv_m:
        cv_val = cv_m.group(1).strip().strip("'\"")
        if cv_val.startswith("http"):
            cv_final_ok = True
        else:
            cv_abs = (project_dir / cv_val).resolve()
            cv_final_ok = cv_abs.exists()

    configured = bool(var2 and cv_final_ok)
    missing2 = ([" api_key"] if not var2 else []) + (["cv"] if not cv_final_ok else [])

    if configured:
        final_prompt = (
            f"\u2705 JobRadar is configured and ready!\n"
            f"\u2022 API Key: {var2} (auto-detected)\n"
            f"\u2022 CV: {cv_m.group(1).strip() if cv_m else 'set'}\n"
            f"\u2022 Locations: Germany-wide ({len(_DEFAULT_LOCATIONS)} cities + Remote)\n"
            f"\nShall I run a quick job search now? "
            f"(I'll call run_pipeline and show you the top matches)"
        )
    else:
        final_prompt = f"Still need: {', '.join(missing2)}. Please provide them."

    results.update({
        "configured": configured,
        "missing": missing2,
        "prompt_for_user": final_prompt,
        "status": "setup_complete" if configured else "setup_partial",
    })
    return json.dumps(results, ensure_ascii=False, indent=2)


# ── Server lifecycle ───────────────────────────────────────────────

def ensure_server_running(host: str, port: int, timeout: int = 20) -> bool:
    global _SERVER_PROC
    base_url = f"http://{host}:{port}"
    try:
        httpx.get(f"{base_url}/api/pipeline/status", timeout=2).raise_for_status()
        return True
    except Exception:
        pass

    jobradar_bin = _find_jobradar_bin()
    if jobradar_bin:
        _SERVER_PROC = subprocess.Popen(
            [jobradar_bin, "web", "--no-browser"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    else:
        _SERVER_PROC = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "jobradar.api.main:create_app",
             "--factory", "--host", host, "--port", str(port), "--log-level", "error"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            httpx.get(f"{base_url}/api/pipeline/status", timeout=1).raise_for_status()
            return True
        except Exception:
            time.sleep(0.5)
    return False


def _find_jobradar_bin() -> str | None:
    venv_bin = Path(sys.executable).parent / "jobradar"
    if venv_bin.exists():
        return str(venv_bin)
    result = subprocess.run(["which", "jobradar"], capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None


# ── Skill HTTP tools ───────────────────────────────────────────────

class JobRadarSkill:
    def __init__(self):
        # Load config from detected project dir
        project_dir = _find_project_dir()
        if project_dir:
            os.chdir(project_dir)
        from ..config import load_config
        cfg = load_config()
        self.host = cfg.server.host
        self.port = cfg.server.port
        self.base_url = f"http://{self.host}:{self.port}"
        ensure_server_running(self.host, self.port)

    def handle(self, tool_name: str, params: dict) -> str:
        handlers = {
            "run_pipeline":         self._run_pipeline,
            "list_jobs":            self._list_jobs,
            "get_job_detail":       self._get_job_detail,
            "generate_application": self._generate_application,
            "get_digest":           self._get_digest,
            "get_report":           self._get_report,
            "apply_jobs":           self._apply_jobs,
            "get_status":           self._get_status,
        }
        fn = handlers.get(tool_name)
        if not fn:
            return json.dumps({"error": f"Unknown tool: {tool_name}",
                               "available": list(handlers)})
        return fn(params)

    def _run_pipeline(self, p: dict) -> str:
        resp = httpx.post(f"{self.base_url}/api/pipeline/run",
                          json={"mode": p.get("mode", "quick")}, timeout=300)
        return resp.text

    def _list_jobs(self, p: dict) -> str:
        params = {k: v for k, v in {"min_score": p.get("min_score", 6),
                                     "source": p.get("source", ""),
                                     "limit": p.get("limit", 20)}.items()
                  if v is not None and v != ""}
        return httpx.get(f"{self.base_url}/api/jobs", params=params, timeout=30).text

    def _get_job_detail(self, p: dict) -> str:
        jid = p.get("job_id", "")
        if not jid:
            return json.dumps({"error": "job_id is required"})
        return httpx.get(f"{self.base_url}/api/jobs/{jid}", timeout=15).text

    def _generate_application(self, p: dict) -> str:
        jid = p.get("job_id", "")
        if not jid:
            return json.dumps({"error": "job_id is required"})
        return httpx.post(f"{self.base_url}/api/generate/application/{jid}", timeout=120).text

    def _get_digest(self, p: dict) -> str:
        return httpx.get(f"{self.base_url}/api/outputs/digest",
                         params={"min_score": p.get("min_score", 6)}, timeout=30).text

    def _get_report(self, p: dict) -> str:
        """Generate HTML report and optionally publish to GitHub Pages."""
        import json as _json
        from pathlib import Path as _Path
        try:
            project_dir = _find_project_dir()
            from ..config import load_config
            cfg = load_config()
            db_path = cfg.resolve_path(cfg.server.db_path)
            from ..report.generator import generate_report, jobs_from_db
            min_score = float(p.get("min_score", 0))
            jobs = jobs_from_db(db_path, min_score=min_score)
            if not jobs:
                return _json.dumps({"error": "No scored jobs found. Run the pipeline first."})
            report_dir = cfg.resolve_path(cfg.report.report_dir)
            report_dir.mkdir(parents=True, exist_ok=True)
            import hashlib as _hashlib
            h = _hashlib.sha256(f"{min_score}{len(jobs)}".encode()).hexdigest()[:8]
            output_path = report_dir / f"report-{h}.html"
            report_path = generate_report(jobs, output_path=output_path)
            result = {"report_path": str(report_path), "job_count": len(jobs)}
            if p.get("publish", False):
                from ..report.publisher import publish_to_github_pages
                url = publish_to_github_pages(report_path, repo_dir=project_dir)
                result["url"] = url
                result["message"] = f"Report published: {url}"
            else:
                result["message"] = f"Report saved locally: {report_path}"
            return _json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            return _json.dumps({"error": str(exc)})



    def _get_status(self, _p: dict) -> str:
        return httpx.get(f"{self.base_url}/api/pipeline/status", timeout=10).text

    def _apply_jobs(self, p: dict) -> str:
        """Apply to top-scoring jobs. dry_run=True by default for safety."""
        import json as _json
        try:
            from ..config import load_config
            from ..apply.engine import run_apply
            cfg = load_config()
            db_path = cfg.resolve_path(cfg.server.db_path)
            min_score = float(p.get("min_score", cfg.scoring.auto_apply_min_score))
            dry_run = bool(p.get("dry_run", True))   # safe default
            platforms = p.get("platforms", ["bosszhipin", "linkedin"])
            if isinstance(platforms, str):
                platforms = [x.strip() for x in platforms.split(",")]
            session = run_apply(
                db_path=db_path,
                min_score=min_score,
                dry_run=dry_run,
                confirm_each=False,
                daily_limit=int(p.get("daily_limit", 50)),
                platforms=platforms,
            )
            return _json.dumps({
                "summary": session.summary,
                "applied": len(session.applied),
                "dry_run": dry_run,
                "results": [
                    {"job_id": r.job_id, "title": r.title,
                     "company": r.company, "status": r.status.value,
                     "message": r.message}
                    for r in session.results
                ],
            }, ensure_ascii=False)
        except Exception as exc:
            return _json.dumps({"error": str(exc)})


# ── Main entry point ───────────────────────────────────────────────

def run_skill(tool_name: str, params_json: str | dict = "{}") -> str:
    """Entry point called by OpenClaw. Always returns valid JSON, never raises."""
    try:
        # Accept both str and dict for params (agents sometimes pass dicts directly)
        if isinstance(params_json, dict):
            params = params_json
        else:
            params = json.loads(params_json) if params_json else {}

        # 'setup' tool is handled without requiring a running server or full config
        if tool_name == "setup":
            return _handle_setup(params)

        # All other tools require configuration
        ok, message = _is_configured()
        if not ok:
            return _not_configured_response(message)

        skill = JobRadarSkill()
        return skill.handle(tool_name, params)

    except Exception as exc:
        return json.dumps({
            "error": str(exc),
            "tip": "Run 'jobradar health' to diagnose, or call setup({}) to reconfigure.",
        }, ensure_ascii=False)


# ── Minimal fallback config ────────────────────────────────────────

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
  db_path: ./jobradar.db
  cache_dir: ./cache
"""


if __name__ == "__main__":
    tool = sys.argv[1] if len(sys.argv) > 1 else "get_status"
    params = sys.argv[2] if len(sys.argv) > 2 else "{}"
    print(run_skill(tool, params))
