import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.database import Base, engine, SessionLocal
from app.routers import (
    auth, cases, dashboard, export, chat, network,
    audit, offenders, analytics, finance, masters,
    fir, collaboration, notifications
)
from app.routers import admin as admin_router
from app.routers import import_csv
from app import models, auth as app_auth
from app.limiter import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables and seed demo RBAC users instantly on startup."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.User).filter(models.User.email == "admin@crimeintel.local").first() is None:
            admin_user = models.User(
                name="Admin User (DGP Office)",
                email="admin@crimeintel.local",
                hashed_password=app_auth.hash_password("Admin@123"),
                role=models.RoleEnum.admin,
            )
            analyst_user = models.User(
                name="Lead Analyst Priya",
                email="analyst@crimeintel.local",
                hashed_password=app_auth.hash_password("Analyst@123"),
                role=models.RoleEnum.analyst,
            )
            investigator_user = models.User(
                name="Inspector K. Sharma",
                email="investigator@crimeintel.local",
                hashed_password=app_auth.hash_password("Investigator@123"),
                role=models.RoleEnum.investigator,
            )
            viewer_user = models.User(
                name="Junior Duty Officer",
                email="viewer@crimeintel.local",
                hashed_password=app_auth.hash_password("Viewer@123"),
                role=models.RoleEnum.viewer,
            )
            db.add_all([admin_user, analyst_user, investigator_user, viewer_user])
            db.commit()
            print("--> Seeded default demo RBAC users (Admin@123).")
    except Exception as e:
        print(f"--> Demo user seed notice: {e}")
    finally:
        db.close()
    yield


app = FastAPI(title="Crime Intelligence Platform API", version="0.4.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(dashboard.router)
app.include_router(export.router)
app.include_router(chat.router)
app.include_router(network.router)
app.include_router(audit.router)
app.include_router(admin_router.router)
app.include_router(import_csv.router)
app.include_router(offenders.router)
app.include_router(analytics.router)
app.include_router(finance.router)
app.include_router(masters.router)
app.include_router(fir.router)
app.include_router(collaboration.router)
app.include_router(notifications.router)


@app.get("/")
@app.get("/health")
@app.get("/api/health")
def health():
    return {"status": "ok", "message": "CrimeIntel Platform Online"}
