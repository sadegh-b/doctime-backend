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
):
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=403,
            detail="Only doctors can manage availability"
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
            status_code=404,
            detail="Doctor profile not found"
        )

    return doctor



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

    doctor = get_doctor(
        db,
        current_user
    )


    if payload.end_time <= payload.start_time:
        raise HTTPException(
            status_code=400,
            detail="End time must be greater than start time"
        )


    if payload.duration_minutes <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid duration"
        )


    start_dt = _time_to_dt(
        payload.start_time
    )

    end_dt = _time_to_dt(
        payload.end_time
    )


    duration = timedelta(
        minutes=payload.duration_minutes
    )


    slots = []

    cursor = start_dt


    while cursor + duration <= end_dt:

        slots.append(
            (
                cursor.time(),
                (cursor + duration).time()
            )
        )

        cursor += duration



    existing = (
        db.query(Availability)
        .filter(
            Availability.doctor_id == doctor.id,
            Availability.date == payload.date
        )
        .all()
    )



    def overlap(
        a_start,
        a_end,
        b_start,
        b_end
    ):
        return (
            a_start < b_end
            and
            a_end > b_start
        )


    for s,e in slots:

        for old in existing:

            if overlap(
                s,
                e,
                old.start_time,
                old.end_time
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Slot already exists"
                )



    try:

        items=[]


        for s,e in slots:

            item = Availability(
                doctor_id=doctor.id,
                date=payload.date,
                start_time=s,
                end_time=e,
                is_available=True,
                is_booked=False
            )

            items.append(item)



        db.add_all(items)

        db.commit()


        for item in items:
            db.refresh(item)



        return {
            "success":True,
            "count":len(items),
            "items":items
        }



    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Database error"
        )





@router.get(
    "",
    status_code=status.HTTP_200_OK
)
def get_availability(
    doctor_id: Optional[int] = None,
    only_available: bool = False,
    db: Session = Depends(get_db)
):


    query = db.query(
        Availability
    )


    if doctor_id:

        query = query.filter(
            Availability.doctor_id == doctor_id
        )


    if only_available:

        query = query.filter(
            Availability.is_available == True,
            Availability.is_booked == False
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

        "success":True,

        "count":len(slots),

        "items":[

            {

                "id":slot.id,

                "doctor_id":slot.doctor_id,

                "date":
                    slot.date.isoformat(),

                "start_time":
                    slot.start_time.strftime(
                        "%H:%M"
                    ),

                "end_time":
                    slot.end_time.strftime(
                        "%H:%M"
                    ),

                "is_available":
                    slot.is_available,

                "is_booked":
                    slot.is_booked

            }

            for slot in slots

        ]

    }