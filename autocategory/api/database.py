"""
Database connection and session management
"""
import logging
import time

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import os
from config import settings

# Get database URL from environment or config
DATABASE_URL = os.getenv("DATABASE_URL", settings.database_url)

logger = logging.getLogger(__name__)
_POOL_PRESSURE_LOG_INTERVAL_SECONDS = 30.0
_last_pool_pressure_warning_at = 0.0

# Keep the per-process pool bounded. With four Gunicorn workers, the defaults
# below allow at most 60 application connections in total, leaving PostgreSQL
# headroom for migrations, health checks and administrative access.
engine = create_engine(
    DATABASE_URL,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_pre_ping=True,
    pool_recycle=settings.db_pool_recycle,
    pool_use_lifo=True,
    echo=False  # Set to True for SQL debug logging
)


@event.listens_for(engine, "checkout")
def _track_connection_checkout(dbapi_connection, connection_record, connection_proxy):
    """Remember when a pooled connection starts being used."""
    global _last_pool_pressure_warning_at

    now = time.monotonic()
    connection_record.info["checkout_started_at"] = now
    capacity = engine.pool.size() + settings.db_max_overflow
    checked_out = engine.pool.checkedout()
    if (
        capacity
        and checked_out / capacity >= 0.8
        and now - _last_pool_pressure_warning_at >= _POOL_PRESSURE_LOG_INTERVAL_SECONDS
    ):
        _last_pool_pressure_warning_at = now
        logger.warning(
            "Database pool pressure is high: checked_out=%s capacity=%s",
            checked_out,
            capacity,
        )


@event.listens_for(engine, "checkin")
def _track_connection_checkin(dbapi_connection, connection_record):
    """Warn when application code held a connection for too long."""
    started_at = connection_record.info.pop("checkout_started_at", None)
    if started_at is None:
        return
    held_seconds = time.monotonic() - started_at
    if held_seconds >= settings.db_pool_warn_seconds:
        logger.warning(
            "Database connection was checked out for %.2fs (warn threshold=%ss)",
            held_seconds,
            settings.db_pool_warn_seconds,
        )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency for FastAPI endpoints to get database session
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_pool_status() -> dict:
    """Return QueuePool pressure without checking out another connection."""
    pool = engine.pool
    pool_size = pool.size()
    max_overflow = settings.db_max_overflow
    capacity = pool_size + max_overflow
    checked_out = pool.checkedout()
    return {
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "capacity": capacity,
        "checked_in": pool.checkedin(),
        "checked_out": checked_out,
        "overflow": max(0, pool.overflow()),
        "utilization": round(checked_out / capacity, 3) if capacity else 0.0,
    }


@contextmanager
def get_db_context():
    """
    Context manager for database session
    Usage: 
        with get_db_context() as db:
            # do something with db
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize database (create tables)
    Only for development/testing - use Alembic for production
    """
    Base.metadata.create_all(bind=engine)


def close_db():
    """
    Close database connections
    """
    engine.dispose()
