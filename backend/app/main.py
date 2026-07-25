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
from app import rag, models
from app.limiter import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables, auto-seed if empty, build RAG index."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        try:
            if db.query(models.User).count() == 0:
                print("--> Database empty. Running seed pipeline...")
                import subprocess
                subprocess.run(["python", "seed.py"], check=False)
                # Reconnect after seed
                db.close()
                db = SessionLocal()
        except Exception as se:
            print(f"--> Auto-seed notice: {se}")
        try:
            rag.build_index(db)
        except Exception as re:
            print(f"--> RAG build notice: {re}")
    finally:
        db.close()
    yield


app = FastAPI(title="Crime Intelligence Platform API", version="0.4.0", lifespan=lifespan)

# ── Rate limiter ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ─────────────────────────────────────────────────────────────────────
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

# If wildcard is set, allow all origins
if "*" in allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
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


@app.get("/api/health")
def health():
    return {"status": "ok"}
