# app/services/auth_service.py

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User, UserRole


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    دریافت کاربر براساس شناسه.

    Args:
        db: نشست دیتابیس SQLAlchemy
        user_id: شناسه کاربر

    Returns:
        User | None
    """
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_phone(db: Session, phone: str) -> Optional[User]:
    """
    دریافت کاربر براساس شماره موبایل.

    شماره موبایل باید پیش از فراخوانی، توسط schema یا route نرمال‌سازی شده باشد.

    Args:
        db: نشست دیتابیس SQLAlchemy
        phone: شماره موبایل کاربر

    Returns:
        User | None
    """
    normalized_phone = phone.strip()

    return db.query(User).filter(User.phone == normalized_phone).first()


def is_phone_registered(db: Session, phone: str) -> bool:
    """
    بررسی می‌کند شماره موبایل قبلاً ثبت‌نام شده است یا نه.
    """
    return get_user_by_phone(db, phone) is not None


def create_user(
    db: Session,
    *,
    phone: str,
    password: str,
    first_name: str,
    last_name: str,
    role: UserRole = UserRole.PATIENT,
    is_active: bool = True,
) -> User:
    """
    ایجاد کاربر جدید.

    هش کردن رمز عبور فقط در بک‌اند انجام می‌شود.
    هرگز password خام را در دیتابیس ذخیره نکن.

    Raises:
        ValueError: اگر شماره موبایل یا اطلاعات ضروری نامعتبر باشد.
    """
    normalized_phone = phone.strip()
    normalized_first_name = first_name.strip()
    normalized_last_name = last_name.strip()

    if not normalized_phone:
        raise ValueError("شماره موبایل الزامی است.")

    if not password or not password.strip():
        raise ValueError("رمز عبور الزامی است.")

    if not normalized_first_name:
        raise ValueError("نام الزامی است.")

    if not normalized_last_name:
        raise ValueError("نام خانوادگی الزامی است.")

    if is_phone_registered(db, normalized_phone):
        raise ValueError("این شماره موبایل قبلاً ثبت‌نام شده است.")

    user = User(
        phone=normalized_phone,
        first_name=normalized_first_name,
        last_name=normalized_last_name,
        hashed_password=get_password_hash(password),
        role=role,
        is_active=is_active,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(
    db: Session,
    *,
    phone: str,
    password: str,
) -> Optional[User]:
    """
    اعتبارسنجی شماره موبایل و رمز عبور.

    برای امنیت، در صورت نامعتبر بودن شماره یا رمز، هر دو حالت None برمی‌گردانند
    تا مشخص نشود شماره موبایل در سیستم وجود دارد یا خیر.

    Returns:
        User | None
    """
    user = get_user_by_phone(db, phone)

    if user is None:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def create_user_access_token(user: User) -> str:
    """
    ساخت JWT برای کاربر معتبر.

    payload شامل:
    - sub: شناسه کاربر
    - role: نقش کاربر
    - phone: شماره موبایل

    توجه:
    هیچ اطلاعات حساسی مانند رمز عبور یا hashed_password
    نباید داخل JWT قرار گیرد.
    """
    return create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value,
            "phone": user.phone,
        }
    )


def authenticate_and_create_token(
    db: Session,
    *,
    phone: str,
    password: str,
) -> tuple[Optional[User], Optional[str]]:
    """
    ورود کاربر و ساخت توکن.

    Returns:
        tuple[User | None, str | None]:
            - در ورود موفق: (user, access_token)
            - در ورود ناموفق: (None, None)
    """
    user = authenticate_user(
        db,
        phone=phone,
        password=password,
    )

    if user is None:
        return None, None

    access_token = create_user_access_token(user)

    return user, access_token
