# Path: backend/app/api/routes/auth.py

import logging
import random
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.doctor import Doctor
from app.models.user import User
from app.models.otp import OTPVerification
from app.schemas.auth import TokenResponse, UserLogin, UserResponse, OTPRequest
from app.schemas.user import DoctorOut, UserOut, UserRegister
from app.api.routes.availability import create_slots_for_range

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

PERSIAN_DAY_TO_WEEKDAY = {
    "دوشنبه": 0, "سه شنبه": 1, "سه‌شنبه": 1, "چهارشنبه": 2,
    "پنج شنبه": 3, "پنج‌شنبه": 3, "جمعه": 4, "شنبه": 5,
    "یکشنبه": 6, "یک‌شنبه": 6,
}

def split_full_name(full_name: str) -> tuple[str, str]:
    cleaned = (full_name or "").strip()
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="نام و نام خانوادگی الزامی است.")
    parts = cleaned.split(maxsplit=1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else "نامشخص"
    return first_name, last_name

def parse_time_str(value: Optional[str], field_name: str = "زمان") -> time:
    if value is None or str(value).strip() == "":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field_name} الزامی است.")
    value = str(value).strip()
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"فرمت ساعت نامعتبر است: {value}. فرمت درست مثل 09:30 است.")

def parse_date_str(value: Optional[str]) -> date:
    if not value: return date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"فرمت تاریخ نامعتبر است: {value}. فرمت درست مثل 2026-07-25 است.")

def validate_time_range(start: time, end: time, title: str) -> None:
    if start >= end:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"ساعت شروع {title} باید قبل از ساعت پایان باشد.")

def validate_doctor_registration_data(user_data: UserRegister) -> None:
    if user_data.role != "doctor": return
    if not user_data.work_days:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="حداقل یک روز کاری برای پزشک الزامی است.")
    invalid_days = [day for day in user_data.work_days if day not in PERSIAN_DAY_TO_WEEKDAY]
    if invalid_days:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"روز(های) کاری نامعتبر هستند: {', '.join(invalid_days)}")
    if user_data.work_shift not in ("morning", "afternoon", "both"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="نوع شیفت پزشک نامعتبر است.")
    if user_data.work_shift in ("morning", "both"):
        m_start = parse_time_str(user_data.morning_start, "ساعت شروع شیفت صبح")
        m_end = parse_time_str(user_data.morning_end, "ساعت پایان شیفت صبح")
        validate_time_range(m_start, m_end, "شیفت صبح")
    if user_data.work_shift in ("afternoon", "both"):
        a_start = parse_time_str(user_data.afternoon_start, "ساعت شروع شیفت عصر")
        a_end = parse_time_str(user_data.afternoon_end, "ساعت پایان شیفت عصر")
        validate_time_range(a_start, a_end, "شیفت عصر")

def build_user_response(user: User, doctor: Optional[Doctor] = None, message: str = "OK", token: Optional[TokenResponse] = None) -> UserResponse:
    if doctor:
        specialty_name = doctor.specialty_relation.name if doctor.specialty_relation else "نامشخص"
        user_out = DoctorOut(
            id=user.id, name=user.name, phone=user.phone, email=user.email, role=user.role, is_active=user.is_active,
            doctor_id=doctor.id, medical_council_number=doctor.medical_council_number, specialty_id=doctor.specialty_id,
            specialty=specialty_name, sub_specialty=getattr(doctor, "sub_specialty", None), province=getattr(doctor, "province", None),
            city=doctor.city, address=getattr(doctor, "address", None), latitude=getattr(doctor, "latitude", None),
            longitude=getattr(doctor, "longitude", None), bio=getattr(doctor, "bio", None), experience_years=getattr(doctor, "experience_years", 0) or 0,
            consultation_fee=getattr(doctor, "consultation_fee", 0) or 0, work_shift=getattr(doctor, "work_shift", None),
        )
    else:
        user_out = UserOut(id=user.id, name=user.name, phone=user.phone, email=user.email, role=user.role, is_active=user.is_active)
    return UserResponse(message=message, user=user_out, token=token)

def create_doctor_profile(db: Session, user: User, user_data: UserRegister) -> Doctor:
    if not user_data.specialty_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="شناسه تخصص برای ثبت‌نام پزشک الزامی است.")
    doctor = Doctor(
        user_id=user.id, medical_council_number=user_data.medical_council_number, specialty_id=user_data.specialty_id,
        sub_specialty=user_data.sub_specialty, province=user_data.province, city=user_data.city, address=user_data.address,
        latitude=user_data.latitude, longitude=user_data.longitude, bio=user_data.bio, experience_years=user_data.experience_years,
        consultation_fee=user_data.consultation_fee, work_shift=user_data.work_shift,
    )
    db.add(doctor)
    db.flush()
    return doctor

