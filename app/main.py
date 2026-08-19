# app/main.py

import logging
from os import getenv
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging_config import setup_logging
from app.database.base import Base  # noqa: F401
from app.database.session import engine  # noqa: F401


# =============================================================================
# Logging
# =============================================================================

setup_logging()
logger = logging.getLogger(__name__)


# =============================================================================
# Import database models
#
# این importها برای ثبت مدل‌ها در metadata و Alembic autogenerate ضروری هستند.
# =============================================================================

from app.models.user import User  # noqa: E402, F401
from app.models.doctor import Doctor, Specialty  # noqa: E402, F401
from app.models.availability import Availability  # noqa: E402, F401
from app.models.consultation import ConsultationRequest  # noqa: E402, F401
from app.models.otp import OTPVerification  # noqa: E402, F401
from app.models.appointment import Appointment  # noqa: E402, F401
from app.models.wallet import Wallet, Transaction  # noqa: E402, F401

# Doctor billing / finance models
from app.models.doctor_wallet import (  # noqa: E402, F401
    DoctorWallet,
    DoctorWalletTransaction,
)
from app.models.doctor_billing import (  # noqa: E402, F401
    SubscriptionPlan,
    DoctorSubscription,
    PromotionPackage,
    DoctorPromotion,
)


# =============================================================================
# Import routers
# =============================================================================

from app.api.routes.appointments import router as appointments_router  # noqa: E402
from app.api.routes.auth import router as auth_router  # noqa: E402
from app.api.routes.availability import router as availability_router  # noqa: E402
from app.api.routes.consultations import router as consultations_router  # noqa: E402
from app.api.routes.doctors import router as doctors_router  # noqa: E402
from app.api.routes.specialties import router as specialties_router  # noqa: E402
from app.api.routes.wallet import router as wallet_router  # noqa: E402
from app.api.routes.doctor_wallet import router as doctor_wallet_router  # noqa: E402


# =============================================================================
# Application configuration
# =============================================================================

API_PREFIX = "/api/v1"

app = FastAPI(
    title="DocTime API",
    description="Doctor Appointment Management System",
    version="1.0.0",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    openapi_url=f"{API_PREFIX}/openapi.json",
)


# =============================================================================
# CORS Configuration
# =============================================================================

# توجه:
# localhost و 127.0.0.1 دو Origin متفاوت هستند و باید هر دو جداگانه ثبت شوند.
allowed_origins = [
    # Local development
    "http://localhost:5173",
    "http://127.0.0.1:5173",

    # Vercel deployments
    "https://doctime-frontend-sadegh-bs-projects.vercel.app",
    "https://doctime-frontend-bbzcqsquj-sadegh-bs-projects.vercel.app",
    "https://doctime-frontend-omega.vercel.app",
    "https://doctime-frontend.vercel.app",
    "https://doctime-frontend-git-main-sadegh-bs-projects.vercel.app",
    "https://doctime-frontend-6ieh9w4y0-sadegh-bs-projects.vercel.app",
]


# افزودن آدرس فرانت‌اند از Environment Variables در Render
frontend_url = getenv("FRONTEND_URL", "").strip().rstrip("/")

if frontend_url and frontend_url not in allowed_origins:
    allowed_origins.append(frontend_url)


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "PATCH",
        "OPTIONS",
    ],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)


# =============================================================================
# Exception handlers
# =============================================================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """
    پاسخ استاندارد برای خطاهای HTTP مانند 401، 403، 404 و 500.

    این Handler باعث می‌شود پاسخ خطا نیز JSON معتبر داشته باشد
    و Middleware مربوط به CORS بتواند هدرهای لازم را اضافه کند.
    """

    logger.warning(
        "HTTP error: method=%s path=%s status=%s detail=%s",
        request.method,
        request.url.path,
        exc.status_code,
        exc.detail,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
        },
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    مدیریت خطاهای اعتبارسنجی Pydantic/FastAPI.
    """

    logger.warning(
        "Validation error: method=%s path=%s errors=%s",
        request.method,
        request.url.path,
        exc.errors(),
    )

    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    مدیریت خطاهای پیش‌بینی‌نشده.

    logger.exception مهم است، چون Stack Trace کامل را در لاگ Render ثبت می‌کند.
    کاربر فقط پیام عمومی دریافت می‌کند و جزئیات داخلی سیستم افشا نمی‌شود.
    """

    logger.exception(
        "Unhandled server exception: method=%s path=%s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "خطای داخلی سرور رخ داده است.",
        },
    )


# =============================================================================
# Health endpoints
# =============================================================================

@app.get("/", tags=["Health"])
def root() -> dict[str, str]:
    return {
        "status": "online",
        "message": "DocTime API is running",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "doctime-backend",
    }


# =============================================================================
# API routers registration
# =============================================================================

app.include_router(
    auth_router,
    prefix=API_PREFIX,
)

app.include_router(
    doctors_router,
    prefix=API_PREFIX,
)

app.include_router(
    specialties_router,
    prefix=API_PREFIX,
)

app.include_router(
    appointments_router,
    prefix=API_PREFIX,
)

app.include_router(
    availability_router,
    prefix=API_PREFIX,
)

app.include_router(
    consultations_router,
    prefix=API_PREFIX,
)

app.include_router(
    wallet_router,
    prefix=API_PREFIX,
)

app.include_router(
    doctor_wallet_router,
    prefix=API_PREFIX,
)


# =============================================================================
# Application lifecycle
# =============================================================================

@app.on_event("startup")
def on_startup() -> None:
    logger.info("DocTime API started successfully.")
    logger.info("Allowed CORS origins: %s", allowed_origins)


@app.on_event("shutdown")
def on_shutdown() -> None:
    logger.info("DocTime API stopped.")
