from fastapi import APIRouter, Query

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get("")
def get_reviews(doctor_id: int = Query(..., gt=0)):
    """
    گرفتن لیست نظرات یک پزشک
    فعلاً داده نمونه برمی‌گرداند تا فرانت‌اند از 404 خارج شود.
    بعداً باید به دیتابیس وصلش کنی.
    """
    sample_reviews = [
        {
            "id": 1,
            "doctor_id": doctor_id,
            "patient_name": "Ali",
            "comment": "Doctor was very professional.",
            "rating": 5,
            "created_at": "2026-07-12T10:00:00",
        },
        {
            "id": 2,
            "doctor_id": doctor_id,
            "patient_name": "Sara",
            "comment": "Good experience overall.",
            "rating": 4,
            "created_at": "2026-07-11T15:30:00",
        },
    ]

    return sample_reviews


@router.post("")
def create_review(payload: dict):
    """
    ساخت نظر جدید
    فعلاً mock است.
    بعداً باید validation و ذخیره در دیتابیس اضافه شود.
    """
    return {
        "id": 999,
        "doctor_id": payload.get("doctor_id", 0),
        "patient_name": payload.get("patient_name", "").strip(),
        "comment": payload.get("comment", "").strip(),
        "rating": payload.get("rating", 5),
        "created_at": "2026-07-12T12:00:00",
    }
