import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from slowapi.errors import RateLimitExceeded

from app.database import Base, engine, SessionLocal
from app.routers import (
    auth, cases, dashboard, export, chat, network,
    audit, offenders, analytics, finance, masters,
    fir, collaboration, notifications, citizen_reports, activity, jobs, observability, workflows, career_plans
)
from app.routers import admin as admin_router
from app.routers import import_csv
from app import models, auth as app_auth
from app.limiter import limiter
from app.errors import AppException
from app.middleware import (
    RequestIDMiddleware, app_exception_handler, request_validation_exception_handler,
    http_exception_handler, rate_limit_exception_handler, db_exception_handler,
    global_exception_handler
)
from app.activity_logger import ActivityLoggingMiddleware


def migrate_db_schema():
    """Ensure newly added columns exist in SQLite/Postgres tables dynamically."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        if "cases" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("cases")]
            with engine.connect() as conn:
                if "investigation_label" not in columns:
                    conn.execute(text("ALTER TABLE cases ADD COLUMN investigation_label VARCHAR DEFAULT 'Unreviewed'"))
                if "investigator_note" not in columns:
                    conn.execute(text("ALTER TABLE cases ADD COLUMN investigator_note TEXT"))
                if "reviewer_id" not in columns:
                    conn.execute(text("ALTER TABLE cases ADD COLUMN reviewer_id VARCHAR"))
                if "reviewer_name" not in columns:
                    conn.execute(text("ALTER TABLE cases ADD COLUMN reviewer_name VARCHAR"))
                if "review_timestamp" not in columns:
                    conn.execute(text("ALTER TABLE cases ADD COLUMN review_timestamp DATETIME"))
                if "previous_investigation_label" not in columns:
                    conn.execute(text("ALTER TABLE cases ADD COLUMN previous_investigation_label VARCHAR"))
                conn.commit()
    except Exception as mig_err:
        print(f"--> DB Schema Migration Notice: {mig_err}")


def ensure_db_initialized():
    """Create DB tables and seed demo RBAC users & cases safely."""
    try:
        Base.metadata.create_all(bind=engine)
        migrate_db_schema()
        db = SessionLocal()
        try:
            if db.query(models.User).filter(models.User.email == "admin@crimeintel.local").first() is None:
                admin_user = models.User(
                    id="user-admin-demo-001",
                    name="Admin User (DGP Office)",
                    email="admin@crimeintel.local",
                    hashed_password=app_auth.hash_password("Admin@123"),
                    role=models.RoleEnum.admin,
                )
                analyst_user = models.User(
                    id="user-analyst-demo-001",
                    name="Lead Analyst Priya",
                    email="analyst@crimeintel.local",
                    hashed_password=app_auth.hash_password("Analyst@123"),
                    role=models.RoleEnum.analyst,
                )
                investigator_user = models.User(
                    id="user-investigator-demo-001",
                    name="Inspector K. Sharma",
                    email="investigator@crimeintel.local",
                    hashed_password=app_auth.hash_password("Investigator@123"),
                    role=models.RoleEnum.investigator,
                )
                viewer_user = models.User(
                    id="user-viewer-demo-001",
                    name="Junior Duty Officer",
                    email="viewer@crimeintel.local",
                    hashed_password=app_auth.hash_password("Viewer@123"),
                    role=models.RoleEnum.viewer,
                )
                db.add_all([admin_user, analyst_user, investigator_user, viewer_user])
                db.commit()

            if db.query(models.Case).first() is None:
                try:
                    from seed import seed_all
                    seed_all(db)
                except Exception as s_err:
                    print(f"--> Auto-seed cases notice: {s_err}")

            if db.query(models.CareerPlan).first() is None:
                try:
                    from seed import seed_career_plans
                    seed_career_plans(db)
                except Exception as cp_err:
                    print(f"--> Auto-seed career plans notice: {cp_err}")

            if db.query(models.Case).filter(models.Case.case_id == "CR-2026-9999").first() is None:
                try:
                    from seed import seed_sample_reviewed_case
                    seed_sample_reviewed_case(db)
                except Exception as sc_err:
                    print(f"--> Auto-seed sample case notice: {sc_err}")
        except Exception as seed_err:
            print(f"--> Demo user seed notice: {seed_err}")
        finally:
            db.close()
    except Exception as db_err:
        print(f"--> DB init notice: {db_err}")


# Ensure DB tables exist on import/serverless startup
ensure_db_initialized()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables and seed demo RBAC users safely on startup."""
    ensure_db_initialized()
    yield


app = FastAPI(title="Crime Intelligence Platform API", version="0.4.0", lifespan=lifespan)

app.state.limiter = limiter

# ── Middleware & Exception Handlers ──────────────────────────────────────────
app.add_middleware(ActivityLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
app.add_exception_handler(SQLAlchemyError, db_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(dashboard.router)
app.include_router(export.router)
app.include_router(chat.router)
app.include_router(network.router)
app.include_router(audit.router)
app.include_router(activity.router)
app.include_router(jobs.router)
app.include_router(observability.router)
app.include_router(workflows.router)
app.include_router(career_plans.router)
app.include_router(admin_router.router)
app.include_router(import_csv.router)
app.include_router(offenders.router)
app.include_router(analytics.router)
app.include_router(finance.router)
app.include_router(masters.router)
app.include_router(fir.router)
app.include_router(collaboration.router)
app.include_router(notifications.router)
app.include_router(citizen_reports.router)


@app.get("/")
@app.get("/health")
@app.get("/api/health")
def health():
    return {"status": "ok", "message": "CrimeIntel Platform Online"}
