from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional
from uuid import uuid4

import jdatetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database import get_db
from app.core.logger import get_logger
from app.models.appointment import Appointment
from app.models.availability import Availability
from app.models.doctor import Doctor
from app.models.user import User
from app.models.wallet import Transaction, TransactionType
from app.services.wallet_service import WalletService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"],
)

ACTIVE_APPOINTMENT_STATUSES = {"pending", "confirmed"}

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


def convert_to_jalali_details(gregorian_date: date):
    j_date = jdatetime.date.fromgregorian(date=gregorian_date)
    numeric = f"{j_date.year}/{j_date.month:02d}/{j_date.day:02d}"
    text = f"{j_date.year} {JALALI_MONTHS[j_date.month - 1]} {j_date.day}"
    return numeric, text


def get_user_by_id(db: Session, user_id: int | None) -> User | None:
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


def get_doctor_by_id(db: Session, doctor_id: int | None) -> Doctor | None:
    if not doctor_id:
        return None
    return db.query(Doctor).filter(Doctor.id == doctor_id).first()


def get_availability_by_id(db: Session, availability_id: int | None) -> Availability | None:
    if not availability_id:
        return None
    return db.query(Availability).filter(Availability.id == availability_id).first()


def get_user_display_name(user: User | None) -> str:
    if not user:
        return "نامشخص"

    name = getattr(user, "name", None)
    if name:
        return str(name)

    full_name = getattr(user, "full_name", None)
    if full_name:
        return str(full_name)

    first_name = getattr(user, "first_name", None)
    last_name = getattr(user, "last_name", None)
    combined_name = f"{first_name or ''} {last_name or ''}".strip()
    if combined_name:
        return combined_name

    phone = getattr(user, "phone", None)
    if phone:
        return str(phone)

    return "نامشخص"


def get_doctor_specialty_name(doctor: Doctor | None) -> str | None:
    if not doctor:
        return None

    for attr_name in ("specialty_relation", "specialty_obj"):
        try:
            specialty_obj = getattr(doctor, attr_name, None)
            if specialty_obj:
                specialty_name = getattr(specialty_obj, "name", None)
                if specialty_name:
                    return str(specialty_name)
        except Exception:
            pass

    specialty_id = getattr(doctor, "specialty_id", None)
    if specialty_id:
        return f"تخصص کد {specialty_id}"

    return None


def serialize_appointment(db: Session, appointment: Appointment) -> dict:
    availability_id = getattr(appointment, "availability_id", None)
    doctor_id = getattr(appointment, "doctor_id", None)
    patient_id = getattr(appointment, "patient_id", None)

    availability = get_availability_by_id(db, availability_id)
    doctor = get_doctor_by_id(db, doctor_id)

    doctor_user = None
    if doctor:
        doctor_user_id = getattr(doctor, "user_id", None)
        doctor_user = get_user_by_id(db, doctor_user_id)

    patient_user = get_user_by_id(db, patient_id)

    date_value = None
    start_time_value = None
    end_time_value = None

    if availability:
        availability_date = getattr(availability, "date", None)
        availability_start_time = getattr(availability, "start_time", None)
        availability_end_time = getattr(availability, "end_time", None)

        if availability_date:
            date_value = availability_date.isoformat()
        if availability_start_time:
            start_time_value = availability_start_time.strftime("%H:%M")
        if availability_end_time:
            end_time_value = availability_end_time.strftime("%H:%M")

    held_at = getattr(appointment, "held_at", None)

    return {
        "id": getattr(appointment, "id", None),
        "status": getattr(appointment, "status", None),
        "doctor_id": doctor_id,
        "patient_id": patient_id,
        "availability_id": availability_id,
        "doctor_name": get_user_display_name(doctor_user),
        "patient_name": get_user_display_name(patient_user),
        "doctor_specialty": get_doctor_specialty_name(doctor),
        "date": date_value,
        "start_time": start_time_value,
        "end_time": end_time_value,
        "notes": getattr(appointment, "notes", None),
        "tracking_code": getattr(appointment, "tracking_code", None),
        "held_at": held_at.isoformat() if held_at else None,
    }


def get_current_doctor_profile(db: Session, current_user: User):
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="فقط پزشک دسترسی دارد.",
        )

    doctor = (
        db.query(Doctor)
        .filter(Doctor.user_id == current_user.id)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="پروفایل پزشک پیدا نشد.",
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="نوبت پیدا نشد.",
        )

    return appointment


