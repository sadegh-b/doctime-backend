# Path: backend/app/api/routes/doctors.py

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
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


def get_or_create_specialty(db: Session, specialty_name: str) -> Specialty:
    specialty_name = specialty_name.strip()
    specialty = db.query(Specialty).filter(Specialty.name == specialty_name).first()
    if not specialty:
        slug = specialty_name.lower().replace(" ", "-")
        specialty = Specialty(name=specialty_name, slug=slug)
        db.add(specialty)
        db.flush()
    return specialty


def get_doctor_profile_or_404(
    db: Session,
    user_id: int,
) -> Doctor:
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


def build_doctor_profile_response(
    doctor: Doctor,
    user: User,
) -> DoctorProfileResponse:
    # اصلاح شد: استخراج ایمن نام و شناسه تخصص
    specialty_name = doctor.specialty_relation.name if doctor.specialty_relation else "نامشخص"
    specialty_id = doctor.specialty_id
    return DoctorProfileResponse(
        id=user.id,
        name=user.name,
        phone=user.phone,
        email=getattr(user, "email", None),
        role=user.role,
        specialty_id=specialty_id,
        specialty_name=specialty_name,
        work_shift=doctor.work_shift,
        city=doctor.city,
        address=doctor.address,
        bio=doctor.bio,
        experience_years=doctor.experience_years,
        consultation_fee=doctor.consultation_fee,
    )


def build_doctor_list_item(
    doctor: Doctor,
) -> DoctorListItem:
    # اصلاح شد: استخراج ایمن نام و شناسه تخصص
    specialty_name = doctor.specialty_relation.name if doctor.specialty_relation else "نامشخص"
    specialty_id = doctor.specialty_id
    return DoctorListItem(
        id=doctor.id,
        user_id=doctor.user_id,
        name=doctor.user.name if doctor.user else None,
        specialty_id=specialty_id,
        specialty_name=specialty_name,
        work_shift=doctor.work_shift,
        city=doctor.city,
        address=doctor.address,
        bio=doctor.bio,
        experience_years=doctor.experience_years,
        consultation_fee=doctor.consultation_fee,
    )


@router.post(
    "",
    response_model=DoctorCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_doctor_profile(
    payload: DoctorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="فقط پزشکان مجاز به ساخت پروفایل هستند.",
        )

    existing_doctor = (
        db.query(Doctor)
        .filter(Doctor.user_id == current_user.id)
        .first()
    )

    if existing_doctor is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="پروفایل پزشک پیش از این ساخته شده است.",
        )

    doctor = Doctor(
        user_id=current_user.id,
        specialty_id=payload.specialty_id,
        work_shift=payload.work_shift,
        city=payload.city,
        address=payload.address,
        bio=payload.bio,
        experience_years=payload.experience_years,
        consultation_fee=payload.consultation_fee,
    )

    try:
        db.add(doctor)
        db.commit()
        db.refresh(doctor)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطای دیتابیس در هنگام ثبت پروفایل پزشک",
        ) from exc

    return {
        "success": True,
        "data": DoctorResponse.model_validate(doctor),
    }


@router.get(
    "/me",
    response_model=DoctorProfileApiResponse,
)
def get_my_doctor_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="تنها پزشک به این اطلاعات دسترسی دارد.",
        )

    doctor = get_doctor_profile_or_404(
        db=db,
        user_id=current_user.id,
    )

    return {
        "success": True,
        "data": build_doctor_profile_response(
            doctor=doctor,
            user=current_user,
        ),
    }


@router.patch(
    "/me",
    response_model=DoctorProfileApiResponse,
)
def update_my_doctor_profile(
    payload: DoctorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="تنها پزشک می‌تواند پروفایل خود را بروزرسانی کند.",
        )

    doctor = get_doctor_profile_or_404(
        db=db,
        user_id=current_user.id,
    )

    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data:
        current_user.name = update_data.pop("name")

    for field_name, field_value in update_data.items():
        setattr(doctor, field_name, field_value)

    try:
        db.add(current_user)
        db.add(doctor)
        db.commit()

        db.refresh(current_user)
        db.refresh(doctor)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطای دیتابیس هنگام بروزرسانی پروفایل",
        ) from exc

    return {
        "success": True,
        "data": build_doctor_profile_response(
            doctor=doctor,
            user=current_user,
        ),
    }


@router.get(
    "/search",
    response_model=DoctorListResponse,
)
def search_doctors(
    q: str | None = Query(default=None, max_length=120),
    city: str | None = Query(default=None, max_length=120),
    specialty: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Doctor)
        .join(Doctor.user)
        .join(Doctor.specialty_relation)
        .options(joinedload(Doctor.user), joinedload(Doctor.specialty_relation))
    )

    if q:
        search_value = f"%{q.strip()}%"

        query = query.filter(
            or_(
                User.name.ilike(search_value),
                Specialty.name.ilike(search_value),
                Doctor.city.ilike(search_value),
                Doctor.address.ilike(search_value),
                Doctor.bio.ilike(search_value),
            )
        )

    if city:
        query = query.filter(
            Doctor.city.ilike(f"%{city.strip()}%"),
        )

    if specialty:
        query = query.filter(
            Specialty.name.ilike(f"%{specialty.strip()}%"),
        )

    doctors = query.order_by(Doctor.id.desc()).all()

    items = [
        build_doctor_list_item(doctor)
        for doctor in doctors
    ]

    return {
        "success": True,
        "count": len(items),
        "items": items,
    }


@router.get(
    "",
    response_model=DoctorListResponse,
)
def list_doctors(
    db: Session = Depends(get_db),
):
    doctors = (
        db.query(Doctor)
        .options(joinedload(Doctor.user), joinedload(Doctor.specialty_relation))
        .order_by(Doctor.id.desc())
        .all()
    )

    items = [
        build_doctor_list_item(doctor)
        for doctor in doctors
    ]

    return {
        "success": True,
        "count": len(items),
        "items": items,
    }


@router.get(
    "/{doctor_id}",
    response_model=DoctorCreateResponse,
)
def get_doctor_by_id(
    doctor_id: int,
    db: Session = Depends(get_db),
):
    doctor = (
        db.query(Doctor)
        .options(joinedload(Doctor.user), joinedload(Doctor.specialty_relation))
        .filter(Doctor.id == doctor_id)
        .first()
    )

    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="پزشک پیدا نشد.",
        )

    return {
        "success": True,
        "data": DoctorResponse.model_validate(doctor),
    }
