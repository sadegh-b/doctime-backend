import logging
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
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


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

logger = logging.getLogger(__name__)


PERSIAN_DAY_TO_WEEKDAY = {
    "دوشنبه": 0,
    "سه شنبه": 1,
    "چهارشنبه": 2,
    "پنج شنبه": 3,
    "جمعه": 4,
    "شنبه": 5,
    "یکشنبه": 6,
}


def normalize_spaces(value: str) -> str:
    return " ".join(
        value.replace("\u200c", " ")
        .replace("\u200f", "")
        .replace("\u200e", "")
        .split()
    )


class UpdateProfileInput(BaseModel):
    first_name: str | None = None
    last_name: str | None = None

    specialty: str | None = None
    province: str | None = None
    city: str | None = None
    address: str | None = None
    bio: str | None = None

    @field_validator(
        "first_name",
        "last_name",
        "specialty",
        "province",
        "city",
        "address",
        "bio",
    )
    @classmethod
    def clean_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


def parse_time_str(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"فرمت ساعت نامعتبر است: {value}",
        ) from exc


def create_time_slots(
    db: Session,
    doctor_id: int,
    target_date: date,
    start_at: time,
    end_at: time,
    slot_minutes: int = 30,
) -> None:
    current_datetime = datetime.combine(
        target_date,
        start_at,
    )

    end_datetime = datetime.combine(
        target_date,
        end_at,
    )

    if current_datetime >= end_datetime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ساعت شروع باید از ساعت پایان کمتر باشد.",
        )

    while current_datetime < end_datetime:
        next_datetime = current_datetime + timedelta(
            minutes=slot_minutes
        )

        if next_datetime > end_datetime:
            break

        existing_slot = (
            db.query(Availability)
            .filter(
                Availability.doctor_id == doctor_id,
                Availability.date == target_date,
                Availability.start_time
                == current_datetime.time(),
                Availability.end_time
                == next_datetime.time(),
            )
            .first()
        )

        if not existing_slot:
            db.add(
                Availability(
                    doctor_id=doctor_id,
                    date=target_date,
                    start_time=current_datetime.time(),
                    end_time=next_datetime.time(),
                    is_available=True,
                    is_booked=False,
                )
            )

        current_datetime = next_datetime


