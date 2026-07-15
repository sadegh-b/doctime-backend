# app/api/routes/availability.py
from datetime import datetime, timedelta, time as dtime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.availability import Availability
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.availability import (
    AvailabilityBulkCreateResponse,
    AvailabilityCreate,
    AvailabilityResponse,
)

router = APIRouter(prefix="/availability", tags=["Availability"])


def _time_to_dt(t: dtime) -> datetime:
    # We only need a dummy date to do time arithmetic reliably.
    return datetime.combine(datetime(2000, 1, 1).date(), t)


@router.post(
    "",
    response_model=AvailabilityBulkCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_availability(
    payload: AvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can create availability")

    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="End time must be greater than start time")

    if payload.duration_minutes <= 0:
        raise HTTPException(status_code=400, detail="duration_minutes must be positive")

    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    # Generate candidate slots based on duration
    candidate_slots = []
    start_dt = _time_to_dt(payload.start_time)
    end_dt = _time_to_dt(payload.end_time)
    duration = timedelta(minutes=payload.duration_minutes)

    cursor = start_dt
    while cursor + duration <= end_dt:
        candidate_slots.append((cursor.time(), (cursor + duration).time()))
        cursor += duration

    # Overlap check
    existing = (
        db.query(Availability)
        .filter(
            Availability.doctor_id == doctor.id,
            Availability.date == payload.date,
        )
        .all()
    )

    def overlaps(a_start: dtime, a_end: dtime, b_start: dtime, b_end: dtime) -> bool:
        return a_start < b_end and a_end > b_start

    for s, e in candidate_slots:
        for ex in existing:
            if overlaps(s, e, ex.start_time, ex.end_time):
                raise HTTPException(
                    status_code=400,
                    detail="This time slot overlaps with an existing availability",
                )

    try:
        items: list[Availability] = []
        for s, e in candidate_slots:
            items.append(
                Availability(
                    doctor_id=doctor.id,
                    date=payload.date,
                    start_time=s,
                    end_time=e,
                    is_available=True,
                    is_booked=False,
                )
            )

        db.add_all(items)
        db.commit()
        for item in items:
            db.refresh(item)

        return {
            "success": True,
            "count": len(items),
            "items": items,
        }
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create availability")


@router.get("", status_code=status.HTTP_200_OK)
def get_availability(
    doctor_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get all availability slots.
    Optionally filter by doctor_id to get specific doctor's slots.
    """
    query = db.query(Availability)
    
    if doctor_id is not None:
        query = query.filter(Availability.doctor_id == doctor_id)
        
    slots = query.order_by(Availability.date.asc(), Availability.start_time.asc()).all()
    
    return {
        "success": True,
        "count": len(slots),
        "items": [
            {
                "id": slot.id,
                "doctor_id": slot.doctor_id,
                "date": slot.date.isoformat() if hasattr(slot.date, "isoformat") else str(slot.date),
                "start_time": slot.start_time.isoformat() if hasattr(slot.start_time, "isoformat") else str(slot.start_time),
                "end_time": slot.end_time.isoformat() if hasattr(slot.end_time, "isoformat") else str(slot.end_time),
                "is_available": slot.is_available,
                "is_booked": slot.is_booked
            }
            for slot in slots
        ]
    }
