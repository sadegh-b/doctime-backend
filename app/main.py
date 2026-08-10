# مسیر قرارگیری فایل: backend/app/main.py

import logging
from os import getenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.core.logging_config import setup_logging

# 1. تنظیم و پیکربندی سیستم لاگینگ متمرکز (کنسول + فایل)
setup_logging()
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Import database models before Base.metadata.create_all().
# تمام ایمپورت‌ها صریح و بدون بلاک‌های try-except پنهان‌کننده خطا نوشته شده‌اند.
# -----------------------------------------------------------------------------

from app.models.user import User  # noqa: F401
from app.models.doctor import Doctor, Specialty  # noqa: F401
from app.models.availability import Availability  # noqa: F401
from app.models.consultation import ConsultationRequest  # noqa: F401
from app.models.otp import OTPVerification  # noqa: F401
from app.models.appointment import Appointment  # noqa: F401
from app.models.wallet import Wallet, Transaction  # noqa: F401

# اگر ماژول Review در کل سیستم وجود ندارد یا حذف شده است،
# خط زیر و روت مربوط به آن در پایین فایل باید کامنت یا حذف شوند.
try:
    from app.models.review import Review  # noqa: F401
except ImportError:
    logger.warning("Warning: app.models.review could not be imported. Ensure the file exists.")

# -----------------------------------------------------------------------------
# Routers
# -----------------------------------------------------------------------------

from app.api.routes.appointments import router as appointments_router
from app.api.routes.auth import router as auth_router
from app.api.routes.availability import router as availability_router
from app.api.routes.consultations import router as consultations_router
from app.api.routes.doctors import router as doctors_router
from app.api.routes.specialties import router as specialties_router
from app.api.routes.wallet import router as wallet_router

# برای جلوگیری از کرش در صورت نبودن روت کامنت‌ها (Reviews)
try:
    from app.api.routes.reviews import router as reviews_router
    HAS_REVIEWS = True
except ImportError:
    logger.warning("Warning: app.api.routes.reviews could not be imported.")
    HAS_REVIEWS = False

API_PREFIX = "/api/v1"

app = FastAPI(
    title="DocTime API",
    description="Doctor Appointment Management System",
    version="1.0.0",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    openapi_url=f"{API_PREFIX}/openapi.json",
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Health endpoints
# -----------------------------------------------------------------------------

@app.get("/", tags=["Health"], summary="API root endpoint")
def root() -> dict[str, str]:
    return {
        "status": "online",
        "message": "DocTime API is running successfully",
        "version": "1.0.0",
        "docs": f"{API_PREFIX}/docs",
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
# API routers
# -----------------------------------------------------------------------------

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(doctors_router, prefix=API_PREFIX)
app.include_router(specialties_router, prefix=API_PREFIX)
app.include_router(appointments_router, prefix=API_PREFIX)
app.include_router(availability_router, prefix=API_PREFIX)
app.include_router(consultations_router, prefix=API_PREFIX)
app.include_router(wallet_router, prefix=API_PREFIX)

if HAS_REVIEWS:
    app.include_router(reviews_router, prefix=API_PREFIX)
else:
    logger.warning("Skipping reviews_router registration due to import failure.")


# -----------------------------------------------------------------------------
# Lifecycle
# -----------------------------------------------------------------------------

@app.on_event("startup")
def on_startup() -> None:
    logger.info("Creating database tables if they do not exist...")
    Base.metadata.create_all(bind=engine)

    logger.info("DocTime API started successfully.")
    logger.info("API prefix: %s", API_PREFIX)
    logger.info("Allowed CORS origins: %s", allowed_origins)


@app.on_event("shutdown")
def on_shutdown() -> None:
    logger.info("DocTime API stopped.")
