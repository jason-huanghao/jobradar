"""Database engine, session factory, and Alembic-backed initialisation."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

from alembic import command
from alembic.config import Config
from sqlmodel import Session, create_engine

# Import all table models so SQLModel.metadata is populated.
from .models import (  # noqa: F401
    Application,
    Job,
    PipelineRun,
    Profile,
    Score,
    User,
)

_engines: dict[str, object] = {}
_REPO_ROOT = Path(__file__).resolve().parents[3]   # .../jobradar
_ALEMBIC_INI = _REPO_ROOT / "alembic.ini"


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
    """Create/upgrade the schema by running Alembic migrations to head."""
    path = Path(db_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_REPO_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    command.upgrade(cfg, "head")


def get_session(db_path: str | Path = "./jobradar.db") -> Generator[Session, None, None]:
    with Session(get_engine(Path(db_path).resolve())) as session:
        yield session