def create_doctor_availabilities(db: Session, doctor_id: int, user_data: UserRegister, days_count: int = 30, slot_minutes: int = 30) -> None:
    if user_data.role != "doctor": return
    start_date = parse_date_str(user_data.schedule_start_date)
    selected_weekdays = {PERSIAN_DAY_TO_WEEKDAY[day] for day in user_data.work_days if day in PERSIAN_DAY_TO_WEEKDAY}
    m_start = m_end = a_start = a_end = None
    if user_data.work_shift in ("morning", "both"):
        m_start = parse_time_str(user_data.morning_start, "ساعت شروع شیفت صبح")
        m_end = parse_time_str(user_data.morning_end, "ساعت پایان شیفت صبح")
    if user_data.work_shift in ("afternoon", "both"):
        a_start = parse_time_str(user_data.afternoon_start, "ساعت شروع شیفت عصر")
        a_end = parse_time_str(user_data.afternoon_end, "ساعت پایان شیفت عصر")
    for day_offset in range(days_count):
        current_date = start_date + timedelta(days=day_offset)
        if current_date.weekday() not in selected_weekdays: continue
        if m_start and m_end:
            create_slots_for_range(db=db, doctor_id=doctor_id, slot_date=current_date, start_time=m_start, end_time=m_end, slot_minutes=slot_minutes)
        if a_start and a_end:
            create_slots_for_range(db=db, doctor_id=doctor_id, slot_date=current_date, start_time=a_start, end_time=a_end, slot_minutes=slot_minutes)

# ==========================================
# OTP Endpoints
# ==========================================

@router.post("/otp/send", status_code=status.HTTP_200_OK)
def send_otp(payload: OTPRequest, db: Session = Depends(get_db)):
    # تغییر صادق: تولید کد ۶ رقمی استاندارد برای امنیت بالاتر و هماهنگی کامل با فرانت
    code = f"{random.randint(100000, 999999)}" 
    # برای جلوگیری از باگ‌های اختلاف ساعت سرور و دیتابیس، از datetime.utcnow() هماهنگ استفاده می‌کنیم
    expires_at = datetime.utcnow() + timedelta(minutes=2)

    db.query(OTPVerification).filter(
        OTPVerification.phone == payload.phone,
        OTPVerification.is_verified == False
    ).delete()

    otp_entry = OTPVerification(phone=payload.phone, code=code, expires_at=expires_at, is_verified=False)
    db.add(otp_entry)
    db.commit()

    logger.info(f"=========== SIMULATED SMS SMS ==============")
    logger.info(f"SMS SENT TO: {payload.phone} | CODE: {code}")
    logger.info(f"============================================")

    return {
        "success": True,
        "message": "کد تایید ۶ رقمی پیامک شد.",
        "expires_in_seconds": 120,
        "code_debug_only": code 
    }

# ==========================================
# Core Authentication Endpoints
# ==========================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserRegister, otp_code: str = Query(..., description="کد اعتبارسنجی پیامکی"), db: Session = Depends(get_db)):
    validate_doctor_registration_data(user_data)
    
    # حل مشکل اختلاف ساعت با استفاده از datetime.utcnow()
    now = datetime.utcnow()
    otp_record = db.query(OTPVerification).filter(
        OTPVerification.phone == user_data.phone,
        OTPVerification.code == otp_code,
        OTPVerification.is_verified == False
    ).first()

    if not otp_record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="کد تایید نامعتبر است.")
    
    # حذف replace(tzinfo=timezone.utc) برای مقایسه دقیق و بدون خطای timezone دیتابیس
    if otp_record.expires_at < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="کد تایید منقضی شده است.")

    filters = (User.phone == user_data.phone) | (User.national_id == user_data.national_id)
    if user_data.email and user_data.email.strip() != "":
        filters = filters | (User.email == user_data.email)

    existing_user = db.query(User).filter(filters).first()
    if existing_user:
        if existing_user.phone == user_data.phone: detail = "این شماره موبایل قبلاً ثبت شده است."
        elif existing_user.national_id == user_data.national_id: detail = "این کد ملی قبلاً ثبت شده است."
        else: detail = "این ایمیل قبلاً ثبت شده است."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    if user_data.role == "doctor":
        if db.query(Doctor).filter(Doctor.medical_council_number == user_data.medical_council_number).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="این کد نظام پزشکی قبلاً ثبت شده است.")

    try:
        first_name, last_name = split_full_name(user_data.name)
        user = User(
            name=user_data.name, first_name=first_name, last_name=last_name, national_id=user_data.national_id,
            phone=user_data.phone, email=user_data.email, hashed_password=hash_password(user_data.password),
            role=user_data.role, is_active=True,
        )
        db.add(user)
        db.flush()

        doctor = None
        if user_data.role == "doctor":
            doctor = create_doctor_profile(db=db, user=user, user_data=user_data)
            create_doctor_availabilities(db=db, doctor_id=doctor.id, user_data=user_data)

        otp_record.is_verified = True
        db.commit()
        db.refresh(user)
        if doctor: db.refresh(doctor)

        access_token = create_access_token(subject=str(user.id))
        return build_user_response(user=user, doctor=doctor, message="ثبت‌نام با موفقیت انجام شد.", token=TokenResponse(access_token=access_token, token_type="bearer"))

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="اطلاعات وارد شده تکراری یا نامعتبر است.")
    except Exception as exc:
        db.rollback()
        logger.exception("Registration error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="خطای داخلی سرور.")

@router.post("/login", response_model=UserResponse)
def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == user_data.phone).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="شماره موبایل یا رمز عبور اشتباه است.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="حساب کاربری شما غیرفعال است.")
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first() if user.role == "doctor" else None
    access_token = create_access_token(subject=str(user.id))
    return build_user_response(user=user, doctor=doctor, message="ورود موفقیت‌آمیز بود.", token=TokenResponse(access_token=access_token, token_type="bearer"))

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first() if current_user.role == "doctor" else None
    return build_user_response(user=current_user, doctor=doctor, message="اطلاعات کاربر دریافت شد.")

@router.post("/logout")
def logout_user():
    return {"message": "خروج با موفقیت انجام شد."}
