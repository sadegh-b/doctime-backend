import logging
from datetime import date, datetime, time, timedelta

import jdatetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.availability import Availability
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.user import (
    AuthResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    WorkShift,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

PERSIAN_DAY_TO_WEEKDAY = {
    "دوشنبه": 0,
    "سه‌شنبه": 1,
    "چهارشنبه": 2,
    "پنجشنبه": 3,
    "پنج‌شنبه": 3,
    "جمعه": 4,
    "شنبه": 5,
    "یکشنبه": 6,
    "یک‌شنبه": 6,
}


def parse_time_str(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"فرمت ساعت نامعتبر است: {value}",
        ) from exc


def parse_jalali_to_gregorian(value: str) -> date:
    try:
        year, month, day = map(int, value.split("/"))
        return jdatetime.date(year, month, day).togregorian()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="تاریخ شمسی نامعتبر است.",
        ) from exc


def create_time_slots(
    db: Session,
    doctor_id: int,
    target_date: date,
    start_at: time,
    end_at: time,
    slot_minutes: int = 30,
) -> None:
    current_dt = datetime.combine(target_date, start_at)
    end_dt = datetime.combine(target_date, end_at)

    if current_dt >= end_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ساعت شروع باید از ساعت پایان کمتر باشد.",
        )

    while current_dt < end_dt:
        next_dt = current_dt + timedelta(minutes=slot_minutes)

        if next_dt > end_dt:
            break

        exists = (
            db.query(Availability)
            .filter(
                Availability.doctor_id == doctor_id,
                Availability.date == target_date,
                Availability.start_time == current_dt.time(),
                Availability.end_time == next_dt.time(),
            )
            .first()
        )

        if not exists:
            db.add(
                Availability(
                    doctor_id=doctor_id,
                    date=target_date,
                    start_time=current_dt.time(),
                    end_time=next_dt.time(),
                    is_available=True,
                    is_booked=False,
                )
            )

        current_dt = next_dt


def create_doctor_availability(
    db: Session,
    doctor_id: int,
    work_shift: WorkShift,
    work_days: list[str],
    schedule_start_date: str,
    morning_start: str | None = None,
    morning_end: str | None = None,
    afternoon_start: str | None = None,
    afternoon_end: str | None = None,
    days_ahead: int = 30,
    slot_minutes: int = 30,
) -> None:
    start_date = parse_jalali_to_gregorian(schedule_start_date)

    try:
        selected_weekdays = {PERSIAN_DAY_TO_WEEKDAY[day] for day in work_days}
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="یکی از روزهای کاری نامعتبر است.",
        ) from exc

    morning_range = None
    afternoon_range = None

    if work_shift in {"morning", "both"}:
        if not morning_start or not morning_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ساعت شیفت صبح کامل نیست.",
            )
        morning_range = (parse_time_str(morning_start), parse_time_str(morning_end))

    if work_shift in {"afternoon", "both"}:
        if not afternoon_start or not afternoon_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ساعت شیفت عصر کامل نیست.",
            )
        afternoon_range = (
            parse_time_str(afternoon_start),
            parse_time_str(afternoon_end),
        )

    for offset in range(days_ahead):
        target_date = start_date + timedelta(days=offset)

        if target_date.weekday() not in selected_weekdays:
            continue

        if morning_range:
            create_time_slots(
                db=db,
                doctor_id=doctor_id,
                target_date=target_date,
                start_at=morning_range[0],
                end_at=morning_range[1],
                slot_minutes=slot_minutes,
            )

        if afternoon_range:
            create_time_slots(
                db=db,
                doctor_id=doctor_id,
                target_date=target_date,
                start_at=afternoon_range[0],
                end_at=afternoon_range[1],
                slot_minutes=slot_minutes,
            )


def build_user_response(
    user: User,
    doctor_profile: Doctor | None = None,
) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        phone=user.phone,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        specialty=doctor_profile.specialty if doctor_profile else None,
        city=doctor_profile.city if doctor_profile else None,
        work_shift=doctor_profile.work_shift if doctor_profile else None,
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    try:
        existing_phone = db.query(User).filter(User.phone == user_data.phone).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="کاربری با این شماره موبایل قبلاً ثبت شده است.",
            )

        if user_data.email:
            existing_email = db.query(User).filter(User.email == user_data.email).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="این ایمیل قبلاً ثبت شده است.",
                )

        new_user = User(
            name=user_data.name,
            phone=user_data.phone,
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
            role=user_data.role,
            is_active=True,
        )
        db.add(new_user)
        db.flush()

        doctor_profile = None

        if user_data.role == "doctor":
            specialty = (user_data.specialty or "").strip()
            city = (user_data.city or "").strip()

            if not specialty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="تخصص پزشک الزامی است.",
                )

            if not city:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="شهر پزشک الزامی است.",
                )

            if not user_data.work_shift:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="شیفت کاری پزشک الزامی است.",
                )

            if not user_data.work_days:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="حداقل یک روز کاری باید انتخاب شود.",
                )

            if not user_data.schedule_start_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="تاریخ شروع برنامه کاری الزامی است.",
                )

            doctor_profile = Doctor(
                user_id=new_user.id,
                specialty=specialty,
                work_shift=user_data.work_shift,
                city=city,
                experience_years=0,
                consultation_fee=0,
            )
            db.add(doctor_profile)
            db.flush()

            create_doctor_availability(
                db=db,
                doctor_id=doctor_profile.id,
                work_shift=user_data.work_shift,
                work_days=user_data.work_days,
                schedule_start_date=user_data.schedule_start_date,
                morning_start=user_data.morning_start,
                morning_end=user_data.morning_end,
                afternoon_start=user_data.afternoon_start,
                afternoon_end=user_data.afternoon_end,
            )

        db.commit()
        db.refresh(new_user)

        if doctor_profile:
            db.refresh(doctor_profile)

        access_token = create_access_token(
            subject=new_user.id,
            role=new_user.role,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": build_user_response(new_user, doctor_profile),
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        logger.exception(
            "Registration failed. phone=%s role=%s",
            user_data.phone,
            user_data.role,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطای داخلی هنگام ثبت‌نام کاربر رخ داد.",
        )


@router.post("/login", response_model=AuthResponse)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == user_credentials.phone).first()

    if not user or not verify_password(
        user_credentials.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="شماره موبایل یا رمز عبور اشتباه است.",
        )

    doctor_profile = None
    if user.role == "doctor":
        doctor_profile = db.query(Doctor).filter(Doctor.user_id == user.id).first()

    access_token = create_access_token(
        subject=user.id,
        role=user.role,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": build_user_response(user, doctor_profile),
    }


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doctor_profile = None

    if current_user.role == "doctor":
        doctor_profile = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()

    return build_user_response(current_user, doctor_profile)
