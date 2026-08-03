# Path: backend/app/api/routes/doctors.py

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_user, get_db
from app.models.doctor import Doctor, Specialty
from app.models.user import User

router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"],
)


# ==========================================
# Pydantic Schemas (اعتبارسنجی داده‌های ورودی و خروجی)
# ==========================================

class DoctorRegisterRequest(BaseModel):
    medical_council_number: str = Field(..., min_length=3, max_length=20)
    specialty_id: int
    sub_specialty: Optional[str] = None
    work_shift: str = Field("morning", pattern="^(morning|evening|night|all_day)$")
    province: str = Field(..., min_length=2, max_length=120)
    city: str = Field(..., min_length=2, max_length=120)
    address: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    bio: Optional[str] = Field(None, max_length=1000)
    experience_years: int = Field(0, ge=0)
    consultation_fee: int = Field(0, ge=0)
    waiting_time_estimate: Optional[int] = Field(None, ge=0)


class DoctorUpdateRequest(BaseModel):
    medical_council_number: Optional[str] = Field(None, min_length=3, max_length=20)
    specialty_id: Optional[int] = None
    sub_specialty: Optional[str] = None
    work_shift: Optional[str] = Field(None, pattern="^(morning|evening|night|all_day)$")
    province: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    bio: Optional[str] = None
    experience_years: Optional[int] = Field(None, ge=0)
    consultation_fee: Optional[int] = Field(None, ge=0)
    waiting_time_estimate: Optional[int] = Field(None, ge=0)


class SpecialtyResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class UserBriefResponse(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: str

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
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    bio: Optional[str] = None
    experience_years: int
    consultation_fee: int
    waiting_time_estimate: Optional[int] = None

    # روابط
    user: UserBriefResponse
    specialty_relation: Optional[SpecialtyResponse] = None

    model_config = {"from_attributes": True}


# ==========================================
# Endpoints
# ==========================================

@router.post("/register", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
def register_doctor_profile(
    payload: DoctorRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    ثبت مشخصات پزشک برای کاربری که در سیستم وارد شده است.
    """
    existing_doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if existing_doctor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="شما قبلاً پروفایل پزشک ایجاد کرده‌اید.",
        )

    dup_number = db.query(Doctor).filter(
        Doctor.medical_council_number == payload.medical_council_number
    ).first()
    if dup_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="شماره نظام پزشکی وارد شده قبلاً ثبت شده است.",
        )

    specialty = db.query(Specialty).filter(Specialty.id == payload.specialty_id).first()
    if not specialty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="تخصص مورد نظر یافت نشد.",
        )

    new_doctor = Doctor(
        user_id=current_user.id,
        medical_council_number=payload.medical_council_number,
        specialty_id=payload.specialty_id,
        sub_specialty=payload.sub_specialty,
        work_shift=payload.work_shift,
        province=payload.province,
        city=payload.city,
        address=payload.address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        bio=payload.bio,
        experience_years=payload.experience_years,
        consultation_fee=payload.consultation_fee,
        waiting_time_estimate=payload.waiting_time_estimate,
    )

    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)
    return new_doctor


@router.get("/", response_model=List[DoctorResponse])
def get_doctors_list(
    specialty_slug: Optional[str] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """
    دریافت لیست تمام پزشکان با قابلیت فیلتر بر اساس تخصص، شهر و کلمه کلیدی.
    """
    query = db.query(Doctor).options(
        joinedload(Doctor.user),
        joinedload(Doctor.specialty_relation),
    )

    if specialty_slug:
        query = query.join(Doctor.specialty_relation).filter(Specialty.slug == specialty_slug)

    if city:
        query = query.filter(Doctor.city.ilike(f"%{city}%"))

    if search:
        query = query.join(Doctor.user).filter(
            (User.first_name.ilike(f"%{search}%"))
            | (User.last_name.ilike(f"%{search}%"))
            | (Doctor.bio.ilike(f"%{search}%"))
        )

    return query.all()


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor_profile(doctor_id: int, db: Session = Depends(get_db)) -> Any:
    """
    نمایش اطلاعات کامل یک پزشک با شناسه یکتا.
    """
    doctor = (
        db.query(Doctor)
        .options(
            joinedload(Doctor.user),
            joinedload(Doctor.specialty_relation),
        )
        .filter(Doctor.id == doctor_id)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="پزشک مورد نظر یافت نشد.",
        )
    return doctor


@router.put("/me", response_model=DoctorResponse)
def update_my_doctor_profile(
    payload: DoctorUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    ویرایش اطلاعات پروفایل پزشک لاگین شده.
    """
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="پروفایل پزشکی برای شما پیدا نشد.",
        )

    if (
        payload.medical_council_number
        and payload.medical_council_number != doctor.medical_council_number
    ):
        dup = (
            db.query(Doctor)
            .filter(
                Doctor.medical_council_number == payload.medical_council_number,
                Doctor.id != doctor.id,
            )
            .first()
        )
        if dup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="شماره نظام پزشکی وارد شده متعلق به شخص دیگری است.",
            )

    update_data = payload.model_dump(exclude_unset=True)

    if "specialty_id" in update_data and update_data["specialty_id"] is not None:
        specialty = db.query(Specialty).filter(Specialty.id == update_data["specialty_id"]).first()
        if not specialty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="تخصص مورد نظر یافت نشد.",
            )

    for key, value in update_data.items():
        setattr(doctor, key, value)

    db.commit()
    db.refresh(doctor)
    return doctor
