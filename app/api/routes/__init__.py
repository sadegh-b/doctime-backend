# Path: app/api/routes/__init__.py

from fastapi import APIRouter
from app.api.routes import (
    auth,
    doctors,
    appointments,
    availability,
    reviews,
    consultations,
    specialties
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(doctors.router, prefix="/doctors", tags=["doctors"])
api_router.include_router(specialties.router, prefix="/specialties", tags=["specialties"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
api_router.include_router(availability.router, prefix="/availability", tags=["availability"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(consultations.router, prefix="/consultations", tags=["consultations"])
