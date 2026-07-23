# Path: backend/app/api/routes/appointments.py

import traceback
from datetime import date, timedelta, datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

import jdatetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_
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

ACTIVE_APPOINTMENT_STATUSES = {
    "pending",
    "confirmed",
}

WEEKDAY_TO_PERSIAN = {
    0: "دوشنبه",
    1: "سه‌شنبه",
    2: "چهارشنبه",
    3: "پنج‌شنبه",
    4: "جمعه",
    5: "شنبه",
    6: "یکشنبه",
}

JALALI_MONTHS = [
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
]

# ==========================
# Schemas
# ==========================

class AppointmentCreate(BaseModel):
    availability_id: int
    notes: str | None = None

class SlotDetailOut(BaseModel):
    slot_id: int
    start_time: str
    end_time: str
    is_available: bool
    is_booked: bool

class DailyScheduleOut(BaseModel):
    date: str
    persian_date: str
    persian_formatted_date: str
    persian_day_name: str
    slots: List[SlotDetailOut]

class DoctorScheduleResponse(BaseModel):
    success: bool
    doctor_id: int
    schedule: List[DailyScheduleOut]

# ==========================
# Helpers
# ==========================

def convert_to_jalali_details(gregorian_date: date):
    j_date = jdatetime.date.fromgregorian(date=gregorian_date)
    numeric = f"{j_date.year}/{j_date.month:02d}/{j_date.day:02d}"
    text = f"{j_date.year} {JALALI_MONTHS[j_date.month - 1]} {j_date.day}"
    return numeric, text

def get_current_doctor_profile(db: Session, current_user: User):
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=403,
            detail="فقط پزشک دسترسی دارد."
        )
    doctor = (
        db.query(Doctor)
        .filter(Doctor.user_id == current_user.id)
        .first()
    )
    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="پروفایل پزشک پیدا نشد."
        )
    return doctor

def get_locked_appointment(db: Session, appointment_id: int):
    appointment = (
        db.query(Appointment)
        .filter(Appointment.id == appointment_id)
        .with_for_update()
        .first()
    )
    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="نوبت پیدا نشد."
        )
    return appointment

# ==========================
# Booking Core
# ==========================

def execute_booking(
    db: Session,
    slot_id: int,
    current_user: User,
    notes: str | None = None,
):
    print("=" * 60)
    print("BOOKING REQUEST")
    print("slot_id =", slot_id)
    print("user_id =", current_user.id)
    print("=" * 60)

    if current_user.role != "patient":
        raise HTTPException(
            status_code=403,
            detail="فقط بیمار می‌تواند رزرو کند.",
        )

    try:
        # قفل‌کردن اسلات برای جلوگیری از ثبت همزمان دو بیمار (Race Conditions)
        slot = (
            db.query(Availability)
            .filter(Availability.id == slot_id)
            .with_for_update()
            .first()
        )

        if not slot:
            raise HTTPException(
                status_code=404,
                detail="زمان پیدا نشد.",
            )

        print(
            "FOUND SLOT:",
            "id =", slot.id,
            "doctor_id =", slot.doctor_id,
            "booked =", slot.is_booked,
            "available =", slot.is_available,
        )

        if slot.is_booked or not slot.is_available:
            raise HTTPException(
                status_code=400,
                detail="این زمان قبلاً رزرو شده است یا در دسترس نیست.",
            )

        doctor = (
            db.query(Doctor)
            .filter(Doctor.id == slot.doctor_id)
            .first()
        )

        if not doctor:
            raise HTTPException(
                status_code=404,
                detail="پزشک پیدا نشد.",
            )

        # جلوگیری از داشتن دو نوبت فعال برای یک بیمار نزد یک پزشک در یک روز
        duplicate = (
            db.query(Appointment)
            .join(
                Availability,
                Appointment.availability_id == Availability.id,
            )
            .filter(
                Appointment.patient_id == current_user.id,
                Appointment.doctor_id == slot.doctor_id,
                Availability.date == slot.date,
                Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
            )
            .first()
        )

        if duplicate:
            raise HTTPException(
                status_code=400,
                detail="برای این پزشک در این روز نوبت فعال دارید.",
            )

        tracking_code = f"DT{uuid4().hex[:16]}"

        # حل مشکل منسوخ شدن datetime.utcnow()
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        appointment = Appointment(
            patient_id=current_user.id,
            doctor_id=slot.doctor_id,
            availability_id=slot.id,
            status="confirmed",
            tracking_code=tracking_code,
            disclaimer="رزرو آنلاین نوبت",
            held_at=now_utc,
            notes=notes.strip() if notes and notes.strip() else None,
        )

        slot.is_booked = True
        slot.is_available = False

        db.add(appointment)
        db.commit()
        db.refresh(appointment)

        print(
            "BOOKING SUCCESS:",
            "appointment_id =", appointment.id,
            "tracking_code =", appointment.tracking_code,
        )

        return appointment

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()
        print("=" * 60)
        print("BOOKING ERROR")
        print(repr(exc))
        traceback.print_exc()
        print("=" * 60)
        raise HTTPException(
            status_code=500,
            detail="خطای داخلی هنگام رزرو نوبت در دیتابیس.",
        )

