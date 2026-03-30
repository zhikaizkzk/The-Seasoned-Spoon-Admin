from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from .config import DATABASE_URL, SQL_ECHO

# Create database engine
engine = create_engine(DATABASE_URL, echo=SQL_ECHO.lower() == "true")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db() -> Session:
    """Dependency for getting a database session in endpoints"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
