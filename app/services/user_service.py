# مسیر فایل: app/api/routes/appointments.py

import traceback
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

class AppointmentCreate(BaseModel):
    availability_id: int
    notes: str | None = None

@router.post("", status_code=status.HTTP_201_CREATED)
def create_appointment(
    body: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ثبت نوبت جدید توسط بیمار.
    بررسی عدم رزرو تکراری برای یک پزشک در یک روز.
    """
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can book appointments",
        )

    # پیدا کردن اسلات زمانی و قفل کردن آن برای جلوگیری از Race Condition
    slot = (
        db.query(Availability)
        .filter(Availability.id == body.availability_id)
        .with_for_update() # جلوگیری از رزرو همزمان
        .first()
    )

    if not slot:
        raise HTTPException(status_code=404, detail="Time slot not found")

    if slot.is_booked or not slot.is_available:
        raise HTTPException(status_code=400, detail="Time slot already booked or unavailable")

    # بررسی قانون: یک نوبت با این پزشک در این تاریخ
    duplicate_date_check = (
        db.query(Appointment)
        .join(Availability, Appointment.availability_id == Availability.id)
        .filter(
            Appointment.patient_id == current_user.id,
            Appointment.doctor_id == slot.doctor_id,
            Availability.date == slot.date,
            Appointment.status != "cancelled",
        )
        .first()
    )

    if duplicate_date_check:
        raise HTTPException(
            status_code=400,
            detail="You already have an active appointment with this doctor on this date",
        )

    try:
        # ایجاد نوبت
        appointment = Appointment(
            patient_id=current_user.id,
            doctor_id=slot.doctor_id,
            availability_id=slot.id,
            status="confirmed",
            notes=body.notes,
        )

        # به‌روزرسانی وضعیت اسلات
        slot.is_booked = True
        slot.is_available = False

        db.add(appointment)
        db.commit()
        db.refresh(appointment)

        return {
            "success": True,
            "message": "Appointment created successfully",
            "appointment_id": appointment.id,
        }

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Internal server error during booking",
        )

@router.get("/me")
def get_my_appointments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """لیست نوبت‌های من (بیمار یا پزشک)"""
    query = db.query(Appointment).options(
        joinedload(Appointment.availability),
        joinedload(Appointment.doctor).joinedload(Doctor.user),
        joinedload(Appointment.patient)
    )

    if current_user.role == "patient":
        query = query.filter(Appointment.patient_id == current_user.id)
    elif current_user.role == "doctor":
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        query = query.filter(Appointment.doctor_id == doctor.id)

    appointments = query.order_by(Appointment.id.desc()).all()

    return {
        "success": True,
        "count": len(appointments),
        "items": [
            {
                "id": item.id,
                "status": item.status,
                "doctor_name": item.doctor.user.name if item.doctor else "N/A",
                "patient_name": item.patient.name,
                "date": item.availability.date.isoformat() if item.availability else None,
                "start_time": item.availability.start_time.isoformat() if item.availability else None,
                "notes": item.notes,
            }
            for item in appointments
        ],
    }

@router.put("/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """لغو نوبت و آزاد کردن اسلات زمانی (بدون حذف فیزیکی)"""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # بررسی دسترسی برای لغو نوبت
    can_cancel = False
    if current_user.role == "patient" and appointment.patient_id == current_user.id:
        can_cancel = True
    elif current_user.role == "doctor":
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if doctor and appointment.doctor_id == doctor.id:
            can_cancel = True

    if not can_cancel:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this appointment")

    if appointment.status == "cancelled":
        raise HTTPException(status_code=400, detail="Appointment already cancelled")

    try:
        # آزاد کردن مجدد اسلات زمانی
        slot = db.query(Availability).filter(Availability.id == appointment.availability_id).first()
        if slot:
            slot.is_booked = False
            slot.is_available = True

        # تغییر وضعیت نوبت بدون حذف رکورد
        appointment.status = "cancelled"
        db.commit()

        return {"success": True, "message": "Appointment cancelled successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error during cancellation")

@router.put("/{appointment_id}/complete")
def complete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """اتمام نوبت توسط پزشک"""
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can complete appointments")

    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.doctor_id == doctor.id
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment.status = "completed"
    db.commit()

    return {"success": True, "message": "Appointment marked as completed"}
