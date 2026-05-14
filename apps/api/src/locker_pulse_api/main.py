from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from locker_pulse_api.config import get_settings
from locker_pulse_api.repositories.db import connect_database, disconnect_database
from locker_pulse_api.repositories.point_repository import PointRepository
from locker_pulse_api.routers import admin, geocode, health, history, points, reports


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    db = await connect_database(settings)
    app.state.point_repository = PointRepository(db)
    yield
    await disconnect_database(db)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(admin.router)
    app.include_router(geocode.router)
    app.include_router(history.router)
    app.include_router(reports.router)
    app.include_router(reports.analysis_router)
    app.include_router(points.router)
    return app


app = create_app()
