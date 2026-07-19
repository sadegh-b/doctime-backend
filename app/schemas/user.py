import re
from typing import Literal

from pydantic import BaseModel, EmailStr, field_validator, model_validator


UserRole = Literal["patient", "doctor"]
WorkShift = Literal["morning", "afternoon", "both"]


PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
ENGLISH_DIGITS = "0123456789"

DIGIT_TRANSLATION_TABLE = str.maketrans(
    PERSIAN_DIGITS + ARABIC_DIGITS,
    ENGLISH_DIGITS + ENGLISH_DIGITS,
)


CANONICAL_WORK_DAYS = {
    "شنبه",
    "یکشنبه",
    "دوشنبه",
    "سه شنبه",
    "چهارشنبه",
    "پنج شنبه",
    "جمعه",
}


def normalize_digits(value: str) -> str:
    return value.translate(DIGIT_TRANSLATION_TABLE)


def normalize_spaces(value: str) -> str:
    return " ".join(
        value.replace("\u200c", " ")
        .replace("\u200f", "")
        .replace("\u200e", "")
        .split()
    )


def normalize_work_day(value: str) -> str:
    return normalize_spaces(value.strip())


def validate_time_format(value: str) -> str:
    if not re.fullmatch(r"\d{2}:\d{2}", value):
        raise ValueError("فرمت ساعت باید HH:MM باشد.")

    hour, minute = map(int, value.split(":"))

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("ساعت واردشده معتبر نیست.")

    return value


def is_valid_iranian_national_id(value: str) -> bool:
    if not re.fullmatch(r"\d{10}", value):
        return False

    if len(set(value)) == 1:
        return False

    digits = [int(character) for character in value]

    weighted_sum = sum(
        digits[index] * (10 - index)
        for index in range(9)
    )

    remainder = weighted_sum % 11
    expected_check_digit = (
        remainder
        if remainder < 2
        else 11 - remainder
    )

    return digits[9] == expected_check_digit


