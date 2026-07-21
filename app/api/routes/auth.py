import logging
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.availability import Availability
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.auth import TokenResponse, UserLogin, UserResponse
from app.schemas.user import DoctorOut, UserOut, UserRegister


router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


PERSIAN_DAY_TO_WEEKDAY = {
    "دوشنبه": 0,
    "سه شنبه": 1,
    "سه‌شنبه": 1,
    "چهارشنبه": 2,
    "پنج شنبه": 3,
    "پنج‌شنبه": 3,
    "جمعه": 4,
    "شنبه": 5,
    "یکشنبه": 6,
    "یک‌شنبه": 6,
}


def split_full_name(full_name: str) -> tuple[str, str]:
    cleaned = (full_name or "").strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="نام و نام خانوادگی الزامی است.",
        )

    parts = cleaned.split(maxsplit=1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else "نامشخص"
    return first_name, last_name


def parse_time_str(value: Optional[str], field_name: str = "زمان") -> time:
    if value is None or str(value).strip() == "":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} الزامی است.",
        )

    value = str(value).strip()
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"فرمت ساعت نامعتبر است: {value}. فرمت درست مثل 09:30 است.",
        )


def parse_date_str(value: Optional[str]) -> date:
    if not value:
        return date.today()

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"فرمت تاریخ نامعتبر است: {value}. فرمت درست مثل 2025-01-20 است.",
        )


def validate_time_range(start: time, end: time, title: str) -> None:
    if start >= end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ساعت شروع {title} باید قبل از ساعت پایان باشد.",
        )


def validate_doctor_registration_data(user_data: UserRegister) -> None:
    if user_data.role != "doctor":
        return

    if not user_data.work_days:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="حداقل یک روز کاری برای پزشک الزامی است.",
        )

    invalid_days = [
        day for day in user_data.work_days if day not in PERSIAN_DAY_TO_WEEKDAY
    ]
    if invalid_days:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"روز(های) کاری نامعتبر هستند: {', '.join(invalid_days)}",
        )

    if user_data.work_shift not in ("morning", "afternoon", "both"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="نوع شیفت پزشک نامعتبر است.",
        )

    if user_data.work_shift in ("morning", "both"):
        morning_start = parse_time_str(user_data.morning_start, "ساعت شروع شیفت صبح")
        morning_end = parse_time_str(user_data.morning_end, "ساعت پایان شیفت صبح")
        validate_time_range(morning_start, morning_end, "شیفت صبح")

    if user_data.work_shift in ("afternoon", "both"):
        afternoon_start = parse_time_str(
            user_data.afternoon_start, "ساعت شروع شیفت عصر"
        )
        afternoon_end = parse_time_str(user_data.afternoon_end, "ساعت پایان شیفت عصر")
        validate_time_range(afternoon_start, afternoon_end, "شیفت عصر")


def find_existing_user(
    db: Session, phone: str, national_id: str, email: Optional[str] = None
) -> Optional[User]:
    # اگر ایمیل فرستاده شده بود، آن را هم در شرط OR بررسی کن
    filters = (User.phone == phone) | (User.national_id == national_id)
    if email:
        filters = filters | (User.email == email)
    return db.query(User).filter(filters).first()


def find_existing_doctor(
    db: Session, medical_council_number: Optional[str]
) -> Optional[Doctor]:
    if not medical_council_number:
        return None

    return (
        db.query(Doctor)
        .filter(Doctor.medical_council_number == medical_council_number)
        .first()
    )


