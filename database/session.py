from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from .config import DATABASE_URL, SQL_ECHO

Base = declarative_base()

engine = None
SessionLocal = None

# Only create engine if DATABASE_URL is valid
if DATABASE_URL:
    try:
        engine = create_engine(
            DATABASE_URL,
            echo=(SQL_ECHO or "false").lower() == "true"
        )
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
    except Exception as e:
        print(f"[WARNING] Database not initialized: {e}")
        engine = None
        SessionLocal = None


def get_db() -> Session:
    """Dependency for getting a database session in endpoints"""
    if SessionLocal is None:
        raise RuntimeError("Database is not configured")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()