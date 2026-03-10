"""Install jobradar as a 7x24 background agent (launchd on macOS, cron on Linux).

Run via: jobradar --install-agent
         jobradar --uninstall-agent
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path


_LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
_PLIST_LABEL = "com.jobradar.agent"
_PLIST_PATH = _LAUNCH_AGENTS_DIR / f"{_PLIST_LABEL}.plist"
_CRON_MARKER = "# jobradar-agent"


def _get_python() -> str:
    """Return path to the current Python executable."""
    return sys.executable


def _get_project_root() -> Path:
    """Return the project root (parent of src/)."""
    return Path(__file__).parent.parent


def install_agent(run_hour: int = 8) -> None:
    """Install the daily agent scheduler."""
    system = platform.system()
    if system == "Darwin":
        _install_launchd(run_hour)
    elif system == "Linux":
        _install_cron(run_hour)
    else:
        print(f"⚠️  Unsupported OS: {system}")
        print("   Add this to your scheduler manually:")
        print(f"   {_get_python()} -m src.main --update")
        return


def uninstall_agent() -> None:
    """Remove the agent scheduler."""
    system = platform.system()
    if system == "Darwin":
        _uninstall_launchd()
    elif system == "Linux":
        _uninstall_cron()
    else:
        print(f"⚠️  Unsupported OS: {system}")


# ── macOS launchd ──────────────────────────────────────────────────

def _install_launchd(run_hour: int) -> None:
    python = _get_python()
    project_root = _get_project_root()
    log_path = project_root / "memory" / "agent.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{_PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>-m</string>
        <string>src.main</string>
        <string>--update</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{project_root}</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{run_hour}</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    <key>StandardErrorPath</key>
    <string>{log_path}</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
"""
    _LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    _PLIST_PATH.write_text(plist, encoding="utf-8")

    # Load into launchd
    try:
        subprocess.run(["launchctl", "unload", str(_PLIST_PATH)], capture_output=True)
        result = subprocess.run(
            ["launchctl", "load", str(_PLIST_PATH)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"✅  Agent installed (macOS launchd)")
            print(f"   Runs daily at {run_hour:02d}:00")
            print(f"   Log: {log_path}")
            print(f"   Plist: {_PLIST_PATH}")
        else:
            print(f"⚠️  launchctl load returned: {result.stderr}")
            print(f"   Plist written to {_PLIST_PATH} — load it manually with:")
            print(f"   launchctl load {_PLIST_PATH}")
    except FileNotFoundError:
        print(f"   Plist written to {_PLIST_PATH}")
        print("   Load it with: launchctl load " + str(_PLIST_PATH))


def _uninstall_launchd() -> None:
    if _PLIST_PATH.exists():
        subprocess.run(["launchctl", "unload", str(_PLIST_PATH)], capture_output=True)
        _PLIST_PATH.unlink()
        print("✅  Agent uninstalled (launchd plist removed)")
    else:
        print("ℹ️  No agent plist found at", _PLIST_PATH)


# ── Linux cron ────────────────────────────────────────────────────

def _install_cron(run_hour: int) -> None:
    python = _get_python()
    project_root = _get_project_root()
    log_path = project_root / "memory" / "agent.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    cron_line = (
        f"0 {run_hour} * * * cd {project_root} && "
        f"{python} -m src.main --update >> {log_path} 2>&1 "
        f"{_CRON_MARKER}"
    )

    # Read existing crontab
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ""

    # Remove old jobradar lines
    lines = [l for l in existing.splitlines() if _CRON_MARKER not in l]
    lines.append(cron_line)

    new_crontab = "\n".join(lines) + "\n"
    proc = subprocess.run(["crontab", "-"], input=new_crontab, text=True, capture_output=True)
    if proc.returncode == 0:
        print(f"✅  Agent installed (cron)")
        print(f"   Runs daily at {run_hour:02d}:00")
        print(f"   Log: {log_path}")
    else:
        print(f"⚠️  crontab install failed: {proc.stderr}")
        print(f"   Add this line manually to crontab -e:")
        print(f"   {cron_line}")


def _uninstall_cron() -> None:
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if result.returncode != 0:
        print("ℹ️  No crontab found.")
        return
    lines = [l for l in result.stdout.splitlines() if _CRON_MARKER not in l]
    new_crontab = "\n".join(lines) + "\n"
    subprocess.run(["crontab", "-"], input=new_crontab, text=True)
    print("✅  Agent uninstalled (cron entry removed)")
