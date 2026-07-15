from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator


UserRole = Literal["patient", "doctor"]
WorkShift = Literal["morning", "afternoon", "both"]

ALLOWED_WORK_DAYS = {
    "شنبه",
    "یکشنبه",
    "یک‌شنبه",
    "دوشنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنجشنبه",
    "پنج‌شنبه",
    "جمعه",
}


def _validate_time_format(value: str) -> str:
    try:
        datetime.strptime(value, "%H:%M")
    except ValueError as exc:
        raise ValueError("فرمت ساعت باید HH:MM باشد.") from exc

    return value


class UserRegister(BaseModel):
    name: str
    phone: str
    email: Optional[EmailStr] = None
    password: str
    role: UserRole = "patient"

    specialty: Optional[str] = None
    city: Optional[str] = None
    work_shift: Optional[WorkShift] = None
    work_days: Optional[list[str]] = None
    schedule_start_date: Optional[str] = None
    morning_start: Optional[str] = None
    morning_end: Optional[str] = None
    afternoon_start: Optional[str] = None
    afternoon_end: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("نام باید حداقل 3 کاراکتر باشد.")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        value = value.strip()
        if not value.isdigit() or len(value) != 11 or not value.startswith("09"):
            raise ValueError("شماره موبایل نامعتبر است.")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 6:
            raise ValueError("رمز عبور باید حداقل 6 کاراکتر باشد.")
        return value

    @field_validator("specialty", "city")
    @classmethod
    def validate_optional_text_fields(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        value = value.strip()
        return value or None

    @field_validator("schedule_start_date")
    @classmethod
    def validate_schedule_start_date(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        value = value.strip()

        try:
            datetime.strptime(value, "%Y/%m/%d")
        except ValueError as exc:
            raise ValueError("فرمت تاریخ باید YYYY/MM/DD باشد.") from exc

        return value

    @field_validator(
        "morning_start",
        "morning_end",
        "afternoon_start",
        "afternoon_end",
    )
    @classmethod
    def validate_time_fields(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        value = value.strip()
        return _validate_time_format(value)

    @field_validator("work_days")
    @classmethod
    def validate_work_days(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        if value is None:
            return None

        cleaned = [day.strip() for day in value if day and day.strip()]

        if not cleaned:
            raise ValueError("حداقل یک روز کاری باید انتخاب شود.")

        invalid_days = [day for day in cleaned if day not in ALLOWED_WORK_DAYS]
        if invalid_days:
            raise ValueError("برخی از روزهای کاری نامعتبر هستند.")

        return cleaned

    @model_validator(mode="after")
    def validate_doctor_fields(self):
        if self.role != "doctor":
            return self

        if not self.specialty:
            raise ValueError("تخصص پزشک الزامی است.")

        if not self.city:
            raise ValueError("شهر پزشک الزامی است.")

        if not self.work_shift:
            raise ValueError("شیفت کاری پزشک الزامی است.")

        if not self.work_days:
            raise ValueError("روزهای کاری پزشک الزامی است.")

        if not self.schedule_start_date:
            raise ValueError("تاریخ شروع برنامه کاری الزامی است.")

        if self.work_shift in ("morning", "both"):
            if not self.morning_start or not self.morning_end:
                raise ValueError("ساعت شروع و پایان شیفت صبح الزامی است.")

            if self.morning_start >= self.morning_end:
                raise ValueError("ساعت شروع شیفت صبح باید کمتر از پایان باشد.")

        if self.work_shift in ("afternoon", "both"):
            if not self.afternoon_start or not self.afternoon_end:
                raise ValueError("ساعت شروع و پایان شیفت عصر الزامی است.")

            if self.afternoon_start >= self.afternoon_end:
                raise ValueError("ساعت شروع شیفت عصر باید کمتر از پایان باشد.")

        return self


class UserLogin(BaseModel):
    phone: str
    password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("شماره موبایل الزامی است.")

        if not value.isdigit() or len(value) != 11 or not value.startswith("09"):
            raise ValueError("شماره موبایل نامعتبر است.")

        return value

    @field_validator("password")
    @classmethod
    def validate_login_password(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("رمز عبور الزامی است.")

        return value


class UserResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[EmailStr] = None
    role: UserRole
    is_active: bool

    specialty: Optional[str] = None
    city: Optional[str] = None
    work_shift: Optional[WorkShift] = None

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

    model_config = {"from_attributes": True}