def create_doctor_availability(
    db: Session,
    doctor_id: int,
    work_shift: WorkShift,
    work_days: list[str],
    morning_start: str | None = None,
    morning_end: str | None = None,
    afternoon_start: str | None = None,
    afternoon_end: str | None = None,
    days_ahead: int = 30,
    slot_minutes: int = 30,
) -> None:
    # تاریخ شروع برنامه دیگر از کاربر گرفته نمی‌شود.
    # برنامه از تاریخ امروز سرور ایجاد می‌شود.
    start_date = date.today()

    selected_weekdays: set[int] = set()

    for raw_day in work_days:
        normalized_day = normalize_spaces(raw_day)

        weekday_number = PERSIAN_DAY_TO_WEEKDAY.get(
            normalized_day
        )

        if weekday_number is None:
            logger.warning(
                "Invalid work day received: %s",
                raw_day,
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"روز کاری نامعتبر است: {raw_day}",
            )

        selected_weekdays.add(weekday_number)

    if not selected_weekdays:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="حداقل یک روز کاری باید انتخاب شود.",
        )

    morning_range: tuple[time, time] | None = None
    afternoon_range: tuple[time, time] | None = None

    if work_shift in ("morning", "both"):
        if not morning_start or not morning_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ساعت شیفت صبح کامل نیست.",
            )

        morning_range = (
            parse_time_str(morning_start),
            parse_time_str(morning_end),
        )

    if work_shift in ("afternoon", "both"):
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

        if morning_range is not None:
            create_time_slots(
                db=db,
                doctor_id=doctor_id,
                target_date=target_date,
                start_at=morning_range[0],
                end_at=morning_range[1],
                slot_minutes=slot_minutes,
            )

        if afternoon_range is not None:
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
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        specialty=(
            doctor_profile.specialty
            if doctor_profile
            else None
        ),
        province=(
            doctor_profile.province
            if doctor_profile
            else None
        ),
        city=(
            doctor_profile.city
            if doctor_profile
            else None
        ),
        address=(
            doctor_profile.address
            if doctor_profile
            else None
        ),
        bio=(
            doctor_profile.bio
            if doctor_profile
            else None
        ),
        experience_years=(
            doctor_profile.experience_years
            if doctor_profile
            else None
        ),
        consultation_fee=(
            doctor_profile.consultation_fee
            if doctor_profile
            else None
        ),
        work_shift=(
            doctor_profile.work_shift
            if doctor_profile
            else None
        ),
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    try:
        existing_phone = (
            db.query(User)
            .filter(User.phone == user_data.phone)
            .first()
        )

        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "کاربری با این شماره موبایل قبلاً "
                    "ثبت شده است."
                ),
            )

        existing_national_id = (
            db.query(User)
            .filter(
                User.national_id == user_data.national_id
            )
            .first()
        )

        if existing_national_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="این کد ملی قبلاً ثبت شده است.",
            )

        if user_data.email:
            existing_email = (
                db.query(User)
                .filter(User.email == user_data.email)
                .first()
            )

            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="این ایمیل قبلاً ثبت شده است.",
                )

        full_name = (
            f"{user_data.first_name} "
            f"{user_data.last_name}"
        ).strip()

        hashed_password = hash_password(
            user_data.password
        )

        new_user = User(
            name=full_name,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            national_id=user_data.national_id,
            phone=user_data.phone,
            email=user_data.email,
            hashed_password=hashed_password,
            role=user_data.role,
            is_active=True,
        )

        db.add(new_user)
        db.flush()

        doctor_profile: Doctor | None = None

        if user_data.role == "doctor":
            if not user_data.specialty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="تخصص پزشک الزامی است.",
                )

            if not user_data.province:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="استان پزشک الزامی است.",
                )

            if not user_data.city:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="شهر پزشک الزامی است.",
                )

            if not user_data.address:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="آدرس پزشک الزامی است.",
                )

            if not user_data.work_shift:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="شیفت کاری پزشک الزامی است.",
                )

            if not user_data.work_days:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "حداقل یک روز کاری باید "
                        "انتخاب شود."
                    ),
                )

            doctor_profile = Doctor(
                user_id=new_user.id,
                specialty=user_data.specialty,
                work_shift=user_data.work_shift,
                province=user_data.province,
                city=user_data.city,
                address=user_data.address,
                bio=user_data.bio,
                experience_years=user_data.experience_years,
                consultation_fee=user_data.consultation_fee,
            )

            db.add(doctor_profile)
            db.flush()

            create_doctor_availability(
                db=db,
                doctor_id=doctor_profile.id,
                work_shift=user_data.work_shift,
                work_days=user_data.work_days,
                morning_start=user_data.morning_start,
                morning_end=user_data.morning_end,
                afternoon_start=user_data.afternoon_start,
                afternoon_end=user_data.afternoon_end,
            )

        db.commit()

        db.refresh(new_user)

        if doctor_profile is not None:
            db.refresh(doctor_profile)

        access_token = create_access_token(
            subject=new_user.id,
            role=new_user.role,
        )

        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=build_user_response(
                new_user,
                doctor_profile,
            ),
        )

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError as exc:
        db.rollback()

        logger.exception(
            "Database integrity error during registration. "
            "phone=%s national_id=%s",
            user_data.phone,
            user_data.national_id,
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "شماره موبایل، ایمیل یا کد ملی قبلاً "
                "ثبت شده است."
            ),
        ) from exc

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Registration failed. phone=%s role=%s error=%s",
            user_data.phone,
            user_data.role,
            exc,
        )

        # جزئیات خطای داخلی نباید برای کاربر production نمایش داده شود.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطای داخلی سرور هنگام ثبت‌نام رخ داد.",
        ) from exc


