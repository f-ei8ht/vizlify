from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.clients import router as clients_router
from app.api.me import router as account_router
from app.api.milestones import router as milestones_router
from app.api.projects import router as projects_router
from app.api.team import router as team_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.schemas.response import ApiResponse, success


def create_app() -> FastAPI:
    app = FastAPI(
        title="Vizlify API",
        version="0.1.0",
        summary="An AI agent that proposes; a human approves; PayPal executes.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    @app.get("/", tags=["system"])
    async def root() -> ApiResponse[dict[str, str]]:
        return success({"name": "Vizlify API", "version": "0.1.0", "docs": "/docs"})

    @app.get("/health", tags=["system"])
    async def health() -> ApiResponse[dict[str, str]]:
        return success({"status": "ok"})

    app.include_router(account_router)
    app.include_router(clients_router)
    app.include_router(projects_router)
    app.include_router(milestones_router)
    app.include_router(team_router)
    return app


app = create_app()
