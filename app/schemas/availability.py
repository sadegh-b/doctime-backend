# app/schemas/availability.py
from datetime import date, time
from pydantic import BaseModel, Field


class AvailabilityCreate(BaseModel):
    date: date
    start_time: time
    end_time: time
    duration_minutes: int = Field(default=15, ge=5, le=240)

    # English tip:
    # duration_minutes -> "duration" یعنی "مدت زمان"
    # Field constraints: ge=... (greater or equal) / le=... (less or equal)


class AvailabilityResponse(BaseModel):
    id: int
    doctor_id: int
    date: date
    start_time: time
    end_time: time
    is_available: bool
    is_booked: bool

    model_config = {"from_attributes": True}


class AvailabilityBulkCreateResponse(BaseModel):
    success: bool
    count: int
    items: list[AvailabilityResponse]