class UserRegister(BaseModel):
    first_name: str
    last_name: str
    national_id: str
    phone: str
    email: EmailStr | None = None
    password: str
    role: UserRole = "patient"

    # فیلدهای اختصاصی پزشک
    specialty: str | None = None
    province: str | None = None
    city: str | None = None
    address: str | None = None
    bio: str | None = None
    experience_years: int = 0
    consultation_fee: int = 0

    work_shift: WorkShift | None = None
    work_days: list[str] | None = None

    morning_start: str | None = None
    morning_end: str | None = None
    afternoon_start: str | None = None
    afternoon_end: str | None = None

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, value: str) -> str:
        value = normalize_spaces(value)

        if len(value) < 2:
            raise ValueError("نام باید حداقل ۲ کاراکتر باشد.")

        if len(value) > 60:
            raise ValueError("نام نمی‌تواند بیشتر از ۶۰ کاراکتر باشد.")

        return value

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, value: str) -> str:
        value = normalize_spaces(value)

        if len(value) < 2:
            raise ValueError("نام خانوادگی باید حداقل ۲ کاراکتر باشد.")

        if len(value) > 80:
            raise ValueError(
                "نام خانوادگی نمی‌تواند بیشتر از ۸۰ کاراکتر باشد."
            )

        return value

    @field_validator("national_id")
    @classmethod
    def validate_national_id(cls, value: str) -> str:
        value = normalize_digits(value.strip())

        if not re.fullmatch(r"\d{10}", value):
            raise ValueError("کد ملی باید دقیقاً ۱۰ رقم باشد.")

        if not is_valid_iranian_national_id(value):
            raise ValueError("کد ملی واردشده معتبر نیست.")

        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        value = normalize_digits(value.strip())

        if not re.fullmatch(r"09\d{9}", value):
            raise ValueError(
                "شماره موبایل باید ۱۱ رقم و با 09 شروع شود."
            )

        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 6:
            raise ValueError("رمز عبور باید حداقل ۶ کاراکتر باشد.")

        if len(value) > 128:
            raise ValueError(
                "رمز عبور نمی‌تواند بیشتر از ۱۲۸ کاراکتر باشد."
            )

        return value

    @field_validator("specialty")
    @classmethod
    def validate_specialty(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = normalize_spaces(value)

        if not value:
            return None

        if len(value) > 120:
            raise ValueError(
                "تخصص نمی‌تواند بیشتر از ۱۲۰ کاراکتر باشد."
            )

        return value

    @field_validator("province", "city")
    @classmethod
    def validate_location_fields(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = normalize_spaces(value)

        if not value:
            return None

        if len(value) > 120:
            raise ValueError(
                "نام استان یا شهر نمی‌تواند بیشتر از ۱۲۰ کاراکتر باشد."
            )

        return value

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = normalize_spaces(value)

        if not value:
            return None

        if len(value) > 500:
            raise ValueError(
                "آدرس نمی‌تواند بیشتر از ۵۰۰ کاراکتر باشد."
            )

        return value

    @field_validator("bio")
    @classmethod
    def validate_bio(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            return None

        if len(value) > 2000:
            raise ValueError(
                "توضیحات پزشک نمی‌تواند بیشتر از ۲۰۰۰ کاراکتر باشد."
            )

        return value

    @field_validator("experience_years")
    @classmethod
    def validate_experience_years(cls, value: int) -> int:
        if not (0 <= value <= 80):
            raise ValueError(
                "سابقه کاری باید بین صفر تا ۸۰ سال باشد."
            )

        return value

    @field_validator("consultation_fee")
    @classmethod
    def validate_consultation_fee(cls, value: int) -> int:
        if not (0 <= value <= 100_000_000):
            raise ValueError("هزینه ویزیت نامعتبر است.")

        return value

    @field_validator(
        "morning_start",
        "morning_end",
        "afternoon_start",
        "afternoon_end",
    )
    @classmethod
    def validate_time_fields(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = normalize_digits(value.strip())

        if not value:
            return None

        return validate_time_format(value)

    @field_validator("work_days")
    @classmethod
    def validate_work_days(
        cls,
        value: list[str] | None,
    ) -> list[str] | None:
        if value is None:
            return None

        cleaned_days: list[str] = []

        for raw_day in value:
            if not raw_day:
                continue

            normalized_day = normalize_work_day(raw_day)

            if not normalized_day:
                continue

            if normalized_day not in CANONICAL_WORK_DAYS:
                raise ValueError(
                    f"روز کاری نامعتبر است: {raw_day}"
                )

            if normalized_day not in cleaned_days:
                cleaned_days.append(normalized_day)

        if not cleaned_days:
            raise ValueError(
                "حداقل یک روز کاری باید انتخاب شود."
            )

        return cleaned_days

    @model_validator(mode="after")
    def validate_doctor_fields(self):
        if self.role != "doctor":
            return self

        if not self.specialty:
            raise ValueError("تخصص پزشک الزامی است.")

        if not self.province:
            raise ValueError("استان پزشک الزامی است.")

        if not self.city:
            raise ValueError("شهر پزشک الزامی است.")

        if not self.address:
            raise ValueError("آدرس پزشک الزامی است.")

        if not self.work_shift:
            raise ValueError("شیفت کاری پزشک الزامی است.")

        if not self.work_days:
            raise ValueError("روزهای کاری پزشک الزامی است.")

        if self.work_shift in ("morning", "both"):
            if not self.morning_start or not self.morning_end:
                raise ValueError(
                    "ساعت شروع و پایان شیفت صبح الزامی است."
                )

            if self.morning_start >= self.morning_end:
                raise ValueError(
                    "ساعت شروع شیفت صبح باید کمتر از ساعت پایان باشد."
                )

        if self.work_shift in ("afternoon", "both"):
            if not self.afternoon_start or not self.afternoon_end:
                raise ValueError(
                    "ساعت شروع و پایان شیفت عصر الزامی است."
                )

            if self.afternoon_start >= self.afternoon_end:
                raise ValueError(
                    "ساعت شروع شیفت عصر باید کمتر از ساعت پایان باشد."
                )

        return self


class UserLogin(BaseModel):
    phone: str
    password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        value = normalize_digits(value.strip())

        if not re.fullmatch(r"09\d{9}", value):
            raise ValueError("شماره موبایل نامعتبر است.")

        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value:
            raise ValueError("رمز عبور الزامی است.")

        if len(value) < 6:
            raise ValueError(
                "رمز عبور باید حداقل ۶ کاراکتر باشد."
            )

        return value


class UserResponse(BaseModel):
    id: int

    # برای سازگاری با فرانت‌اند فعلی حفظ شده است.
    name: str

    first_name: str
    last_name: str

    phone: str
    email: EmailStr | None = None
    role: UserRole
    is_active: bool

    specialty: str | None = None
    province: str | None = None
    city: str | None = None
    address: str | None = None
    bio: str | None = None
    experience_years: int | None = None
    consultation_fee: int | None = None
    work_shift: WorkShift | None = None

    model_config = {
        "from_attributes": True,
    }


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

    model_config = {
        "from_attributes": True,
    }
