"""
Rangroop API — FastAPI Application
====================================
Single-endpoint pipeline that chains Phase 1 (skin tone analysis) and
Phase 2 (palette lookup) and Phase 3 (clothing matching) and returns a combined JSON result.

How to run:
uvicorn app.main:app --reload --port 8000
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analyze import router as analyze_router

app = FastAPI(
    title="Rangroop API",
    description="Skin tone analysis and clothing palette recommendation API.",
    version="0.1.0",
)

# Allow any localhost / 127.0.0.1 port so a dev React frontend can call freely.
_CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://localhost:5174,http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:5174",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}

app.include_router(analyze_router)