# ==========================
# Endpoints
# ==========================

@router.get(
    "/doctors/{doctor_id}/schedule",
    response_model=DoctorScheduleResponse
)
def get_doctor_schedule_grid(
    doctor_id: int,
    start_date: Optional[date] = None,
    days_limit: int = Query(default=14, ge=1, le=90),
    db: Session = Depends(get_db),
):
    if start_date is None:
        start_date = date.today()

    end_date = start_date + timedelta(days=days_limit)

    availabilities = (
        db.query(Availability)
        .filter(
            and_(
                Availability.doctor_id == doctor_id,
                Availability.date >= start_date,
                Availability.date < end_date,
            )
        )
        .order_by(Availability.date, Availability.start_time)
        .all()
    )

    grouped: Dict[date, List[SlotDetailOut]] = {}

    for slot in availabilities:
        item = SlotDetailOut(
            slot_id=slot.id,
            start_time=slot.start_time.strftime("%H:%M"),
            end_time=slot.end_time.strftime("%H:%M"),
            is_available=slot.is_available,
            is_booked=slot.is_booked,
        )
        grouped.setdefault(slot.date, []).append(item)

    schedule = []

    for target_date in sorted(grouped.keys()):
        jalali_numeric, jalali_text = convert_to_jalali_details(target_date)
        schedule.append(
            DailyScheduleOut(
                date=target_date.isoformat(),
                persian_date=jalali_numeric,
                persian_formatted_date=jalali_text,
                persian_day_name=WEEKDAY_TO_PERSIAN.get(target_date.weekday(), "نامشخص"),
                slots=grouped[target_date],
            )
        )

    return {
        "success": True,
        "doctor_id": doctor_id,
        "schedule": schedule,
    }

