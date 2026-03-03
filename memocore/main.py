"""
main.py — FastAPI application entry point.

Architecture decision: We use the modern `lifespan` context manager (Python
3.10+) instead of the deprecated @app.on_event decorators. It gives clear
startup/shutdown semantics and works correctly with ASGI test clients.

Startup sequence:
  1. Initialise the database (create tables in dev mode)
  2. Start the background scheduler

Shutdown sequence (reversed):
  1. Stop the scheduler
  2. SQLAlchemy connection pool is disposed automatically by the engine

The application is exposed as `app` so it can be run with:
    uvicorn memocore.main:app --reload
"""

import logging
import logging.config
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from memocore.config import get_settings
from memocore.database import init_db
from memocore.routers.webhook import router as webhook_router
from memocore.scheduler import start_scheduler, stop_scheduler

# ------------------------------------------------------------------ #
# Logging configuration
# ------------------------------------------------------------------ #
LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        # Suppress overly verbose SQLAlchemy engine logs unless in DEBUG mode
        "sqlalchemy.engine": {"level": "WARNING", "propagate": True},
        "apscheduler": {"level": "INFO", "propagate": True},
        "httpx": {"level": "WARNING", "propagate": True},
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)
settings = get_settings()


# ------------------------------------------------------------------ #
# Lifespan
# ------------------------------------------------------------------ #
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup → yield (app running) → Shutdown."""
    logger.info("Starting %s…", settings.APP_NAME)

    # Initialise database tables
    await init_db()
    logger.info("Database initialised.")

    # Start the background reminder scheduler
    start_scheduler()

    yield  # <-- application is live here

    # Graceful shutdown
    stop_scheduler()
    logger.info("%s shut down cleanly.", settings.APP_NAME)


# ------------------------------------------------------------------ #
# Application factory
# ------------------------------------------------------------------ #
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A production-ready personal AI assistant that manages your calendar "
        "and tasks via a WhatsApp-style webhook interface."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — restrict in production to your actual frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------ #
# Routers
# ------------------------------------------------------------------ #
app.include_router(webhook_router)


# ------------------------------------------------------------------ #
# Global exception handler
# ------------------------------------------------------------------ #
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected internal error occurred."},
    )


@app.get("/", tags=["Root"])
async def root() -> dict:
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
    }
