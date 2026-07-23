# app/api/dependencies.py

from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.database.base import SessionLocal
from app.core.security import SECRET_KEY, ALGORITHM  # ایمپورت کردن ثابت‌های امنیتی
from app.models.user import User

# آدرس مسیر دریافت توکن برای Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def get_db() -> Generator:
    """وابستگی برای دریافت سشن دیتابیس"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """وابستگی برای استخراج کاربر جاری از روی توکن JWT معتبر"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # رمزگشایی توکن و استخراج فیلد sub (شماره تلفن یا ایمیل یا آی‌دی)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    # پیدا کردن کاربر در دیتابیس
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user
