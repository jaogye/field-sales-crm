"""
Field Sales CRM — FastAPI Application

AI-powered mobile CRM for field sales teams.
Runs on the owner's Windows laptop with SQLite.

Usage:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text

from app.core.config import settings
from app.core.database import engine, Base, async_session
from app.api.routes import router

logger = logging.getLogger(__name__)

_DEFAULT_SECRET = "change-this-to-a-random-string-in-production"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup checks + table creation."""
    # Refuse to start in production with the default secret key
    if not settings.debug and settings.secret_key == _DEFAULT_SECRET:
        raise RuntimeError(
            "SECRET_KEY must be changed before running in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    if settings.secret_key == _DEFAULT_SECRET:
        logger.warning(
            "WARNING: Using the default SECRET_KEY. "
            "Generate a secure key before going to production: "
            "python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migrate existing databases: add demo columns if missing
        for ddl in [
            "ALTER TABLE vendedores ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE vendedores ADD COLUMN demo_segundos_usados INTEGER NOT NULL DEFAULT 0",
        ]:
            try:
                await conn.execute(text(ddl))
            except Exception:
                pass  # Column already exists

    # Ensure the demo account exists
    await _ensure_demo_vendedor()

    yield
    await engine.dispose()


async def _ensure_demo_vendedor():
    """Create the demo vendedor + sample clients if they don't exist."""
    from app.models.models import Vendedor, Cliente
    from app.core.auth import hash_password

    async with async_session() as db:
        result = await db.execute(
            select(Vendedor).where(Vendedor.telefono == "0000000000")
        )
        if result.scalar_one_or_none():
            return  # Already exists

        demo = Vendedor(
            nombre="Demo Vendedor",
            telefono="0000000000",
            password_hash=hash_password("demo1234"),
            is_demo=True,
            demo_segundos_usados=0,
            zona="Demo",
            activo=True,
        )
        db.add(demo)

        # Add a handful of demo clients
        demo_clientes = [
            ("Ana García", "1111111111", "Brooklyn"),
            ("Carlos López", "2222222222", "Queens"),
            ("María Rodríguez", "3333333333", "Bronx"),
            ("José Martínez", "4444444444", "Manhattan"),
            ("Laura Torres", "5555555555", "Staten Island"),
        ]
        for nombre, tel, zona in demo_clientes:
            exists = await db.execute(select(Cliente).where(Cliente.telefono == tel))
            if not exists.scalar_one_or_none():
                db.add(Cliente(nombre_apellido=nombre, telefono=tel, zona=zona))

        await db.commit()
        logger.info("Demo account created: telefono=0000000000 / password=demo1234")


app = FastAPI(
    title="Field Sales CRM",
    description=(
        "AI-powered CRM for field sales teams. "
        "Automatically transcribes visit conversations and fills CRM fields."
    ),
    version="0.1.0",
    lifespan=lifespan,
    # Disable docs in production
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS — Bearer tokens are used, not cookies, so allow_credentials=False
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include API routes
app.include_router(router)


@app.get("/", tags=["health"])
async def root():
    return {
        "app": "Field Sales CRM",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}
