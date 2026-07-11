# app/api/routes/availability.py
from datetime import datetime, timedelta, time as dtime

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
    # "arithmetic" تلفظ: اَرِثمِتیک = محاسبات
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

    start_dt = _time_to_dt(payload.start_time)
    end_dt = _time_to_dt(payload.end_time)
    duration = timedelta(minutes=payload.duration_minutes)

    if start_dt + duration > end_dt:
        raise HTTPException(
            status_code=400,
            detail="Time range is smaller than duration_minutes",
        )

    # Generate candidate slots
    candidate_slots: list[tuple[dtime, dtime]] = []
    cursor = start_dt
    while cursor + duration <= end_dt:
        s = cursor.time()
        e = (cursor + duration).time()
        candidate_slots.append((s, e))
        cursor += duration

    # Overlap check: we must ensure none of the candidate slots collide with existing slots
    # This is stricter than checking only the payload whole range.
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

        for it in items:
            db.refresh(it)

        return {
            "success": True,
            "count": len(items),
            "items": items,
        }
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create availability")
