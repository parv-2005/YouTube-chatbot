"""
Database Session Configuration
==============================
Sets up SQLAlchemy to connect to PostgreSQL.

SQLAlchemy uses two main concepts:
1. Engine — the actual connection pool to the database
2. Session — a "workspace" for querying/modifying data

Each API request gets its own Session (via the get_db dependency),
ensuring that database operations are isolated between requests.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings


# ── Engine ───────────────────────────────────────────────────
# The engine manages a pool of database connections.
# pool_pre_ping=True: checks if connections are alive before using them,
# preventing "connection closed" errors after idle periods.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# ── Session Factory ──────────────────────────────────────────
# SessionLocal is a factory — calling SessionLocal() creates a new session.
# autocommit=False: we manually commit transactions
# autoflush=False: we manually flush changes to the database
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ── Base Class ───────────────────────────────────────────────
# All ORM models inherit from this Base class.
# It provides the mapping between Python classes and SQL tables.
Base = declarative_base()


def create_tables():
    """
    Create all database tables defined in models.py.

    This is a development convenience — in production,
    you would use a migration tool like Alembic.

    IMPORTANT: This must be called AFTER all models are imported,
    so SQLAlchemy knows about them.
    """
    # Import models here to ensure they're registered with Base
    from app.database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
