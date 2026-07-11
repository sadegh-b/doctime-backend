from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_user, get_db
from app.models.appointment import Appointment
from app.models.availability import Availability
from app.models.doctor import Doctor
from app.models.user import User

# صادق دقت کن: prefix را اینجا گذاشتم تا با main.py هماهنگ باشد
router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post("/book/{slot_id}", status_code=status.HTTP_201_CREATED)
def book_appointment(
        slot_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """
    رزرو نوبت توسط بیمار
    """
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can book appointments",
        )

    slot = db.query(Availability).filter(Availability.id == slot_id).first()
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time slot not found",
        )

    if slot.is_booked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This slot is already booked",
        )

    # جلوگیری از رزرو تکراری (اختیاری ولی لازم برای امنیت)
    existing_appointment = db.query(Appointment).filter(
        Appointment.availability_id == slot.id
    ).first()

    if existing_appointment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An appointment already exists for this slot",
        )

    new_appointment = Appointment(
        doctor_id=slot.doctor_id,
        patient_id=current_user.id,
        availability_id=slot.id,
        status="confirmed",
    )

    try:
        slot.is_booked = True
        db.add(new_appointment)
        db.commit()
        db.refresh(new_appointment)
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database Error: {e}")  # برای دیباگ خودت
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during booking process",
        )

    return {
        "success": True,
        "message": "Appointment booked successfully",
        "appointment_id": new_appointment.id,
    }


@router.get("/me")
def get_my_appointments(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    Sadegh, this is the missing piece!
    نمایش نوبت‌های رزرو شده توسط بیمار لاگین شده
    """
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only patients can view their appointments",
        )

    appointments = (
        db.query(Appointment)
        .options(
            joinedload(Appointment.availability),
        )
        .filter(Appointment.patient_id == current_user.id)
        .order_by(Appointment.id.desc())
        .all()
    )

    return {
        "success": True,
        "count": len(appointments),
        "items": [
            {
                "id": appt.id,
                "status": appt.status,
                "doctor_id": appt.doctor_id,
                "time_slot": {
                    "id": appt.availability.id if appt.availability else None,
                    "start_time": appt.availability.start_time.isoformat() if appt.availability else None,
                    "end_time": appt.availability.end_time.isoformat() if appt.availability else None,
                },
            }
            for appt in appointments
        ],
    }


@router.get("/doctor")
def get_doctor_appointments(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    نمایش نوبت‌های مربوط به یک پزشک خاص
    """
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: doctors only",
        )

    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found",
        )

    appointments = (
        db.query(Appointment)
        .options(
            joinedload(Appointment.patient),
            joinedload(Appointment.availability),
        )
        .filter(Appointment.doctor_id == doctor.id)
        .order_by(Appointment.id.desc())
        .all()
    )

    return {
        "success": True,
        "count": len(appointments),
        "items": [
            {
                "id": appt.id,
                "status": appt.status,
                "patient": {
                    "id": appt.patient.id if appt.patient else None,
                    "name": appt.patient.name if appt.patient else None,
                },
                "time_slot": {
                    "id": appt.availability.id if appt.availability else None,
                    "start_time": appt.availability.start_time.isoformat() if appt.availability else None,
                    "end_time": appt.availability.end_time.isoformat() if appt.availability else None,
                },
            }
            for appt in appointments
        ],
    }
