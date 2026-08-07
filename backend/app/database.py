import os
import tempfile
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

# Read DATABASE_URL or default to /tmp/ for container write access
raw_db_url = os.getenv("DATABASE_URL", "sqlite:////tmp/crime_intel.db")

# Normalize legacy postgres:// to postgresql:// for SQLAlchemy 2.0+ compatibility
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

# Force writable /tmp/ directory for SQLite in container environments
if raw_db_url.startswith("sqlite:///./") or raw_db_url == "sqlite:///crime_intel.db":
    tmp_db = os.path.join(tempfile.gettempdir(), "crime_intel.db")
    DATABASE_URL = f"sqlite:///{tmp_db}"
else:
    DATABASE_URL = raw_db_url

print(f"--> Using Database URL: {DATABASE_URL}")

engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL / Supabase pool configuration
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
