"""Database session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from pathlib import Path

from .models import Base

_engine = None
_SessionLocal = None


def init_db(db_path: str):
    """Initialize the database."""
    global _engine, _SessionLocal

    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    _engine = create_engine(f"sqlite:///{db_path}", echo=False)
    _SessionLocal = sessionmaker(bind=_engine)

    # Create tables
    Base.metadata.create_all(_engine)

    return _engine


@contextmanager
def get_session():
    """Get a database session as a context manager."""
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
