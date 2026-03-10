"""
Field Sales CRM — FastAPI Application

AI-powered mobile CRM for field sales teams.
Runs on the owner's Windows laptop with SQLite.

Usage:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Field Sales CRM",
    description=(
        "AI-powered CRM for field sales teams. "
        "Automatically transcribes visit conversations and fills CRM fields."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow mobile app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/", tags=["health"])
async def root():
    return {
        "app": "Field Sales CRM",
        "version": "0.1.0",
        "database": settings.database_path,
        "status": "running",
    }


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}
