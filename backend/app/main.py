from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import capture, chat, graph, memories, stats, topics
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.sqlite import initialize_database
from app.jobs.scheduler import build_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_database()
    logger.info("sqlite database initialized")
    scheduler = build_scheduler()
    if scheduler:
        scheduler.start()
        logger.info("scheduler started", extra={"jobs": [job.id for job in scheduler.get_jobs()]})
    try:
        yield
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)
            logger.info("scheduler stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled exception method=%s path=%s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(capture.router, prefix="/api")
    app.include_router(memories.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(graph.router, prefix="/api")
    app.include_router(topics.router, prefix="/api")
    app.include_router(stats.router, prefix="/api")
    return app


app = create_app()
