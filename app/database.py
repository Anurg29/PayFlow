"""
PayFlow — Database Engine.

Supports BOTH SQLite (local dev) and PostgreSQL (production).
Set DATABASE_URL in .env:
  Local:  sqlite:///./payflow.db
  Prod:   postgresql://user:pass@host:5432/payflow_db

Render provides DATABASE_URL starting with 'postgres://' — we auto-fix that
to 'postgresql://' which SQLAlchemy 2.x requires.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./payflow.db")

# ── Render Fix: postgres:// → postgresql:// ───────────────────────────────────
# Render (and Heroku) provide URLs starting with 'postgres://' but
# SQLAlchemy 2.x only accepts 'postgresql://'.
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "postgres://", "postgresql://", 1
    )

# ── Engine configuration ──────────────────────────────────────────────────────
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    # SQLite: needs check_same_thread=False for FastAPI's threaded requests
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL: connection pool tuning for production
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=10,           # maintain 10 connections
        max_overflow=20,        # allow up to 20 extra under load
        pool_pre_ping=True,     # verify connections are alive before use
        pool_recycle=300,       # recycle connections every 5 min
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session, auto-closes after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
