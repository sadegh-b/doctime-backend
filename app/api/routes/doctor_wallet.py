# Path: backend/app/api/routes/doctor_wallet.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.dependencies import get_current_doctor  # استفاده از وابستگی امن جدید
from app.models.doctor import Doctor

from app.schemas.doctor_wallet import (
    DoctorWalletRead,
    DoctorWalletTransactionRead,
    WalletTopUpRequest,
)
from app.services.doctor_wallet_service import DoctorWalletService

router = APIRouter(prefix="/doctor-wallet", tags=["Doctor Wallet"])

@router.get("/balance", response_model=DoctorWalletRead)
def get_wallet(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    # استفاده از current_doctor.id که از توکن استخراج شده است
    wallet = DoctorWalletService.get_or_create_wallet(db, current_doctor.id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet

@router.get("/transactions", response_model=list[DoctorWalletTransactionRead])
def get_transactions(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    return DoctorWalletService.list_transactions(db, current_doctor.id)

@router.post("/topup")
def topup_wallet(
    payload: WalletTopUpRequest,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    wallet, tx = DoctorWalletService.top_up(
        db=db,
        doctor_id=current_doctor.id,
        amount=payload.amount,
        reference_id=payload.reference_id,
        description=payload.description,
    )
    return {
        "wallet": wallet,
        "transaction": tx,
        "message": "Wallet topped up successfully",
    }
