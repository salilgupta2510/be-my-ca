"""
GST Engine API — standalone FastAPI service.

Start:
    uvicorn api.main:app --reload --port 8001

Environment:
    GST_ENGINE_API_KEYS   comma-separated valid keys (omit = dev mode, no auth)
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import core, gstr, rcm, risk, fuzzy
from engine.rules_loader import get_rules


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-load default rule bundle at startup to avoid cold-start latency
    get_rules()
    yield


app = FastAPI(
    title="GST Engine API",
    description=(
        "Indian GST law engine — CGST Act 2017 rules, returns computation, "
        "ITC set-off (Section 49), RCM (Section 9(3)), late fees (Section 47), "
        "ITC eligibility (Sections 16 & 17(5))."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — tighten in production via GST_ENGINE_ALLOWED_ORIGINS env var
_origins_raw = os.environ.get("GST_ENGINE_ALLOWED_ORIGINS", "*")
_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# ── Routers ──────────────────────────────────────────────────────────────────

app.include_router(core.router, tags=["Core GST"])
app.include_router(gstr.router, tags=["GSTR Returns"])
app.include_router(rcm.router, tags=["RCM"])
app.include_router(risk.router, tags=["Risk"])
app.include_router(fuzzy.router, tags=["Fuzzy Match"])


# ── Health & Info ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["Meta"])
def health() -> dict:
    rules = get_rules()
    return {
        "status": "ok",
        "rules_version": rules.folder,
        "rules_effective_date": rules.effective_date.isoformat(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/", tags=["Meta"])
def root() -> dict:
    return {
        "service": "gst-engine",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
