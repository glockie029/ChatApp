from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.endpoints.chat import router, unsafe_router
from core.config import settings
from db.base import Base
from db.session import engine


Base.metadata.create_all(bind=engine)


def create_app(enable_unsafe_routes: Optional[bool] = None) -> FastAPI:
    unsafe_routes_enabled = (
        settings.enable_unsafe_routes
        if enable_unsafe_routes is None
        else enable_unsafe_routes
    )

    app = FastAPI(
        title=settings.app_name,
        description="A small chat API designed for DevSecOps and CI/CD security practice.",
        version=settings.app_version,
    )
    app.state.unsafe_routes_enabled = unsafe_routes_enabled

    cors_origins = settings.cors_origin_list
    allow_all_origins = cors_origins == ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=not allow_all_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/")
    def read_root() -> dict[str, object]:
        return {
            "status": "ok",
            "message": "ChatApp DevSecOps API is running",
            "version": settings.app_version,
            "unsafe_routes_enabled": unsafe_routes_enabled,
            "docs": "/docs",
        }

    app.include_router(router)

    if unsafe_routes_enabled:
        app.include_router(unsafe_router)
    
    return app


app = create_app()
