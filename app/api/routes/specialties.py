# Path: backend/app/api/routes/specialties.py

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.doctor import Specialty

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/specialties", tags=["Specialties"])


class SpecialtyOut(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


DEFAULT_SPECIALTIES = [
    {
        "name": "قلب و عروق",
        "slug": "cardiology",
        "description": "متخصص بیماری‌های قلب و عروق",
    },
    {
        "name": "پوست و مو",
        "slug": "dermatology",
        "description": "متخصص بیماری‌های پوست، مو و زیبایی",
    },
    {
        "name": "مغز و اعصاب",
        "slug": "neurology",
        "description": "متخصص مغز، اعصاب و ستون فقرات",
    },
    {
        "name": "داخلی",
        "slug": "internal-medicine",
        "description": "متخصص بیماری‌های داخلی",
    },
    {
        "name": "کودکان",
        "slug": "pediatrics",
        "description": "متخصص بیماری‌های کودکان و نوزادان",
    },
    {
        "name": "چشم‌پزشکی",
        "slug": "ophthalmology",
        "description": "متخصص چشم‌پزشکی و جراحی چشم",
    },
]


def seed_default_specialties(db: Session) -> None:
    """
    Creates default specialties only when the specialties table is empty.

    This helper is intentionally isolated so database transaction handling
    remains explicit and testable.
    """
    has_any_specialty = db.query(Specialty.id).first()

    if has_any_specialty is not None:
        return

    logger.info("Specialties table is empty. Seeding default specialties.")

    entries = [
        Specialty(
            name=item["name"],
            slug=item["slug"],
            description=item["description"],
        )
        for item in DEFAULT_SPECIALTIES
    ]

    db.add_all(entries)
    db.commit()

    logger.info("Default specialties seeded successfully.")


@router.get("/", response_model=List[SpecialtyOut])
def get_specialties(db: Session = Depends(get_db)) -> List[Specialty]:
    """
    Returns all specialties.

    If no specialty exists yet, the default specialty list is seeded once.
    """
    try:
        seed_default_specialties(db)

        return (
            db.query(Specialty)
            .order_by(Specialty.name.asc())
            .all()
        )

    except IntegrityError:
        db.rollback()

        # احتمال درخواست هم‌زمان هنگام seed شدن داده‌ها:
        # بعد از rollback دوباره داده‌های موجود را می‌خوانیم.
        logger.warning(
            "IntegrityError while seeding specialties. "
            "Reading existing specialties again."
        )

        specialties = (
            db.query(Specialty)
            .order_by(Specialty.name.asc())
            .all()
        )

        if specialties:
            return specialties

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در آماده‌سازی لیست تخصص‌ها رخ داد.",
        )

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error while retrieving specialties.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطای دیتابیس هنگام دریافت تخصص‌ها رخ داد.",
        )

    except Exception:
        db.rollback()
        logger.exception("Unexpected error while retrieving specialties.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطای غیرمنتظره‌ای رخ داد.",
        )
