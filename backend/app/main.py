from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.routes import calendar, demo, health, playbook, trace
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="EarningsPulse — AI agent for pre-earnings research and scenario playbooks.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(demo.router, prefix="/api")
    app.include_router(playbook.router, prefix="/api")
    app.include_router(calendar.router, prefix="/api")
    app.include_router(trace.router, prefix="/api")

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()
