# Path: backend/app/schemas/auth.py

from typing import Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re
from app.schemas.user import DoctorOut, UserOut


class OTPRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        value = value.strip()
        # نرمال‌سازی ارقام فارسی و عربی به انگلیسی
        persian_digits = "".join(chr(1776 + i) for i in range(10))
        arabic_digits = "".join(chr(1632 + i) for i in range(10))
        english_digits = "0123456789"
        translation_table = str.maketrans(
            persian_digits + arabic_digits,
            english_digits + english_digits,
        )
        normalized = value.translate(translation_table)

        if not re.fullmatch(r"09\d{9}", normalized):
            raise ValueError("شماره موبایل باید با 09 شروع شده و دقیقاً ۱۱ رقم باشد.")
        return normalized


class OTPVerify(BaseModel):
    phone: str
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"\d{4,6}", value):
            raise ValueError("کد تایید باید بین ۴ تا ۶ رقم عددی باشد.")
        return value


class UserLogin(BaseModel):
    """مدل مورد نیاز برای ورود کاربر که در خطا مفقود شده بود"""
    phone: str
    password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        # استفاده از همان منطق نرمال‌سازی برای لاگین
        value = value.strip()
        persian_digits = "".join(chr(1776 + i) for i in range(10))
        arabic_digits = "".join(chr(1632 + i) for i in range(10))
        english_digits = "0123456789"
        translation_table = str.maketrans(
            persian_digits + arabic_digits,
            english_digits + english_digits,
        )
        return value.translate(translation_table)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    message: str
    user: Union[DoctorOut, UserOut]
    token: Optional[TokenResponse] = None

    model_config = ConfigDict(from_attributes=True)
