# Path: app/api/routes/doctors.py

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_user, get_db
from app.models.doctor import Doctor, Specialty
from app.models.user import User
from app.schemas.doctor import (
    DoctorCreate,
    DoctorCreateResponse,
    DoctorListItem,
    DoctorListResponse,
    DoctorProfileApiResponse,
    DoctorProfileResponse,
    DoctorResponse,
    DoctorUpdate,
)

router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"],
)

def get_doctor_profile_or_404(db: Session, user_id: int) -> Doctor:
    doctor = (
        db.query(Doctor)
        .options(joinedload(Doctor.user), joinedload(Doctor.specialty_relation))
        .filter(Doctor.user_id == user_id)
        .first()
    )
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="پروفایل پزشک یافت نشد.",
        )
    return doctor

def build_doctor_profile_response(doctor: Doctor, user: User) -> DoctorProfileResponse:
    return DoctorProfileResponse(
        id=user.id,
        name=user.name,
        phone=user.phone,
        email=getattr(user, "email", None),
        role=user.role,
        specialty_id=doctor.specialty_id,
        specialty_name=doctor.specialty_relation.name if doctor.specialty_relation else "نامشخص",
        medical_council_number=doctor.medical_council_number,
        sub_specialty=doctor.sub_specialty,
        work_shift=doctor.work_shift,
        province=doctor.province,
        city=doctor.city,
        address=doctor.address,
        bio=doctor.bio,
        experience_years=doctor.experience_years,
        consultation_fee=doctor.consultation_fee,
        waiting_time_estimate=doctor.waiting_time_estimate
    )

def build_doctor_list_item(doctor: Doctor) -> DoctorListItem:
    return DoctorListItem(
        id=doctor.id,
        user_id=doctor.user_id,
        name=doctor.user.name if doctor.user else "پزشک بدون نام",
        specialty_id=doctor.specialty_id,
        specialty_name=doctor.specialty_relation.name if doctor.specialty_relation else "نامشخص",
        work_shift=doctor.work_shift,
        city=doctor.city,
        address=doctor.address,
        bio=doctor.bio,
        experience_years=doctor.experience_years,
        consultation_fee=doctor.consultation_fee,
    )

@router.post("", response_model=DoctorCreateResponse, status_code=status.HTTP_201_CREATED)
def create_doctor_profile(
    payload: DoctorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ۱. اعتبارسنجی نقش کاربر
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="فقط کاربران با نقش 'پزشک' مجاز به ساخت پروفایل هستند.",
        )

    # ۲. بررسی عدم وجود پروفایل تکراری
    existing_doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if existing_doctor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="پروفایل پزشک پیش از این برای شما ساخته شده است.",
        )

    # ۳. بررسی معتبر بودن تخصص
    specialty = db.query(Specialty).get(payload.specialty_id)
    if not specialty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="تخصص انتخاب شده معتبر نیست.",
        )

    # ۴. ایجاد نمونه مدل با تمام فیلدهای لازم
    doctor = Doctor(
        user_id=current_user.id,
        **payload.model_dump()
    )

    try:
        db.add(doctor)
        db.commit()
        db.refresh(doctor)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="شماره نظام پزشکی تکراری است یا نقض یکپارچگی داده رخ داده است.",
        )
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطای داخلی دیتابیس هنگام ثبت پروفایل",
        )

    return {
        "success": True,
        "data": DoctorResponse.model_validate(doctor),
    }

@router.get("/me", response_model=DoctorProfileApiResponse)
def get_my_doctor_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doctor = get_doctor_profile_or_404(db=db, user_id=current_user.id)
    return {
        "success": True,
        "data": build_doctor_profile_response(doctor=doctor, user=current_user),
    }

@router.patch("/me", response_model=DoctorProfileApiResponse)
def update_my_doctor_profile(
    payload: DoctorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doctor = get_doctor_profile_or_404(db=db, user_id=current_user.id)
    update_data = payload.model_dump(exclude_unset=True)

    for field_name, field_value in update_data.items():
        setattr(doctor, field_name, field_value)

    try:
        db.commit()
        db.refresh(doctor)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطای دیتابیس هنگام بروزرسانی پروفایل",
        )

    return {
        "success": True,
        "data": build_doctor_profile_response(doctor=doctor, user=current_user),
    }

@router.get("/search", response_model=DoctorListResponse)
def search_doctors(
    q: str | None = Query(default=None, max_length=120),
    city: str | None = Query(default=None, max_length=120),
    specialty_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Doctor)
        .join(Doctor.user)
        .options(joinedload(Doctor.user), joinedload(Doctor.specialty_relation))
    )

    if q:
        search_value = f"%{q.strip()}%"
        query = query.filter(
            or_(
                User.name.ilike(search_value),
                Doctor.city.ilike(search_value),
                Doctor.bio.ilike(search_value),
            )
        )

    if city:
        query = query.filter(Doctor.city.ilike(f"%{city.strip()}%"))

    if specialty_id:
        query = query.filter(Doctor.specialty_id == specialty_id)

    doctors = query.order_by(Doctor.id.desc()).all()
    items = [build_doctor_list_item(doctor) for doctor in doctors]

    return {"success": True, "count": len(items), "items": items}

@router.get("", response_model=DoctorListResponse)
def list_doctors(db: Session = Depends(get_db)):
    doctors = (
        db.query(Doctor)
        .options(joinedload(Doctor.user), joinedload(Doctor.specialty_relation))
        .order_by(Doctor.id.desc())
        .all()
    )
    items = [build_doctor_list_item(doctor) for doctor in doctors]
    return {"success": True, "count": len(items), "items": items}

@router.get("/{doctor_id}", response_model=DoctorCreateResponse)
def get_doctor_by_id(doctor_id: int, db: Session = Depends(get_db)):
    doctor = (
        db.query(Doctor)
        .options(joinedload(Doctor.user), joinedload(Doctor.specialty_relation))
        .filter(Doctor.id == doctor_id)
        .first()
    )
    if not doctor:
        raise HTTPException(status_code=404, detail="پزشک یافت نشد.")

    return {"success": True, "data": DoctorResponse.model_validate(doctor)}