# ==========================
# Create Appointment (POST /api/v1/appointments)
# ==========================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED
)
def create_appointment(
    body: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    print("=" * 60)
    print("REQUEST BODY:", body.model_dump())
    print("availability_id =", body.availability_id)
    print("user_id =", current_user.id)
    print("=" * 60)

    appointment = execute_booking(
        db,
        body.availability_id,
        current_user,
        body.notes
    )

    return {
        "success": True,
        "appointment_id": appointment.id
    }

@router.post(
    "/book/{slot_id}",
    status_code=status.HTTP_201_CREATED
)
def book_appointment_quick(
    slot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = execute_booking(
        db,
        slot_id,
        current_user
    )

    return {
        "success": True,
        "appointment_id": appointment.id
    }

# ==========================
# Patient Appointments
# ==========================

@router.get("/me")
def get_my_appointments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "patient":
        raise HTTPException(
            status_code=403,
            detail="فقط بیمار دسترسی دارد."
        )

    # اضافه کردن joinedload برای تخصیص رابطه تخصص پزشک به صورت همزمان
    appointments = (
        db.query(Appointment)
        .options(
            joinedload(Appointment.availability),
            joinedload(Appointment.doctor).joinedload(Doctor.user),
            joinedload(Appointment.doctor).joinedload(Doctor.specialty_relation),
        )
        .filter(Appointment.patient_id == current_user.id)
        .order_by(Appointment.id.desc())
        .all()
    )

    items = []

    for appointment in appointments:
        availability = appointment.availability
        doctor = appointment.doctor

        # استخراج نام تخصص از رابطه شیء به جای صفت مستقیم نا‌موجود
        doctor_specialty_name = (
            doctor.specialty_relation.name 
            if doctor and doctor.specialty_relation 
            else "نامشخص"
        )

        items.append(
            {
                "id": appointment.id,
                "status": appointment.status,
                "doctor_name": (doctor.user.name if doctor and doctor.user else "Unknown"),
                "doctor_specialty": doctor_specialty_name,
                "date": (availability.date.isoformat() if availability else None),
                "start_time": (availability.start_time.strftime("%H:%M") if availability else None),
                "end_time": (availability.end_time.strftime("%H:%M") if availability else None),
                "notes": appointment.notes,
            }
        )

    return {
        "success": True,
        "items": items
    }

# ==========================
# Cancel Appointment
# ==========================

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
                status_code=403,
                detail="اجازه لغو این نوبت را ندارید.",
            )
    elif current_user.role == "doctor":
        doctor = get_current_doctor_profile(db, current_user)
        if appointment.doctor_id != doctor.id:
            raise HTTPException(
                status_code=403,
                detail="اجازه لغو این نوبت را ندارید.",
            )
    else:
        raise HTTPException(
            status_code=403,
            detail="دسترسی غیرمجاز.",
        )

    if appointment.status == "cancelled":
        raise HTTPException(
            status_code=400,
            detail="این نوبت قبلاً لغو شده.",
        )

    if appointment.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="نوبت تکمیل شده قابل لغو نیست.",
        )

    try:
        if appointment.availability_id:
            slot = (
                db.query(Availability)
                .filter(Availability.id == appointment.availability_id)
                .with_for_update()
                .first()
            )
            # بهبود پایداری لغو در صورت نبود رکورد فیزیکی اسلات
            if slot:
                slot.is_booked = False
                slot.is_available = True

        appointment.status = "cancelled"

        db.commit()
        db.refresh(appointment)

        return {
            "success": True,
            "message": "نوبت با موفقیت لغو شد و زمان آزاد گردید.",
            "status": appointment.status,
        }

    except Exception as exc:
        db.rollback()
        print("=" * 60)
        print("CANCEL ERROR")
        print(repr(exc))
        traceback.print_exc()
        print("=" * 60)
        raise HTTPException(
            status_code=500,
            detail="خطا در فرآیند لغو نوبت در سرور.",
        )

# ==========================
# Complete Appointment
# ==========================

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
            status_code=403,
            detail="این نوبت متعلق به شما نیست."
        )

    if appointment.status == "cancelled":
        raise HTTPException(
            status_code=400,
            detail="نوبت لغوشده است و قابل انجام نیست."
        )

    if appointment.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="این نوبت قبلاً تکمیل شده است."
        )

    appointment.status = "completed"
    db.commit()
    db.refresh(appointment)

    return {
        "success": True,
        "status": appointment.status
    }

# ==========================
# All Appointments
# ==========================

@router.get("")
@router.get("/")
def get_all_appointments_filtered(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(Appointment)
        .options(
            joinedload(Appointment.availability),
            joinedload(Appointment.doctor).joinedload(Doctor.user),
            joinedload(Appointment.doctor).joinedload(Doctor.specialty_relation),
            joinedload(Appointment.patient),
        )
    )

    if current_user.role == "patient":
        query = query.filter(Appointment.patient_id == current_user.id)
    elif current_user.role == "doctor":
        doctor = get_current_doctor_profile(db, current_user)
        query = query.filter(Appointment.doctor_id == doctor.id)
    else:
        raise HTTPException(
            status_code=403,
            detail="دسترسی ندارید."
        )

    appointments = query.order_by(Appointment.id.desc()).all()
    items = []

    for item in appointments:
        # استخراج نام تخصص پزشک در این بخش نیز اصلاح شد
        doctor_specialty_name = (
            item.doctor.specialty_relation.name 
            if item.doctor and item.doctor.specialty_relation 
            else "نامشخص"
        )

        items.append(
            {
                "id": item.id,
                "status": item.status,
                "patient_name": (item.patient.name if item.patient else "Unknown"),
                "doctor_name": (item.doctor.user.name if item.doctor and item.doctor.user else "Unknown"),
                "doctor_specialty": doctor_specialty_name,
                "date": (item.availability.date.isoformat() if item.availability else None),
                "start_time": (item.availability.start_time.strftime("%H:%M") if item.availability else None),
                "end_time": (item.availability.end_time.strftime("%H:%M") if item.availability else None),
            }
        )

    return {
        "success": True,
        "items": items
    }
