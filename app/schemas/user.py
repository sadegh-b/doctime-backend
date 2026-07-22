import re
from datetime import date, time
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

UserRole = Literal["patient", "doctor", "admin"]
WorkShift = Literal["morning", "afternoon", "both"]


PERSIAN_DIGITS = "".join(chr(1776 + i) for i in range(10))
ARABIC_DIGITS = "".join(chr(1632 + i) for i in range(10))
ENGLISH_DIGITS = "0123456789"

DIGIT_TRANSLATION_TABLE = str.maketrans(
    PERSIAN_DIGITS + ARABIC_DIGITS,
    ENGLISH_DIGITS + ENGLISH_DIGITS,
)


def normalize_digits(value: str) -> str:
    if value is None:
        return value
    return value.translate(DIGIT_TRANSLATION_TABLE)


def normalize_spaces(value: str) -> str:
    if value is None:
        return value
    return " ".join(value.replace("\u200c", " ").split())


def is_valid_iranian_national_id(value: str) -> bool:
    if not re.fullmatch(r"\d{10}", value):
        return False

    if len(set(value)) == 1:
        return False

    check = int(value[9])
    total = sum(int(value[i]) * (10 - i) for i in range(9))
    remainder = total % 11

    if remainder < 2:
        return check == remainder

    return check == 11 - remainder


class UserRegister(BaseModel):
    name: str
    phone: str
    password: str
    national_id: str
    email: Optional[str] = None

    role: UserRole = "patient"

    medical_council_number: Optional[str] = None
    specialty: Optional[str] = None
    sub_specialty: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    bio: Optional[str] = None
    experience_years: int = 0
    consultation_fee: int = 0

    work_shift: Optional[WorkShift] = None
    work_days: Optional[List[str]] = None
    schedule_start_date: Optional[str] = None

    morning_start: Optional[str] = None
    morning_end: Optional[str] = None
    afternoon_start: Optional[str] = None
    afternoon_end: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = normalize_spaces(value)
        if len(value) < 2:
            raise ValueError("نام باید حداقل ۲ کاراکتر باشد.")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        value = normalize_digits(value.strip())
        if not re.fullmatch(r"09\d{9}", value):
            raise ValueError("شماره موبایل باید با 09 شروع شود و دقیقاً ۱۱ رقم باشد.")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 6:
            raise ValueError("رمز عبور باید حداقل ۶ کاراکتر باشد.")
        return value

    @field_validator("national_id")
    @classmethod
    def validate_national_id(cls, value: str) -> str:
        value = normalize_digits(value.strip())
        if not is_valid_iranian_national_id(value):
            raise ValueError("کد ملی معتبر نیست.")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        value = value.strip().lower()
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, value):
            raise ValueError("فرمت ایمیل وارد شده معتبر نیست.")
        return value

    @field_validator("medical_council_number")
    @classmethod
    def validate_medical_council_number(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        value = normalize_digits(value.strip())
        if not value:
            return None

        if not re.fullmatch(r"\d{4,10}", value):
            raise ValueError("کد نظام پزشکی باید بین ۴ تا ۱۰ رقم باشد.")

        return value

    @field_validator("experience_years")
    @classmethod
    def validate_experience_years(cls, value: int) -> int:
        if value < 0:
            raise ValueError("سابقه کار نمی‌تواند منفی باشد.")
        if value > 80:
            raise ValueError("سابقه کار معتبر نیست.")
        return value

    @field_validator("consultation_fee")
    @classmethod
    def validate_consultation_fee(cls, value: int) -> int:
        if value < 0:
            raise ValueError("هزینه ویزیت نمی‌تواند منفی باشد.")
        return value

    @field_validator("work_days")
    @classmethod
    def validate_work_days(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value

        allowed_days = {
            "شنبه",
            "یکشنبه",
            "یک‌شنبه",
            "دوشنبه",
            "سه شنبه",
            "سه‌شنبه",
            "چهارشنبه",
            "پنج شنبه",
            "پنج‌شنبه",
            "جمعه",
        }

        cleaned_days = []
        for day in value:
            day = normalize_spaces(day)
            if day not in allowed_days:
                raise ValueError(f"روز کاری نامعتبر است: {day}")
            cleaned_days.append(day)

        return cleaned_days

    @field_validator(
        "schedule_start_date",
        "morning_start",
        "morning_end",
        "afternoon_start",
        "afternoon_end",
    )
    @classmethod
    def normalize_optional_string(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        value = normalize_digits(value.strip())
        return value or None

    @model_validator(mode="after")
    def validate_doctor_fields(self):
        if self.role != "doctor":
            return self

        if not self.medical_council_number:
            raise ValueError("کد نظام پزشکی برای پزشک الزامی است.")

        if not self.specialty:
            raise ValueError("تخصص برای پزشک الزامی است.")

        if not self.province:
            raise ValueError("استان برای پزشک الزامی است.")

        if not self.city:
            raise ValueError("شهر برای پزشک الزامی است.")

        if not self.address:
            raise ValueError("آدرس مطب برای پزشک الزامی است.")

        if not self.work_shift:
            raise ValueError("شیفت کاری برای پزشک الزامی است.")

        if not self.work_days:
            raise ValueError("روزهای کاری برای پزشک الزامی است.")

        if self.work_shift in ("morning", "both"):
            if not self.morning_start or not self.morning_end:
                raise ValueError("ساعت شروع و پایان شیفت صبح الزامی است.")

        if self.work_shift in ("afternoon", "both"):
            if not self.afternoon_start or not self.afternoon_end:
                raise ValueError("ساعت شروع و پایان شیفت عصر الزامی است.")

        return self


class UserOut(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str] = None
    role: UserRole
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class DoctorOut(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str] = None
    role: UserRole = "doctor"
    is_active: bool = True

    doctor_id: Optional[int] = None
    medical_council_number: Optional[str] = None
    specialty: Optional[str] = None
    sub_specialty: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    bio: Optional[str] = None
    experience_years: int = 0
    consultation_fee: int = 0
    work_shift: Optional[WorkShift] = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        value = normalize_spaces(value)
        if len(value) < 2:
            raise ValueError("نام باید حداقل ۲ کاراکتر باشد.")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        value = normalize_digits(value.strip())
        if not re.fullmatch(r"09\d{9}", value):
            raise ValueError("شماره موبایل باید با 09 شروع شود و دقیقاً ۱۱ رقم باشد.")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        value = value.strip().lower()
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, value):
            raise ValueError("فرمت ایمیل وارد شده معتبر نیست.")
        return value


class DoctorUpdate(BaseModel):
    specialty: Optional[str] = None
    sub_specialty: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    bio: Optional[str] = None
    experience_years: Optional[int] = None
    consultation_fee: Optional[int] = None
    work_shift: Optional[WorkShift] = None

    @field_validator("specialty", "sub_specialty", "province", "city", "address", "bio")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = normalize_spaces(value)
        return value or None

    @field_validator("experience_years")
    @classmethod
    def validate_experience_years(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        if value < 0:
            raise ValueError("سابقه کار نمی‌تواند منفی باشد.")
        if value > 80:
            raise ValueError("سابقه کار معتبر نیست.")
        return value

    @field_validator("consultation_fee")
    @classmethod
    def validate_consultation_fee(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        if value < 0:
            raise ValueError("هزینه ویزیت نمی‌تواند منفی باشد.")
        return value

    model_config = ConfigDict(from_attributes=True)


class AvailabilityOut(BaseModel):
    id: int
    doctor_id: int
    date: date
    start_time: time
    end_time: time
    is_available: bool
    is_booked: bool

    model_config = ConfigDict(from_attributes=True)
