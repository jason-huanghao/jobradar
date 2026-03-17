"""Generator sub-module — CV optimization + cover letter."""

from .cover_letter import generate_cover_letter
from .cv_optimizer import optimize_cv

__all__ = ["optimize_cv", "generate_cover_letter"]
