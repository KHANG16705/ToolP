"""FastAPI application entry point for Batch Photo Enhancer (run with --workers 1)."""

from contextlib import asynccontextmanager
from typing import AsyncIterator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as enhance_router
from config import CORS_ORIGINS, TEMP_DIR
from services.batch_service import cleanup_expired_jobs


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Ensure temporary job directory exists on startup and clean stale jobs on shutdown."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_expired_jobs()
    yield
    cleanup_expired_jobs()


app = FastAPI(
    title="Batch Photo Enhancer API",
    description="Spatial-domain Digital Image Processing backend (FastAPI + NumPy + OpenCV).",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(enhance_router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Simple liveness endpoint for frontend connectivity and QA verification."""
    return {"status": "ok"}
