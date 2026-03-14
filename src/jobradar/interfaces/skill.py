"""OpenClaw skill handler — wraps JobRadar API for use as an OpenClaw skill.

When JobRadar runs as an OpenClaw skill, this module:
  1. Starts the FastAPI server on-demand if not already running.
  2. Translates OpenClaw tool_call invocations into API requests.
  3. Returns structured responses that OpenClaw can display.

OpenClaw will invoke this via the entry point defined in SKILL.md.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from ..config import load_config

_SERVER_PROC: subprocess.Popen | None = None


def ensure_server_running(host: str, port: int, timeout: int = 15) -> bool:
    """Start the FastAPI server if not already responding. Returns True on success."""
    global _SERVER_PROC
    base_url = f"http://{host}:{port}"

    # Check if already up
    try:
        httpx.get(f"{base_url}/api/pipeline/status", timeout=2).raise_for_status()
        return True
    except Exception:
        pass

    # Start it
    _SERVER_PROC = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "jobradar.api.main:create_app",
         "--factory", "--host", host, "--port", str(port), "--log-level", "error"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    # Wait for it to come up
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            httpx.get(f"{base_url}/api/pipeline/status", timeout=1).raise_for_status()
            return True
        except Exception:
            time.sleep(0.5)
    return False


class JobRadarSkill:
    """OpenClaw-compatible skill interface."""

    def __init__(self):
        cfg = load_config()
        self.host = cfg.server.host
        self.port = cfg.server.port
        self.base_url = f"http://{self.host}:{self.port}"
        ensure_server_running(self.host, self.port)

    def handle(self, tool_name: str, params: dict[str, Any]) -> str:
        """Route an OpenClaw tool_call to the appropriate API endpoint."""
        handlers = {
            "run_pipeline":        self._run_pipeline,
            "list_jobs":           self._list_jobs,
            "get_job_detail":      self._get_job_detail,
            "generate_application": self._generate_application,
            "get_digest":          self._get_digest,
            "get_status":          self._get_status,
        }
        fn = handlers.get(tool_name)
        if not fn:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        return fn(params)

    def _run_pipeline(self, p):
        mode = p.get("mode", "quick")
        resp = httpx.post(f"{self.base_url}/api/pipeline/run",
                          json={"mode": mode}, timeout=300)
        return resp.text

    def _list_jobs(self, p):
        params = {k: v for k, v in {
            "min_score": p.get("min_score", 6),
            "source": p.get("source", ""),
            "limit": p.get("limit", 20),
        }.items() if v}
        resp = httpx.get(f"{self.base_url}/api/jobs", params=params, timeout=30)
        return resp.text

    def _get_job_detail(self, p):
        job_id = p.get("job_id", "")
        resp = httpx.get(f"{self.base_url}/api/jobs/{job_id}", timeout=15)
        return resp.text

    def _generate_application(self, p):
        job_id = p.get("job_id", "")
        resp = httpx.post(f"{self.base_url}/api/generate/application/{job_id}", timeout=120)
        return resp.text

    def _get_digest(self, p):
        min_score = p.get("min_score", 6)
        resp = httpx.get(f"{self.base_url}/api/outputs/digest",
                         params={"min_score": min_score}, timeout=30)
        return resp.text

    def _get_status(self, _p):
        resp = httpx.get(f"{self.base_url}/api/pipeline/status", timeout=10)
        return resp.text


# ── Entry point called by OpenClaw ─────────────────────────────────

def run_skill(tool_name: str, params_json: str) -> str:
    """Main entry point for OpenClaw invocation."""
    try:
        params = json.loads(params_json) if params_json else {}
        skill = JobRadarSkill()
        return skill.handle(tool_name, params)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


if __name__ == "__main__":
    # Allow direct invocation: python -m jobradar.interfaces.skill <tool> <params_json>
    import sys
    tool = sys.argv[1] if len(sys.argv) > 1 else "get_status"
    params = sys.argv[2] if len(sys.argv) > 2 else "{}"
    print(run_skill(tool, params))
