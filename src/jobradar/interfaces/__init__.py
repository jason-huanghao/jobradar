"""Interfaces package — CLI and OpenClaw skill."""

from .cli import app as cli_app
from .skill import JobRadarSkill, run_skill

__all__ = ["cli_app", "JobRadarSkill", "run_skill"]
