import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Defaults to local SQLite for easy dev. Swap DATABASE_URL to a Postgres URL
# (e.g. postgresql+psycopg2://user:pass@host:5432/crime_intel) for production.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./crime_intel.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