def execute_booking(
    db: Session,
    slot_id: int,
    current_user: User,
    notes: str | None = None,
):
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="فقط بیمار می‌تواند رزرو کند.",
        )

    try:
        slot = (
            db.query(Availability)
            .filter(Availability.id == slot_id)
            .with_for_update()
            .first()
        )

        if not slot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="زمان انتخاب‌شده پیدا نشد.",
            )

        if slot.is_booked or not slot.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="این زمان قبلاً رزرو شده است یا در دسترس نیست.",
            )

        doctor = (
            db.query(Doctor)
            .filter(Doctor.id == slot.doctor_id)
            .first()
        )

        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="پزشک مربوط به این زمان پیدا نشد.",
            )

        if doctor.user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="پروفایل کاربری پزشک کامل نیست.",
            )

        duplicate = (
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

        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="برای این پزشک در این روز یک نوبت فعال دارید.",
            )

        # -----------------------------
        # اعتبارسنجی قطعی هزینه ویزیت
        # -----------------------------
        fee_raw = getattr(doctor, "consultation_fee", None)
        if fee_raw is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="هزینه ویزیت این پزشک ثبت نشده است.",
            )

        try:
            fee = Decimal(str(fee_raw).strip())
        except (InvalidOperation, ValueError, TypeError) as exc:
            logger.exception(
                "Invalid consultation fee: doctor_id=%s, fee_raw=%r",
                doctor.id,
                fee_raw,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="هزینه ویزیت پزشک نامعتبر است.",
            ) from exc

        if not fee.is_finite() or fee <= Decimal("0"):
            logger.warning(
                "Invalid non-positive consultation fee: doctor_id=%s, fee=%s",
                doctor.id,
                fee,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="هزینه ویزیت پزشک باید بیشتر از صفر باشد.",
            )

        # -----------------------------
        # پرداخت اتمیک از کیف پول بیمار
        # -----------------------------
        try:
            transaction = WalletService.transfer_fee(
                db=db,
                patient_id=current_user.id,
                doctor_id=doctor.user_id,
                amount=fee,
                appointment_id=None,
                commit=False,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(
                "WALLET TRANSFER FAILED: patient_id=%s, doctor_id=%s, "
                "doctor_user_id=%s, slot_id=%s, fee=%s",
                current_user.id,
                doctor.id,
                doctor.user_id,
                slot.id,
                fee,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="خطا در پرداخت کیف پول هنگام ثبت نوبت.",
            ) from exc

        if transaction is None:
            logger.error(
                "WalletService.transfer_fee returned None: patient_id=%s, doctor_user_id=%s",
                current_user.id,
                doctor.user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="تراکنش پرداخت کیف پول ایجاد نشد.",
            )

        # -----------------------------
        # ایجاد نوبت و قفل‌کردن زمان
        # -----------------------------
        tracking_code = f"DT{uuid4().hex[:16].upper()}"
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        normalized_notes = notes.strip() if notes and notes.strip() else None

        appointment = Appointment(
            patient_id=current_user.id,
            doctor_id=slot.doctor_id,
            availability_id=slot.id,
            status="confirmed",
            tracking_code=tracking_code,
            disclaimer="رزرو آنلاین نوبت و پرداخت کیف پول",
            held_at=now_utc,
            notes=normalized_notes,
        )

        slot.is_booked = True
        slot.is_available = False

        db.add(appointment)
        db.flush()

        transaction.appointment_id = appointment.id
        transaction.description = f"پرداخت حق ویزیت برای نوبت شماره {appointment.id}"

        db.commit()
        db.refresh(appointment)

        logger.info(
            "Atomic booking completed: appointment_id=%s, patient_id=%s, "
            "doctor_id=%s, doctor_user_id=%s, slot_id=%s, fee=%s",
            appointment.id,
            current_user.id,
            doctor.id,
            doctor.user_id,
            slot.id,
            fee,
        )
        return appointment

    except HTTPException as exc:
        db.rollback()
        logger.warning(
            "Booking rolled back: slot_id=%s, patient_id=%s, status_code=%s, detail=%s",
            slot_id,
            current_user.id,
            exc.status_code,
            exc.detail,
        )
        raise exc
    except Exception as exc:
        db.rollback()
        logger.exception(
            "UNEXPECTED BOOKING ERROR: slot_id=%s, patient_id=%s",
            slot_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطای داخلی سرور در فرآیند ثبت نوبت.",
        ) from exc


@router.get("/doctors/{doctor_id}/schedule", response_model=DoctorScheduleResponse)
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
            start_time=slot.start_time.strftime("%H:%M") if slot.start_time else "00:00",
            end_time=slot.end_time.strftime("%H:%M") if slot.end_time else "00:00",
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


@router.post("", status_code=status.HTTP_201_CREATED)
def create_appointment(
    body: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = execute_booking(
        db=db,
        slot_id=body.availability_id,
        current_user=current_user,
        notes=body.notes,
    )

    return {
        "success": True,
        "appointment_id": appointment.id,
    }


@router.post("/book/{slot_id}", status_code=status.HTTP_201_CREATED)
def book_appointment_quick(
    slot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = execute_booking(
        db=db,
        slot_id=slot_id,
        current_user=current_user,
    )

    return {
        "success": True,
        "appointment_id": appointment.id,
    }


@router.get("/me")
def get_my_appointments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        if current_user.role == "patient":
            appointments = (
                db.query(Appointment)
                .filter(Appointment.patient_id == current_user.id)
                .order_by(Appointment.id.desc())
                .all()
            )
        elif current_user.role == "doctor":
            doctor_profile = (
                db.query(Doctor)
                .filter(Doctor.user_id == current_user.id)
                .first()
            )

            if not doctor_profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="پروفایل پزشک پیدا نشد.",
                )

            appointments = (
                db.query(Appointment)
                .filter(Appointment.doctor_id == doctor_profile.id)
                .order_by(Appointment.id.desc())
                .all()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="دسترسی غیرمجاز.",
            )

        items = [
            serialize_appointment(db=db, appointment=appointment)
            for appointment in appointments
        ]

        return {
            "success": True,
            "count": len(items),
            "items": items,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch user appointments")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطای سرور در دریافت لیست نوبت‌ها",
        )


@router.post("/{appointment_id}/cancel")
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
            detail="دسترسی غیرمجاز.",
        )

    if appointment.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="این نوبت قبلاً لغو شده.",
        )

    if appointment.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
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

            if slot:
                slot.is_booked = False
                slot.is_available = True
                db.add(slot)

        original_tx = (
            db.query(Transaction)
            .filter(
                Transaction.appointment_id == appointment.id,
                Transaction.transaction_type == TransactionType.TRANSFER,
            )
            .first()
        )

        refund_msg = ""
        if original_tx:
            WalletService.refund(
                db=db,
                transaction_id=original_tx.id,
                description=f"برگشت وجه بابت لغو نوبت شماره {appointment.id}",
                commit=False,
            )
            refund_msg = " و هزینه ویزیت به کیف پول بیمار برگشت داده شد"

        appointment.status = "cancelled"
        db.add(appointment)

        db.commit()
        db.refresh(appointment)

        logger.info("Appointment cancelled atomically: appointment_id=%s", appointment.id)
        return {
            "success": True,
            "message": f"نوبت با موفقیت لغو شد، زمان مجدداً آزاد گردید{refund_msg}.",
            "status": appointment.status,
        }

    except HTTPException as he:
        db.rollback()
        logger.warning("Cancellation failed due to: %s", he.detail)
        raise he
    except Exception:
        db.rollback()
        logger.exception("Cancellation error. Rolled back.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در فرآیند لغو نوبت و بازگشت وجه در سرور",
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
            detail="این نوبت متعلق به شما نیست.",
        )

    if appointment.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="نوبت لغوشده است و قابل انجام نیست.",
        )

    if appointment.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="این نوبت قبلاً تکمیل شده است.",
        )

    try:
        appointment.status = "completed"
        db.commit()
        db.refresh(appointment)

        logger.info("Appointment marked as completed: appointment_id=%s", appointment.id)
        return {
            "success": True,
            "status": appointment.status,
        }

    except Exception:
        db.rollback()
        logger.exception("Failed to complete appointment: appointment_id=%s", appointment_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در تکمیل نوبت",
        )


@router.get("")
@router.get("/")
def get_all_appointments_filtered(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if current_user.role == "patient":
            appointments = (
                db.query(Appointment)
                .filter(Appointment.patient_id == current_user.id)
                .order_by(Appointment.id.desc())
                .all()
            )
        elif current_user.role == "doctor":
            doctor = get_current_doctor_profile(db, current_user)
            appointments = (
                db.query(Appointment)
                .filter(Appointment.doctor_id == doctor.id)
                .order_by(Appointment.id.desc())
                .all()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="دسترسی ندارید.",
            )

        items = [
            serialize_appointment(db=db, appointment=appointment)
            for appointment in appointments
        ]

        return {
            "success": True,
            "count": len(items),
            "items": items,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error listing all filtered appointments")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطای سرور در دریافت نوبت‌ها",
        )