def build_user_response(
    user: User,
    doctor: Optional[Doctor] = None,
    message: str = "OK",
    token: Optional[TokenResponse] = None,
) -> UserResponse:
    if doctor:
        user_out = DoctorOut(
            id=user.id,
            name=user.name,
            phone=user.phone,
            email=user.email,  # ایمیل به خروجی ساختاریافته پزشک پاس داده شد
            role=user.role,
            is_active=user.is_active,
            doctor_id=doctor.id,
            medical_council_number=doctor.medical_council_number,
            specialty=doctor.specialty,
            sub_specialty=getattr(doctor, "sub_specialty", None),
            province=getattr(doctor, "province", None),
            city=doctor.city,
            address=getattr(doctor, "address", None),
            latitude=getattr(doctor, "latitude", None),
            longitude=getattr(doctor, "longitude", None),
            bio=getattr(doctor, "bio", None),
            experience_years=getattr(doctor, "experience_years", 0) or 0,
            consultation_fee=getattr(doctor, "consultation_fee", 0) or 0,
            work_shift=getattr(doctor, "work_shift", None),
        )
    else:
        user_out = UserOut(
            id=user.id,
            name=user.name,
            phone=user.phone,
            email=user.email,  # ایمیل به خروجی ساختاریافته کاربر عادی پاس داده شد
            role=user.role,
            is_active=user.is_active,
        )

    return UserResponse(
        message=message,
        user=user_out,
        token=token,
    )


def create_access_token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role),
        token_type="bearer",
    )


def create_doctor_profile(db: Session, user: User, user_data: UserRegister) -> Doctor:
    doctor = Doctor(
        user_id=user.id,
        medical_council_number=user_data.medical_council_number,
        specialty=user_data.specialty,
        sub_specialty=user_data.sub_specialty,
        province=user_data.province,
        city=user_data.city,
        address=user_data.address,
        latitude=user_data.latitude,
        longitude=user_data.longitude,
        bio=user_data.bio,
        experience_years=user_data.experience_years,
        consultation_fee=user_data.consultation_fee,
        work_shift=user_data.work_shift,
    )

    db.add(doctor)
    db.flush()
    return doctor


def add_availability_slot(
    db: Session,
    doctor_id: int,
    slot_date: date,
    start_time: time,
    end_time: time,
) -> None:
    availability = Availability(
        doctor_id=doctor_id,
        date=slot_date,
        start_time=start_time,
        end_time=end_time,
        is_booked=False,
    )
    db.add(availability)


def create_slots_for_range(
    db: Session,
    doctor_id: int,
    slot_date: date,
    start_time: time,
    end_time: time,
    slot_minutes: int = 30,
) -> None:
    current_datetime = datetime.combine(slot_date, start_time)
    end_datetime = datetime.combine(slot_date, end_time)

    while current_datetime + timedelta(minutes=slot_minutes) <= end_datetime:
        slot_start = current_datetime.time()
        slot_end = (current_datetime + timedelta(minutes=slot_minutes)).time()

        add_availability_slot(
            db=db,
            doctor_id=doctor_id,
            slot_date=slot_date,
            start_time=slot_start,
            end_time=slot_end,
        )

        current_datetime += timedelta(minutes=slot_minutes)


