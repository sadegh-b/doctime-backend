import traceback
from datetime import datetime
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

# --- Schemas ---
class AppointmentCreate(BaseModel):
    availability_id: int
    notes: str | None = None

# --- Helper Functions (Private) ---

def get_current_doctor_profile(db: Session, current_user: User) -> Doctor:
    """پیدا کردن پروفایل پزشکی کاربر فعلی"""
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Doctors only.",
        )
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found.",
        )
    return doctor

def get_locked_appointment(db: Session, appointment_id: int) -> Appointment:
    """دریافت نوبت با قفل سطر برای جلوگیری از تغییرات همزمان"""
    appointment = (
        db.query(Appointment)
        .filter(Appointment.id == appointment_id)
        .with_for_update(of=Appointment)
        .first()
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found.",
        )
    return appointment

def execute_booking(
    db: Session,
    slot_id: int,
    current_user: User,
    notes: str | None = None,
) -> Appointment:
    """منطق اصلی رزرو نوبت با رعایت ایمنی همزمانی"""
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can book appointments.",
        )

    try:
        # 1. قفل کردن اسلات زمان (Locking the Slot)
        slot = (
            db.query(Availability)
            .filter(Availability.id == slot_id)
            .with_for_update(of=Availability)
            .first()
        )

        if not slot:
            raise HTTPException(status_code=404, detail="Time slot not found.")

        if slot.is_booked or not slot.is_available:
            raise HTTPException(status_code=400, detail="This slot is no longer available.")

        # 2. بررسی نوبت تکراری در همان روز (Duplicate Check inside Transaction)
        # صادق: این بخش جلوی ثبت دو نوبت همزمان توسط یک بیمار برای یک پزشک را می‌گیرد
        duplicate_check = (
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

        if duplicate_check:
            raise HTTPException(
                status_code=400,
                detail="You already have an active appointment with this doctor on this date."
            )

        # 3. ثبت نوبت و آپدیت اسلات
        new_appointment = Appointment(
            patient_id=current_user.id,
            doctor_id=slot.doctor_id,
            availability_id=slot.id,
            status="confirmed",
            notes=notes,
        )

        slot.is_booked = True
        slot.is_available = False

        db.add(new_appointment)
        db.commit() # ذخیره نهایی
        db.refresh(new_appointment)
        return new_appointment

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during booking."
        )

# --- Routes ---

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
    """لیست نوبت‌های بیمار"""
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
                "id": a.id,
                "status": a.status,
                "doctor_name": a.doctor.user.name if a.doctor else "Unknown",
                "specialty": a.doctor.specialty if a.doctor else None,
                "date": a.availability.date.isoformat() if a.availability else None,
                "start_time": a.availability.start_time.isoformat() if a.availability else None,
                "notes": a.notes
            } for a in appointments
        ]
    }

@router.put("/{appointment_id}/cancel")
@router.patch("/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """لغو نوبت توسط بیمار یا پزشک"""
    appointment = get_locked_appointment(db, appointment_id)

    # Authorization Check
    if current_user.role == "patient" and appointment.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your appointment.")
    elif current_user.role == "doctor":
        doctor = get_current_doctor_profile(db, current_user)
        if appointment.doctor_id != doctor.id:
            raise HTTPException(status_code=403, detail="Not your patient's appointment.")

    if appointment.status in ["cancelled", "completed"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel a {appointment.status} appointment.")

    try:
        # آزاد کردن اسلات زمانی
        slot = db.query(Availability).filter(Availability.id == appointment.availability_id).first()
        if slot:
            slot.is_booked = False
            slot.is_available = True
        
        appointment.status = "cancelled"
        db.commit()
        return {"success": True, "message": "Appointment cancelled."}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to cancel.")

@router.put("/{appointment_id}/complete")
@router.patch("/{appointment_id}/complete")
def complete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """اتمام نوبت (فقط توسط پزشک)"""
    doctor = get_current_doctor_profile(db, current_user)
    appointment = get_locked_appointment(db, appointment_id)

    if appointment.doctor_id != doctor.id:
        raise HTTPException(status_code=403, detail="This is not your appointment.")

    if appointment.status != "confirmed":
        raise HTTPException(status_code=400, detail="Only confirmed appointments can be completed.")

    try:
        appointment.status = "completed"
        db.commit()
        return {"success": True, "status": "completed"}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Update failed.")

@router.get("")
def get_all_appointments_filtered(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """دریافت تمام نوبت‌ها بر اساس نقش کاربر"""
    query = db.query(Appointment).options(
        joinedload(Appointment.availability),
        joinedload(Appointment.doctor).joinedload(Doctor.user),
        joinedload(Appointment.patient)
    )

    if current_user.role == "patient":
        query = query.filter(Appointment.patient_id == current_user.id)
    elif current_user.role == "doctor":
        doctor = get_current_doctor_profile(db, current_user)
        query = query.filter(Appointment.doctor_id == doctor.id)
    
    items = query.order_by(Appointment.id.desc()).all()
    
    return {
        "success": True,
        "items": [
            {
                "id": i.id,
                "status": i.status,
                "patient_name": i.patient.name if i.patient else "Unknown",
                "doctor_name": i.doctor.user.name if i.doctor else "Unknown",
                "date": i.availability.date.isoformat() if i.availability else None,
                "start_time": i.availability.start_time.isoformat() if i.availability else None,
            } for i in items
        ]
    }
