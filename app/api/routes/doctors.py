# Path: backend/app/api/routes/doctors.py

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_user, get_db
from app.models.doctor import Doctor, Specialty
from app.models.user import User

router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"],
)


# ==========================================
# Pydantic Schemas (خروجی‌های استاندارد شده)
# ==========================================

class SpecialtyResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class UserBriefResponse(BaseModel):
    id: int
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: str
    phone_number: Optional[str] = None  # برای سازگاری با فرانت

    model_config = {"from_attributes": True}


class DoctorResponse(BaseModel):
    id: int
    user_id: int
    medical_council_number: Optional[str] = None
    specialty_id: Optional[int] = None
    sub_specialty: Optional[str] = None
    work_shift: str
    province: Optional[str] = None
    city: str
    address: Optional[str] = None
    bio: Optional[str] = None
    experience_years: int
    consultation_fee: int

    user: UserBriefResponse
    # نکته حیاتی: فرانت‌اندمان دنبال نام specialty می‌گردد
    specialty: Optional[SpecialtyResponse] = Field(None, alias="specialty_relation")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True  # اجازه می‌دهد هر دو نام کار کنند
    }


# سایر مدل‌های درخواست (Request)
class DoctorRegisterRequest(BaseModel):
    medical_council_number: str
    specialty_id: int
    province: str
    city: str
    work_shift: str = "morning"
    experience_years: int = 0
    consultation_fee: int = 0


class DoctorUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    specialty_id: Optional[int] = None
    city: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None


# ==========================================
# Endpoints (اصلاح شده برای بارگذاری تخصص)
# ==========================================

@router.get("/", response_model=List[DoctorResponse])
def get_doctors_list(
        specialty_slug: Optional[str] = None,
        city: Optional[str] = None,
        search: Optional[str] = None,
        db: Session = Depends(get_db),
) -> Any:
    """
    لیست پزشکان - با اصلاح بارگذاری تخصص برای نمایش در لیست
    """
    # استفاده از joinedload برای تخصص و اطلاعات کاربر
    query = db.query(Doctor).options(
        joinedload(Doctor.user),
        joinedload(Doctor.specialty_relation)
    )

    if specialty_slug:
        query = query.join(Doctor.specialty_relation).filter(Specialty.slug == specialty_slug)
    if city:
        query = query.filter(Doctor.city.ilike(f"%{city}%"))
    if search:
        query = query.join(User).filter(
            (User.first_name.ilike(f"%{search}%")) |
            (User.last_name.ilike(f"%{search}%")) |
            (Doctor.bio.ilike(f"%{search}%"))
        )

    return query.all()


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor_profile(doctor_id: int, db: Session = Depends(get_db)) -> Any:
    doctor = db.query(Doctor).options(
        joinedload(Doctor.user),
        joinedload(Doctor.specialty_relation)
    ).filter(Doctor.id == doctor_id).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="پزشک یافت نشد.")
    return doctor


@router.put("/me", response_model=DoctorResponse)
def update_my_doctor_profile(
        payload: DoctorUpdateRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
) -> Any:
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="پروفایل یافت نشد.")

    data = payload.model_dump(exclude_unset=True)

    # آپدیت فیلدهای کاربر
    user_fields = ["first_name", "last_name", "phone"]
    for field in user_fields:
        if field in data:
            setattr(current_user, field, data.pop(field))

    current_user.name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip()

    # آپدیت فیلدهای پزشک
    for key, value in data.items():
        setattr(doctor, key, value)

    db.commit()
    db.refresh(doctor)
    return doctor
