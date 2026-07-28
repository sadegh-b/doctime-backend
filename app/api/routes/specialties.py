# Path: app/api/routes/specialties.py

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.doctor import Specialty

# تنظیم لاگر برای دیدن خطاها در کنسول سرور
logger = logging.getLogger(__name__)


# طرح خروجی Pydantic متناسب با مدل
class SpecialtyOut(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


router = APIRouter(prefix="/specialties", tags=["Specialties"])


@router.get("/", response_model=List[SpecialtyOut])
def get_specialties(db: Session = Depends(get_db)):
    """
    برگشت لیست تمام تخصص‌های ثبت شده.
    در صورتی که جدول تخصص‌ها خالی باشد، مقادیر پیش‌فرض استاندارد را در دیتابیس درج می‌کند.
    """
    try:
        specialties = db.query(Specialty).all()

        if not specialties:
            logger.info("Specialties table is empty. Seeding default data...")

            # نگاشت نام فارسی به slug انگلیسی و توضیحات اولیه
            default_specialties = [
                {"name": "قلب و عروق", "slug": "cardiology", "description": "متخصص بیماری‌های قلب و عروق"},
                {"name": "پوست و مو", "slug": "dermatology", "description": "متخصص بیماری‌های پوست، مو و زیبایی"},
                {"name": "مغز و اعصاب", "slug": "neurology", "description": "متخصص مغز، اعصاب و ستون فقرات"},
                {"name": "داخلی", "slug": "internal-medicine", "description": "متخصص بیماری‌های داخلی"},
                {"name": "کودکان", "slug": "pediatrics", "description": "متخصص بیماری‌های کودکان و نوزادان"},
                {"name": "چشم‌پزشکی", "slug": "ophthalmology", "description": "متخصص چشم‌پزشکی و جراحی چشم"}
            ]

            # ساخت اشیاء مدل
            new_entries = []
            for spec_data in default_specialties:
                new_entries.append(
                    Specialty(
                        name=spec_data["name"],
                        slug=spec_data["slug"],
                        description=spec_data["description"]
                    )
                )

            db.add_all(new_entries)
            db.commit()
            logger.info("Default specialties successfully seeded.")

            # مجددا داده‌ها را واکشی می‌کنیم تا با شناسه‌های اختصاص یافته برگردند
            specialties = db.query(Specialty).all()

        return specialties

    except Exception as e:
        db.rollback()  # لغو تراکنش در صورت بروز خطا برای جلوگیری از خرابی داده‌ها
        logger.error(f"Error in get_specialties: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")
