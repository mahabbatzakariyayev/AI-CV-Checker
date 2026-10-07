from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exports import router as exports_router
from app.api.health import router as health_router
from app.api.screening_jobs import router as screening_jobs_router
from app.config import get_settings
from app.database import Base, engine
from app.utils.logging import configure_app_logging


def create_app() -> FastAPI:
    configure_app_logging()
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    Base.metadata.create_all(bind=engine)
    app.include_router(health_router)
    app.include_router(screening_jobs_router)
    app.include_router(exports_router)
    return app


app = create_app()
