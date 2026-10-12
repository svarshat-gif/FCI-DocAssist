from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.init_db import init_db
from routers import auth, chat, circulars, health, uploads, maintenance
from scheduler.jobs import shutdown_scheduler, start_scheduler
from utils.config import get_settings
from utils.logging import configure_logging

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    if settings.environment == "production" and (len(settings.jwt_secret) < 32 or "replace" in settings.jwt_secret or "change-me" in settings.jwt_secret):
        raise RuntimeError("Set JWT_SECRET to a randomly generated secret of at least 32 characters.")
    init_db()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Find circulars, ask questions, and revisit your saved FCI document conversations.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(circulars.router, prefix=settings.api_prefix)
app.include_router(uploads.router, prefix=settings.api_prefix)
app.include_router(maintenance.router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "ready"}
