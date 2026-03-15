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

    # 3. Default install location ~/.jobradar
    default = Path.home() / ".jobradar"
    if default.exists():
        return default.resolve()

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
    for search_dir in [Path.cwd(), Path.home() / ".jobradar"]:
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
        import re
        match = re.search(r'cv_path:\s*(.+)', cfg_path.read_text())
        if match:
            cv_rel = match.group(1).strip().strip("\"'")
            cv_abs = (project_dir / cv_rel).resolve()
            if not cv_abs.exists():
                return False, (
                    f"CV file not found: {cv_rel}\n"
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
    """Configure JobRadar in-process — no running server required.

    Accepts:
        api_key: "ENV_VAR=value" e.g. "ARK_API_KEY=abc123"
        cv_path: local file path or URL
        cv_content: raw CV text (Markdown)
        locations: "Berlin,Hannover,Remote"
        check_only: bool — just report status without modifying anything
    """
    results: dict[str, Any] = {}

    # Find or create project dir
    project_dir = _find_project_dir()
    if project_dir is None:
        project_dir = Path.home() / ".jobradar"
        project_dir.mkdir(parents=True, exist_ok=True)

    results["project_dir"] = str(project_dir)

    # ── config.yaml ───────────────────────────────────────────────
    cfg_path = project_dir / "config.yaml"
    if not cfg_path.exists():
        example = project_dir / "config.example.yaml"
        if example.exists():
            import shutil
            shutil.copy(example, cfg_path)
        else:
            cfg_path.write_text(_MINIMAL_CONFIG)
        results["config"] = "created"
    else:
        results["config"] = "exists"

    # ── API key ───────────────────────────────────────────────────
    if params.get("check_only"):
        var, base_url, model = _detect_api_key()
        results["api_key_detected"] = var or "none"
    elif "api_key" in params:
        raw = params["api_key"].strip()
        if "=" in raw:
            env_var, _, val = raw.partition("=")
            env_var, val = env_var.strip(), val.strip()
            # Write to .env
            env_file = project_dir / ".env"
            existing_lines = env_file.read_text().splitlines() if env_file.exists() else []
            lines = [l for l in existing_lines if not l.startswith(env_var)]
            lines.append(f"{env_var}={val}")
            env_file.write_text("\n".join(lines) + "\n")
            # Also set in current process for immediate use
            os.environ[env_var] = val
            results["api_key"] = f"{env_var} saved"
            # Update config.yaml to match provider
            if env_var in _PROVIDER_MAP:
                base_url, model = _PROVIDER_MAP[env_var]
                import re
                txt = cfg_path.read_text()
                txt = re.sub(r'api_key_env:.*', f'api_key_env: {env_var}', txt)
                txt = re.sub(r'base_url:.*ark.*|base_url:.*openai.*|base_url:.*z\.ai.*|base_url:.*deepseek.*|base_url:.*anthropic.*|base_url:.*openrouter.*',
                             f'base_url: {base_url}', txt)
                cfg_path.write_text(txt)
        else:
            results["api_key_warning"] = "Format should be ENV_VAR=value"
    else:
        # Try to auto-detect
        var, _, _ = _detect_api_key()
        results["api_key_detected"] = var or "none — provide via api_key parameter"

    # ── CV ────────────────────────────────────────────────────────
    cv_dir = project_dir / "cv"
    cv_dir.mkdir(exist_ok=True)

    if "cv_content" in params:
        # Raw text provided
        cv_text = params["cv_content"].strip()
        dest = cv_dir / "cv_current.md"
        dest.write_text(cv_text, encoding="utf-8")
        import re
        txt = cfg_path.read_text()
        txt = re.sub(r'cv_path:.*', 'cv_path: ./cv/cv_current.md', txt)
        cfg_path.write_text(txt)
        results["cv"] = f"saved ({len(cv_text)} chars) → cv/cv_current.md"

    elif "cv_path" in params:
        src = params["cv_path"].strip()
        if src.startswith("http://") or src.startswith("https://"):
            try:
                resp = httpx.get(src, follow_redirects=True, timeout=30)
                resp.raise_for_status()
                ext = ".pdf" if "pdf" in resp.headers.get("content-type", "") else ".md"
                dest = cv_dir / f"cv_current{ext}"
                dest.write_bytes(resp.content)
                import re
                txt = cfg_path.read_text()
                txt = re.sub(r'cv_path:.*', f'cv_path: ./cv/cv_current{ext}', txt)
                cfg_path.write_text(txt)
                results["cv"] = f"downloaded → cv/cv_current{ext}"
            except Exception as e:
                results["cv_error"] = str(e)
        else:
            src_path = Path(src).expanduser().resolve()
            if src_path.exists():
                import shutil, re
                ext = src_path.suffix.lower() or ".md"
                dest = cv_dir / f"cv_current{ext}"
                try:
                    dest.relative_to(project_dir)
                    rel = str(dest.relative_to(project_dir))
                except ValueError:
                    shutil.copy2(src_path, dest)
                    rel = f"cv/cv_current{ext}"
                txt = cfg_path.read_text()
                txt = re.sub(r'cv_path:.*', f'cv_path: ./{rel}', txt)
                cfg_path.write_text(txt)
                results["cv"] = f"copied → {rel}"
            else:
                results["cv_error"] = f"File not found: {src}"

    # ── Locations ─────────────────────────────────────────────────
    if "locations" in params:
        import re
        locs = [l.strip() for l in params["locations"].split(",") if l.strip()]
        new_locs = "\n".join(f"    - {l}" for l in locs)
        txt = cfg_path.read_text()
        txt = re.sub(r'locations:\s*\n(\s+-[^\n]*\n)+', f'locations:\n{new_locs}\n', txt)
        cfg_path.write_text(txt)
        results["locations"] = locs

    # ── Health check ──────────────────────────────────────────────
    ok, msg = _is_configured()
    results["configured"] = ok
    if not ok:
        results["next_step"] = msg
    else:
        results["next_step"] = (
            "Setup complete! Run the pipeline:\n"
            "  run_pipeline({\"mode\": \"quick\"})"
        )

    return json.dumps({"status": "setup_complete" if ok else "setup_partial",
                       **results}, ensure_ascii=False, indent=2)


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

    def _get_status(self, _p: dict) -> str:
        return httpx.get(f"{self.base_url}/api/pipeline/status", timeout=10).text


# ── Main entry point ───────────────────────────────────────────────

def run_skill(tool_name: str, params_json: str = "{}") -> str:
    """Entry point called by OpenClaw. Always returns valid JSON, never raises."""
    try:
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
llm:
  text:
    provider: volcengine
    model: doubao-seed-2.0-code
    base_url: https://ark.cn-beijing.volces.com/api/coding/v3
    api_key_env: ARK_API_KEY
    temperature: 0.3
    max_tokens: 4096
    rate_limit_delay: 2.0
candidate:
  cv_path: ./cv/cv_current.md
search:
  locations:
    - Berlin
    - Remote
  max_results_per_source: 50
  quick_max_results: 5
  max_days_old: 14
  exclude_keywords:
    - Praktikum
    - Werkstudent
    - internship
    - Ausbildung
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
scoring:
  min_score_application: 7.0
  batch_size: 5
server:
  host: 127.0.0.1
  port: 7842
  open_browser: true
  db_path: ./jobradar.db
  cache_dir: ./memory
"""


if __name__ == "__main__":
    tool = sys.argv[1] if len(sys.argv) > 1 else "get_status"
    params = sys.argv[2] if len(sys.argv) > 2 else "{}"
    print(run_skill(tool, params))
