from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_user, get_db
from app.models.appointment import Appointment
from app.models.availability import Availability
from app.models.doctor import Doctor
from app.models.user import User

router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"],
)

ACTIVE_APPOINTMENT_STATUSES = {"pending", "confirmed"}


class AppointmentCreate(BaseModel):
    availability_id: int
    notes: str | None = None


def get_current_doctor_profile(db: Session, current_user: User) -> Doctor:
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="فقط پزشک به این بخش دسترسی دارد.",
        )

    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="پروفایل پزشک پیدا نشد.",
        )

    return doctor


def get_locked_appointment(db: Session, appointment_id: int) -> Appointment:
    appointment = (
        db.query(Appointment)
        .filter(Appointment.id == appointment_id)
        .with_for_update(of=Appointment)
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="نوبت پیدا نشد.",
        )

    return appointment


def execute_booking(
    db: Session,
    slot_id: int,
    current_user: User,
    notes: str | None = None,
) -> Appointment:
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="فقط بیمار می‌تواند نوبت بگیرد.",
        )

    try:
        slot = (
            db.query(Availability)
            .filter(Availability.id == slot_id)
            .with_for_update(of=Availability)
            .first()
        )

        if not slot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="بازه زمانی پیدا نشد.",
            )

        if slot.is_booked or not slot.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="این بازه زمانی دیگر در دسترس نیست.",
            )

        doctor = db.query(Doctor).filter(Doctor.id == slot.doctor_id).first()
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="پزشک پیدا نشد.",
            )

        duplicate_same_day = (
            db.query(Appointment)
            .join(Availability, Appointment.availability_id == Availability.id)
            .filter(
                Appointment.patient_id == current_user.id,
                Appointment.doctor_id == slot.doctor_id,
                Availability.date == slot.date,
                Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
            )
            .first()
        )

        if duplicate_same_day:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="برای این پزشک در این روز قبلاً نوبت فعال دارید.",
            )

        new_appointment = Appointment(
            patient_id=current_user.id,
            doctor_id=slot.doctor_id,
            availability_id=slot.id,
            status="confirmed",
            notes=notes.strip() if notes else None,
        )

        slot.is_booked = True
        slot.is_available = False

        db.add(new_appointment)
        db.commit()
        db.refresh(new_appointment)
        return new_appointment

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطای داخلی هنگام ثبت نوبت رخ داد.",
        )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_appointment(
    body: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = execute_booking(db, body.availability_id, current_user, body.notes)
    return {"success": True, "appointment_id": appointment.id}


@router.post("/book/{slot_id}", status_code=status.HTTP_201_CREATED)
def book_appointment_quick(
    slot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = execute_booking(db, slot_id, current_user)
    return {"success": True, "appointment_id": appointment.id}


@router.get("/me")
def get_my_appointments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="این بخش فقط برای بیمار است.",
        )

    appointments = (
        db.query(Appointment)
        .options(
            joinedload(Appointment.availability),
            joinedload(Appointment.doctor).joinedload(Doctor.user),
        )
        .filter(Appointment.patient_id == current_user.id)
        .order_by(Appointment.id.desc())
        .all()
    )

    return {
        "success": True,
        "items": [
            {
                "id": appointment.id,
                "status": appointment.status,
                "doctor_name": (
                    appointment.doctor.user.name
                    if appointment.doctor and appointment.doctor.user
                    else "Unknown"
                ),
                "specialty": appointment.doctor.specialty if appointment.doctor else None,
                "date": (
                    appointment.availability.date.isoformat()
                    if appointment.availability
                    else None
                ),
                "start_time": (
                    appointment.availability.start_time.isoformat()
                    if appointment.availability
                    else None
                ),
                "notes": appointment.notes,
            }
            for appointment in appointments
        ],
    }


@router.put("/{appointment_id}/cancel")
@router.patch("/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = get_locked_appointment(db, appointment_id)

    if current_user.role == "patient":
        if appointment.patient_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="اجازه لغو این نوبت را ندارید.",
            )

    elif current_user.role == "doctor":
        doctor = get_current_doctor_profile(db, current_user)
        if appointment.doctor_id != doctor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="اجازه لغو این نوبت را ندارید.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="اجازه دسترسی ندارید.",
        )

    if appointment.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="این نوبت قبلاً لغو شده است.",
        )

    if appointment.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="این نوبت قبلاً تکمیل شده است.",
        )

    try:
        slot = None
        if appointment.availability_id:
            slot = (
                db.query(Availability)
                .filter(Availability.id == appointment.availability_id)
                .first()
            )

        if slot:
            slot.is_booked = False
            slot.is_available = True

        appointment.status = "cancelled"
        db.commit()
        db.refresh(appointment)

        return {
            "success": True,
            "message": "نوبت با موفقیت لغو شد.",
            "status": appointment.status,
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در لغو نوبت.",
        )


@router.put("/{appointment_id}/complete")
@router.patch("/{appointment_id}/complete")
def complete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doctor = get_current_doctor_profile(db, current_user)
    appointment = get_locked_appointment(db, appointment_id)

    if appointment.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="اجازه اتمام این نوبت را ندارید.",
        )

    if appointment.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="نوبت لغوشده قابل اتمام نیست.",
        )

    if appointment.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="این نوبت قبلاً تکمیل شده است.",
        )

    if appointment.status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="فقط نوبت تاییدشده قابل اتمام است.",
        )

    try:
        appointment.status = "completed"
        db.commit()
        db.refresh(appointment)

        return {
            "success": True,
            "status": appointment.status,
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در ثبت اتمام نوبت.",
        )


@router.get("")
def get_all_appointments_filtered(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Appointment).options(
        joinedload(Appointment.availability),
        joinedload(Appointment.doctor).joinedload(Doctor.user),
        joinedload(Appointment.patient),
    )

    if current_user.role == "patient":
        query = query.filter(Appointment.patient_id == current_user.id)
    elif current_user.role == "doctor":
        doctor = get_current_doctor_profile(db, current_user)
        query = query.filter(Appointment.doctor_id == doctor.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="اجازه دسترسی ندارید.",
        )

    items = query.order_by(Appointment.id.desc()).all()

    return {
        "success": True,
        "items": [
            {
                "id": item.id,
                "status": item.status,
                "patient_name": item.patient.name if item.patient else "Unknown",
                "doctor_name": (
                    item.doctor.user.name
                    if item.doctor and item.doctor.user
                    else "Unknown"
                ),
                "date": (
                    item.availability.date.isoformat()
                    if item.availability
                    else None
                ),
                "start_time": (
                    item.availability.start_time.isoformat()
                    if item.availability
                    else None
                ),
            }
            for item in items
        ],
    }
