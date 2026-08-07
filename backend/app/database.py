import os
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

raw_db_url = os.getenv("DATABASE_URL", "").strip()

tmp_db = os.path.join(tempfile.gettempdir(), "crime_intel.db")
default_sqlite = f"sqlite:///{tmp_db}"

DATABASE_URL = default_sqlite

if raw_db_url and not raw_db_url.startswith("sqlite"):
    try:
        # Test connection with a short 3s timeout before committing to engine
        test_engine = create_engine(raw_db_url, connect_args={"connect_timeout": 3})
        conn = test_engine.connect()
        conn.close()
        test_engine.dispose()
        DATABASE_URL = raw_db_url
        print(f"--> Successfully connected to external database: {DATABASE_URL}")
    except Exception as err:
        print(f"--> External DATABASE_URL unreachable ({err}). Falling back to SQLite: {default_sqlite}")
        DATABASE_URL = default_sqlite
elif raw_db_url and raw_db_url.startswith("sqlite"):
    if raw_db_url.startswith("sqlite:///./") or raw_db_url == "sqlite:///crime_intel.db":
        DATABASE_URL = default_sqlite
    else:
        DATABASE_URL = raw_db_url
else:
    DATABASE_URL = default_sqlite

print(f"--> Active Database URL: {DATABASE_URL}")

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