@router.post(
    "/login",
    response_model=AuthResponse,
)
def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.phone == user_data.phone)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="شماره موبایل یا رمز عبور اشتباه است.",
        )

    if not verify_password(
        user_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="شماره موبایل یا رمز عبور اشتباه است.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="حساب کاربری غیرفعال است.",
        )

    doctor_profile: Doctor | None = None

    if user.role == "doctor":
        doctor_profile = (
            db.query(Doctor)
            .filter(Doctor.user_id == user.id)
            .first()
        )

    access_token = create_access_token(
        subject=user.id,
        role=user.role,
    )

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=build_user_response(
            user,
            doctor_profile,
        ),
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doctor_profile: Doctor | None = None

    if current_user.role == "doctor":
        doctor_profile = (
            db.query(Doctor)
            .filter(
                Doctor.user_id == current_user.id
            )
            .first()
        )

    return build_user_response(
        current_user,
        doctor_profile,
    )


@router.patch(
    "/me",
    response_model=UserResponse,
)
def update_profile(
    payload: UpdateProfileInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doctor_profile: Doctor | None = None

    try:
        if payload.first_name is not None:
            first_name = normalize_spaces(
                payload.first_name
            )

            if len(first_name) < 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "نام باید حداقل ۲ کاراکتر باشد."
                    ),
                )

            current_user.first_name = first_name

        if payload.last_name is not None:
            last_name = normalize_spaces(
                payload.last_name
            )

            if len(last_name) < 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "نام خانوادگی باید حداقل "
                        "۲ کاراکتر باشد."
                    ),
                )

            current_user.last_name = last_name

        # ستون قدیمی name را هماهنگ نگه می‌داریم.
        current_user.name = (
            f"{current_user.first_name} "
            f"{current_user.last_name}"
        ).strip()

        if current_user.role == "doctor":
            doctor_profile = (
                db.query(Doctor)
                .filter(
                    Doctor.user_id == current_user.id
                )
                .first()
            )

            if not doctor_profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="پروفایل پزشک پیدا نشد.",
                )

            if payload.specialty is not None:
                specialty = normalize_spaces(
                    payload.specialty
                )

                if not specialty:
                    raise HTTPException(
                        status_code=(
                            status.HTTP_400_BAD_REQUEST
                        ),
                        detail=(
                            "تخصص پزشک نمی‌تواند "
                            "خالی باشد."
                        ),
                    )

                doctor_profile.specialty = specialty

            if payload.province is not None:
                province = normalize_spaces(
                    payload.province
                )

                if not province:
                    raise HTTPException(
                        status_code=(
                            status.HTTP_400_BAD_REQUEST
                        ),
                        detail=(
                            "استان پزشک نمی‌تواند "
                            "خالی باشد."
                        ),
                    )

                doctor_profile.province = province

            if payload.city is not None:
                city = normalize_spaces(
                    payload.city
                )

                if not city:
                    raise HTTPException(
                        status_code=(
                            status.HTTP_400_BAD_REQUEST
                        ),
                        detail=(
                            "شهر پزشک نمی‌تواند "
                            "خالی باشد."
                        ),
                    )

                doctor_profile.city = city

            if payload.address is not None:
                address = payload.address.strip()

                if not address:
                    raise HTTPException(
                        status_code=(
                            status.HTTP_400_BAD_REQUEST
                        ),
                        detail=(
                            "آدرس پزشک نمی‌تواند "
                            "خالی باشد."
                        ),
                    )

                doctor_profile.address = address

            if payload.bio is not None:
                doctor_profile.bio = (
                    payload.bio.strip() or None
                )

        db.commit()
        db.refresh(current_user)

        if doctor_profile is not None:
            db.refresh(doctor_profile)

        return build_user_response(
            current_user,
            doctor_profile,
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Profile update failed. user_id=%s error=%s",
            current_user.id,
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "خطای داخلی هنگام ویرایش پروفایل "
                "رخ داد."
            ),
        ) from exc
