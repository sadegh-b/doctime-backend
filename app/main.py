import logging
from os import getenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# اصلاح مسیر دیتابیس: Base معمولاً در base.py و engine در session.py است
from app.database.base import Base
from app.database.session import engine
from app.core.logging_config import setup_logging

# 1. تنظیم و پیکربندی سیستم لاگینگ متمرکز
setup_logging()
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Import database models before Base.metadata.create_all().
# -----------------------------------------------------------------------------

from app.models.user import User  # noqa: F401
from app.models.doctor import Doctor, Specialty  # noqa: F401
from app.models.availability import Availability  # noqa: F401
from app.models.consultation import ConsultationRequest  # noqa: F401
from app.models.otp import OTPVerification  # noqa: F401
from app.models.appointment import Appointment  # noqa: F401
from app.models.wallet import Wallet, Transaction  # noqa: F401

# --- Doctor billing / finance models ---
from app.models.doctor_wallet import DoctorWallet, DoctorWalletTransaction  # noqa: F401
from app.models.doctor_billing import (  # noqa: F401
    SubscriptionPlan,
    DoctorSubscription,
    PromotionPackage,
    DoctorPromotion,
)

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

# --- Doctor finance router ---
from app.api.routes.doctor_wallet import router as doctor_wallet_router

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
# CORS Configuration
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
    # allows any Vercel preview/deployment of doctime-frontend
    allow_origin_regex=r"^https://doctime-frontend.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Health endpoints
# -----------------------------------------------------------------------------

@app.get("/", tags=["Health"])
def root():
    return {"status": "online", "message": "DocTime API is running", "version": "1.0.0"}

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "doctime-backend"}

# -----------------------------------------------------------------------------
# API routers registration
# -----------------------------------------------------------------------------

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(doctors_router, prefix=API_PREFIX)
app.include_router(specialties_router, prefix=API_PREFIX)
app.include_router(appointments_router, prefix=API_PREFIX)
app.include_router(availability_router, prefix=API_PREFIX)
app.include_router(consultations_router, prefix=API_PREFIX)
app.include_router(wallet_router, prefix=API_PREFIX)
app.include_router(doctor_wallet_router, prefix=API_PREFIX)

# -----------------------------------------------------------------------------
# Lifecycle events
# -----------------------------------------------------------------------------

@app.on_event("startup")
def on_startup():
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("DocTime API started successfully.")

@app.on_event("shutdown")
def on_shutdown():
    logger.info("DocTime API stopped.")
