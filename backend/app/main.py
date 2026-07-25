import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.database import Base, engine, SessionLocal
from app.routers import auth, cases, dashboard, export, chat, network, audit, offenders, analytics, finance, masters, fir, collaboration, notifications
from app.routers import admin as admin_router
from app.routers import import_csv
from app import rag
from app.limiter import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the RAG index once at startup; release resources on shutdown."""
    db = SessionLocal()
    try:
        rag.build_index(db)
    finally:
        db.close()
    yield


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Crime Intelligence Platform API", version="0.4.0", lifespan=lifespan)

# ── Rate limiter ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ─────────────────────────────────────────────────────────────────────
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

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
