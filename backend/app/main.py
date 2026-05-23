"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import get_settings
from app.database import init_db
from app.seed import seed_demo_data

settings = get_settings()
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os

    if os.getenv("TESTING") != "1":
        init_db()
        seed_demo_data()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Платформа управления уязвимостями (вариант 4). NVD, CVSS, EPSS, инвентаризация ПО.",
    version=settings.API_VERSION,
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def web_ui():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "API running", "docs": f"{settings.API_PREFIX}/docs"}


@app.get("/health")
async def root_health():
    return {"status": "ok", "version": settings.API_VERSION}
