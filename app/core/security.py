from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# استفاده از bcrypt_sha256 برای تضمین سازگاری کامل با نسخه‌های جدید bcrypt در سرور Render
pwd_context = CryptContext(
    schemes=["bcrypt_sha256"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    try:
        return pwd_context.verify(
            plain_password,
            hashed_password,
        )
    except (TypeError, ValueError):
        return False


def create_access_token(
    subject: str | int,
    role: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    token_expiration = expires_delta or timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    expire = datetime.now(timezone.utc) + token_expiration

    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
    }

    if role:
        payload["role"] = role

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        subject = payload.get("sub")
        if subject is None or not isinstance(subject, str) or not subject.strip():
            raise credentials_exception

        return payload

    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except JWTError as exc:
        raise credentials_exception from exc
