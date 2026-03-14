"""Database engine, session factory, and initialisation."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

# Import all table models so SQLModel.metadata picks them up
from .models import (  # noqa: F401
    ApplicationRecord,
    Candidate,
    FeedbackRecord,
    Job,
    PipelineRun,
    ScoredJobRecord,
)

_engines: dict[str, object] = {}


def get_engine(db_path: str | Path = "./jobradar.db"):
    key = str(Path(db_path).resolve())
    if key not in _engines:
        _engines[key] = create_engine(
            f"sqlite:///{key}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
    return _engines[key]


def init_db(db_path: str | Path = "./jobradar.db") -> None:
    """Create all tables if they don't exist. Auto-creates parent dirs. Safe to call repeatedly."""
    path = Path(db_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(get_engine(path))


def get_session(db_path: str | Path = "./jobradar.db") -> Generator[Session, None, None]:
    """Yield a database session."""
    with Session(get_engine(Path(db_path).resolve())) as session:
        yield session
