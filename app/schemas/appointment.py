from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class AppointmentStatus(str, Enum):
    booked = "booked"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"


class AppointmentCreate(BaseModel):
    availability_id: int
    notes: str | None = None


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus


class PatientInfo(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DoctorInfo(BaseModel):
    id: int
    specialty: str
    city: str

    model_config = ConfigDict(from_attributes=True)


class AppointmentResponse(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    availability_id: int
    status: AppointmentStatus
    notes: str | None = None
    created_at: datetime

    patient: PatientInfo | None = None
    doctor: DoctorInfo | None = None

    model_config = ConfigDict(from_attributes=True)
