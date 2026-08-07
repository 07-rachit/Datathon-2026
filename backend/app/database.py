import os
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Read DATABASE_URL or default to /tmp/ for container write access
raw_db_url = os.getenv("DATABASE_URL", "sqlite:////tmp/crime_intel.db")

# Force writable /tmp/ directory for SQLite in container environments
if raw_db_url.startswith("sqlite:///./") or raw_db_url == "sqlite:///crime_intel.db":
    tmp_db = os.path.join(tempfile.gettempdir(), "crime_intel.db")
    DATABASE_URL = f"sqlite:///{tmp_db}"
else:
    DATABASE_URL = raw_db_url

print(f"--> Using Database URL: {DATABASE_URL}")

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
