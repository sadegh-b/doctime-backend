# app/models/__init__.py

from app.database.base import Base

from app.models.user import User
from app.models.doctor import Doctor
from app.models.availability import Availability
from app.models.appointment import Appointment

__all__ = [
    "Base",
    "User",
    "Doctor",
    "Availability",
    "Appointment",
]
