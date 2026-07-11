# app/api/routes/doctors.py
from fastapi import APIRouter, Depends, HTTPException, status
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
    DoctorResponse,
)

router = APIRouter(prefix="/doctors", tags=["Doctors"])


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
            detail="Only doctors can create profile",
        )

    existing = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor profile already exists",
        )

    doctor = Doctor(
        user_id=current_user.id,
        specialty=payload.specialty,
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
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while creating doctor profile",
        )

    return {
        "success": True,
        "data": DoctorResponse.model_validate(doctor),
    }


@router.get("", response_model=DoctorListResponse)
def list_doctors(db: Session = Depends(get_db)):
    doctors = (
        db.query(Doctor)
        .options(joinedload(Doctor.user))
        .order_by(Doctor.id.desc())
        .all()
    )

    items = [
        DoctorListItem(
            id=doctor.id,
            user_id=doctor.user_id,
            name=doctor.user.name if doctor.user else None,
            specialty=doctor.specialty,
            city=doctor.city,
            address=doctor.address,
            bio=doctor.bio,
            experience_years=doctor.experience_years,
            consultation_fee=doctor.consultation_fee,
        )
        for doctor in doctors
    ]

    return {
        "success": True,
        "count": len(items),
        "items": items,
    }
