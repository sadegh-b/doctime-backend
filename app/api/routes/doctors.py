from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_user, get_db
from app.models.doctor import Doctor
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


def get_doctor_profile_or_404(
    db: Session,
    user_id: int,
) -> Doctor:
    doctor = (
        db.query(Doctor)
        .options(joinedload(Doctor.user))
        .filter(Doctor.user_id == user_id)
        .first()
    )

    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found",
        )

    return doctor


def build_doctor_profile_response(
    doctor: Doctor,
    user: User,
) -> DoctorProfileResponse:
    return DoctorProfileResponse(
        id=user.id,
        name=user.name,
        phone=user.phone,
        email=getattr(user, "email", None),
        role=user.role,
        specialty=doctor.specialty,
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
    return DoctorListItem(
        id=doctor.id,
        user_id=doctor.user_id,
        name=doctor.user.name if doctor.user else None,
        specialty=doctor.specialty,
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
            detail="Only doctors can create a doctor profile",
        )

    existing_doctor = (
        db.query(Doctor)
        .filter(Doctor.user_id == current_user.id)
        .first()
    )

    if existing_doctor is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor profile already exists",
        )

    doctor = Doctor(
        user_id=current_user.id,
        specialty=payload.specialty,
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
            detail="Database error while creating doctor profile",
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
            detail="Only doctors can access a doctor profile",
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
            detail="Only doctors can update a doctor profile",
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
            detail="Database error while updating doctor profile",
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
        .options(joinedload(Doctor.user))
    )

    if q:
        search_value = f"%{q.strip()}%"

        query = query.filter(
            or_(
                User.name.ilike(search_value),
                Doctor.specialty.ilike(search_value),
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
            Doctor.specialty.ilike(f"%{specialty.strip()}%"),
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
        .options(joinedload(Doctor.user))
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
        .options(joinedload(Doctor.user))
        .filter(Doctor.id == doctor_id)
        .first()
    )

    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    return {
        "success": True,
        "data": DoctorResponse.model_validate(doctor),
    }
