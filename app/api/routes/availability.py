# Path: backend/app/api/routes/availability.py

from datetime import date, datetime, time as dtime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.availability import Availability
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.availability import (
    AvailabilityBulkCreateResponse,
    AvailabilityCreate,
)

router = APIRouter(
    prefix="/availability",
    tags=["Availability"]
)


def _time_to_dt(t: dtime) -> datetime:
    return datetime.combine(
        datetime(2000, 1, 1).date(),
        t
    )


def get_doctor(
        db: Session,
        current_user: User
) -> Doctor:
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="فقط پزشکان مجاز به مدیریت زمان حضور هستند."
        )

    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.user_id == current_user.id
        )
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="پروفایل پزشک پیدا نشد."
        )

    return doctor


def check_slots_overlap(db: Session, doctor_id: int, target_date: date, start_time: dtime, end_time: dtime) -> bool:
    """
    اعتبارسنجی قوی برای جلوگیری از ثبت اسلات‌های دارای تداخل زمانی (Overlap)
    """
    overlapping_slot = db.query(Availability).filter(
        Availability.doctor_id == doctor_id,
        Availability.date == target_date,
        Availability.start_time < end_time,
        Availability.end_time > start_time
    ).first()

    return overlapping_slot is not None


def create_slots_for_range(
        db: Session,
        doctor_id: int,
        slot_date: date,
        start_time: dtime,
        end_time: dtime,
        slot_minutes: int = 30,
) -> int:
    """
    تابع همه‌کاره برای تولید اسلات‌ها و ذخیره در دیتابیس به همراه بررسی تداخل
    """
    current_datetime = datetime.combine(slot_date, start_time)
    end_datetime = datetime.combine(slot_date, end_time)
    duration = timedelta(minutes=slot_minutes)
    created_count = 0

    while current_datetime + duration <= end_datetime:
        slot_start = current_datetime.time()
        slot_end = (current_datetime + duration).time()

        # بررسی عدم تداخل
        if not check_slots_overlap(db, doctor_id, slot_date, slot_start, slot_end):
            availability = Availability(
                doctor_id=doctor_id,
                date=slot_date,
                start_time=slot_start,
                end_time=slot_end,
                is_booked=False,
                is_available=True
            )
            db.add(availability)
            created_count += 1

        current_datetime += duration

    db.flush()
    return created_count


@router.post(
    "",
    response_model=AvailabilityBulkCreateResponse,
    status_code=status.HTTP_201_CREATED
)
def create_availability(
        payload: AvailabilityCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    doctor = get_doctor(db, current_user)

    if payload.end_time <= payload.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ساعت پایان باید بعد از ساعت شروع باشد."
        )

    # ایجاد اسلات‌ها به صورت داینامیک
    try:
        created_slots_count = create_slots_for_range(
            db=db,
            doctor_id=doctor.id,
            slot_date=payload.date,
            start_time=payload.start_time,
            end_time=payload.end_time,
            slot_minutes=payload.duration_minutes
        )

        db.commit()

        # واکشی اسلات‌های تازه ثبت شده برای بازگرداندن در خروجی
        new_slots = db.query(Availability).filter(
            Availability.doctor_id == doctor.id,
            Availability.date == payload.date
        ).order_by(Availability.start_time).all()

        return {
            "success": True,
            "count": created_slots_count,
            "items": new_slots
        }

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطای دیتابیس در هنگام ذخیره‌سازی بازه‌های زمانی."
        ) from exc


@router.get(
    "",
    status_code=status.HTTP_200_OK
)
def get_availability(
        doctor_id: Optional[int] = None,
        only_available: bool = False,
        db: Session = Depends(get_db)
):
    query = db.query(Availability)

    if doctor_id:
        query = query.filter(
            Availability.doctor_id == doctor_id
        )

    if only_available:
        query = query.filter(
            Availability.is_booked == False,
            Availability.is_available == True
        )

    slots = (
        query
        .order_by(
            Availability.date,
            Availability.start_time
        )
        .all()
    )

    return {
        "success": True,
        "count": len(slots),
        "items": [
            {
                "id": slot.id,
                "doctor_id": slot.doctor_id,
                "date": slot.date.isoformat(),
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time": slot.end_time.strftime("%H:%M"),
                "is_booked": slot.is_booked,
                "is_available": slot.is_available
            }
            for slot in slots
        ]
    }