def create_doctor_availabilities(
    db: Session,
    doctor_id: int,
    user_data: UserRegister,
    days_count: int = 30,
    slot_minutes: int = 30,
) -> None:
    if user_data.role != "doctor":
        return

    if not user_data.work_days:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="حداقل یک روز کاری برای ایجاد نوبت‌ها الزامی است.",
        )

    start_date = parse_date_str(user_data.schedule_start_date)
    selected_weekdays = {
        PERSIAN_DAY_TO_WEEKDAY[day]
        for day in user_data.work_days
        if day in PERSIAN_DAY_TO_WEEKDAY
    }

    if not selected_weekdays:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="روزهای کاری معتبر نیستند.",
        )

    morning_start = None
    morning_end = None
    afternoon_start = None
    afternoon_end = None

    if user_data.work_shift in ("morning", "both"):
        morning_start = parse_time_str(user_data.morning_start, "ساعت شروع شیفت صبح")
        morning_end = parse_time_str(user_data.morning_end, "ساعت پایان شیفت صبح")

    if user_data.work_shift in ("afternoon", "both"):
        afternoon_start = parse_time_str(
            user_data.afternoon_start, "ساعت شروع شیفت عصر"
        )
        afternoon_end = parse_time_str(user_data.afternoon_end, "ساعت پایان شیفت عصر")

    for day_offset in range(days_count):
        current_date = start_date + timedelta(days=day_offset)

        if current_date.weekday() not in selected_weekdays:
            continue

        if morning_start and morning_end:
            create_slots_for_range(
                db=db,
                doctor_id=doctor_id,
                slot_date=current_date,
                start_time=morning_start,
                end_time=morning_end,
                slot_minutes=slot_minutes,
            )

        if afternoon_start and afternoon_end:
            create_slots_for_range(
                db=db,
                doctor_id=doctor_id,
                slot_date=current_date,
                start_time=afternoon_start,
                end_time=afternoon_end,
                slot_minutes=slot_minutes,
            )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    validate_doctor_registration_data(user_data)

    existing_user = find_existing_user(
        db=db,
        phone=user_data.phone,
        national_id=user_data.national_id,
        email=user_data.email,  # اضافه کردن چک ایمیل در کوئری
    )

    if existing_user:
        if existing_user.phone == user_data.phone:
            detail = "این شماره موبایل قبلاً ثبت شده است."
        elif existing_user.national_id == user_data.national_id:
            detail = "این کد ملی قبلاً ثبت شده است."
        elif user_data.email and existing_user.email == user_data.email:
            detail = "این ایمیل قبلاً ثبت شده است."
        else:
            detail = "این کاربر قبلاً ثبت شده است."

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )

    if user_data.role == "doctor":
        existing_doctor = find_existing_doctor(
            db=db,
            medical_council_number=user_data.medical_council_number,
        )

        if existing_doctor:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="این کد نظام پزشکی قبلاً ثبت شده است.",
            )

    try:
        first_name, last_name = split_full_name(user_data.name)

        user = User(
            name=user_data.name,
            first_name=first_name,
            last_name=last_name,
            national_id=user_data.national_id,
            phone=user_data.phone,
            email=user_data.email,  # فیلد ایمیل در سازنده مدل دیتابیس ست شد
            hashed_password=hash_password(user_data.password),
            role=user_data.role,
            is_active=True,
        )

        db.add(user)
        db.flush()

        doctor = None
        if user_data.role == "doctor":
            doctor = create_doctor_profile(
                db=db,
                user=user,
                user_data=user_data,
            )

            create_doctor_availabilities(
                db=db,
                doctor_id=doctor.id,
                user_data=user_data,
                days_count=30,
                slot_minutes=30,
            )

        db.commit()
        db.refresh(user)

        if doctor:
            db.refresh(doctor)

        token = create_access_token_response(user)

        return build_user_response(
            user=user,
            doctor=doctor,
            message="ثبت‌نام با موفقیت انجام شد.",
            token=token,
        )

    except IntegrityError as exc:
        db.rollback()
        logger.exception("Registration integrity error: %s", exc)

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="اطلاعات وارد شده تکراری است یا با محدودیت‌های دیتابیس سازگار نیست.",
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()
        logger.exception("Registration error: %s", exc)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطای داخلی سرور هنگام ثبت‌نام.",
        )


@router.post("/login", response_model=UserResponse)
def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == user_data.phone).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="شماره موبایل یا رمز عبور اشتباه است.",
        )

    if not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="شماره موبایل یا رمز عبور اشتباه است.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="حساب کاربری شما غیرفعال است.",
        )

    doctor = None
    if user.role == "doctor":
        doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()

    token = create_access_token_response(user)

    return build_user_response(
        user=user,
        doctor=doctor,
        message="ورود موفقیت‌آمیز بود.",
        token=token,
    )


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doctor = None

    if current_user.role == "doctor":
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()

    return build_user_response(
        user=current_user,
        doctor=doctor,
        message="اطلاعات کاربر دریافت شد.",
        token=None,
    )


@router.post("/logout")
def logout_user():
    return {"message": "خروج با موفقیت انجام شد."}
