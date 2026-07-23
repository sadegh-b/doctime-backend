# app/main.py

import logging
from os import getenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ایمپورت کردن بیس دیتابیس برای ساختن جدول‌ها
from app.database.base import Base, engine

# ایمپورت دقیق مدل‌هایی که وجود آن‌ها قطعی است
from app.models.user import User  # noqa: F401
from app.models.doctor import Doctor  # noqa: F401
from app.models.availability import Availability  # noqa: F401

# مدل‌های زیر را با try-except لود می‌کنیم تا در صورت عدم وجود فیزیکی فایل، سرور کرش نکند
try:
    from app.models.appointment import Appointment  # noqa: F401
except ImportError:
    pass

try:
    from app.models.review import Review  # noqa: F401
except ImportError:
    pass

# ایمپورت راوترها
from app.api.routes.appointments import router as appointments_router
from app.api.routes.auth import router as auth_router
from app.api.routes.availability import router as availability_router
from app.api.routes.doctors import router as doctors_router
from app.api.routes.reviews import router as reviews_router

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

API_PREFIX = "/api/v1"

# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------

app = FastAPI(
    title="DocTime API",
    description="Doctor Appointment Management System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# -----------------------------------------------------------------------------
# CORS
# -----------------------------------------------------------------------------

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://doctime-frontend-omega.vercel.app",
]

frontend_url = getenv("FRONTEND_URL", "").strip().rstrip("/")

if frontend_url and frontend_url not in allowed_origins:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https://doctime-frontend[a-zA-Z0-9-]*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Root / Health
# -----------------------------------------------------------------------------

@app.get("/", tags=["Health"], summary="API root endpoint")
def root() -> dict[str, str]:
    return {
        "status": "online",
        "message": "DocTime API is running successfully",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"], summary="Application health check")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "doctime-backend",
        "version": "1.0.0",
    }


@app.get(f"{API_PREFIX}/health", tags=["Health"], summary="Versioned health check")
def versioned_health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "doctime-backend",
        "api_version": "v1",
    }


@app.get(API_PREFIX, tags=["Health"], summary="API v1 root")
def api_v1_root() -> dict[str, str]:
    return {
        "status": "online",
        "message": "DocTime API v1 is available",
        "api_version": "v1",
    }


# -----------------------------------------------------------------------------
# Routers
# -----------------------------------------------------------------------------

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(doctors_router, prefix=API_PREFIX)
app.include_router(appointments_router, prefix=API_PREFIX)
app.include_router(availability_router, prefix=API_PREFIX)
app.include_router(reviews_router, prefix=API_PREFIX)


# -----------------------------------------------------------------------------
# Lifecycle
# -----------------------------------------------------------------------------

@app.on_event("startup")
def on_startup() -> None:
    # ساختن تمام جدول‌ها در دیتابیس جدید
    logger.info("Creating database tables if not exist...")
    Base.metadata.create_all(bind=engine)

    logger.info("DocTime API started successfully.")
    logger.info("API prefix: %s", API_PREFIX)
    logger.info("Allowed CORS origins: %s", allowed_origins)


@app.on_event("shutdown")
def on_shutdown() -> None:
    logger.info("DocTime API stopped.")
