# Path: backend/app/schemas/availability.py

from datetime import date, time
from pydantic import BaseModel, ConfigDict, Field

class AvailabilityCreate(BaseModel):
    date: date
    start_time: time
    end_time: time
    duration_minutes: int = Field(default=30, ge=15, le=120)  # انتخاب بازه‌های ۱۵، ۳۰، ۴۵، ۶۰ و ...

    model_config = ConfigDict(from_attributes=True)


class AvailabilityBulkCreateResponse(BaseModel):
    success: bool
    count: int
    items: list

    model_config = ConfigDict(from_attributes=True)
