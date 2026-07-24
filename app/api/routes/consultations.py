# Path: backend/app/api/routes/consultations.py

import logging
import random
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

# وارد کردن مدل و تنظیمات دیتابیس
from ...models.consultation import ConsultationRequest, ConsultationType
from ...database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/consultations",
    tags=["Consultations"]
)


# وابستگی برای دریافت سشن دیتابیس
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# اسکیمای ورودی مطابق با فرانت‌اِند
class ConsultationSubmitSchema(BaseModel):
    phone_number: str = Field(..., pattern=r"^09\d{9}$")
    consultation_type: ConsultationType  # استفاده از Enum برای سخت‌گیری بیشتر
    summary_data: str = Field(..., min_length=10)


# اسکیمای خروجی جهت پیگیری وضعیت درخواست توسط بیمار
class ConsultationStatusResponse(BaseModel):
    phone_number: str
    consultation_type: ConsultationType
    status: str
    tracking_code: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_consultation(
        payload: ConsultationSubmitSchema,
        db: Session = Depends(get_db)
):
    logger.info(f"Storing consultation for: {payload.phone_number}")

    # تولید کد پیگیری منحصر به فرد با محدود کردن تلاش برای جلوگیری از حلقه بی‌نهایت در دیتابیس شلوغ
    gen_code = None
    max_attempts = 10
    for attempt in range(max_attempts):
        potential_code = random.randint(100000, 999999)
        exists = db.query(ConsultationRequest.id).filter(ConsultationRequest.tracking_code == potential_code).first()
        if not exists:
            gen_code = potential_code
            break

    if gen_code is None:
        logger.error("Failed to generate a unique tracking code after several attempts.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در تولید کد پیگیری یکتا. لطفا مجددا تلاش کنید."
        )

    try:
        # ایجاد آبجکت دیتابیس
        new_request = ConsultationRequest(
            phone_number=payload.phone_number,
            consultation_type=payload.consultation_type,
            summary_data=payload.summary_data,
            tracking_code=gen_code,
            status="pending"
        )

        # ذخیره در دیتابیس
        db.add(new_request)
        db.commit()
        db.refresh(new_request)

        logger.info(f"Consultation saved. ID: {new_request.id} | Tracking: {gen_code}")

        return {
            "status": "success",
            "tracking_code": new_request.tracking_code,
            "message": "اطلاعات با موفقیت در سیستم ثبت شد."
        }

    except Exception as e:
        db.rollback()
        logger.error(f"DB Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در ذخیره‌سازی داده‌ها"
        )


# مسیر جدید (Endpoint) برای پیگیری وضعیت شرح حال ثبت شده توسط کاربر با استفاده از کد رهگیری
@router.get("/track/{tracking_code}", response_model=ConsultationStatusResponse)
async def track_consultation(
        tracking_code: int,
        db: Session = Depends(get_db)
):
    logger.info(f"Tracking request received for code: {tracking_code}")

    consultation = db.query(ConsultationRequest).filter(
        ConsultationRequest.tracking_code == tracking_code
    ).first()

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="درخواستی با این کد پیگیری پیدا نشد."
        )

    return consultation
