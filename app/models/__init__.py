from app.database.base import Base

from app.models.user import User
from app.models.doctor import Doctor
from app.models.availability import Availability
from app.models.appointment import Appointment

# General wallet model (referenced by User.wallet and Transaction)
from app.models.wallet import Wallet, Transaction

# New domain-specific models
from app.models.doctor_wallet import DoctorWallet, DoctorWalletTransaction
from app.models.doctor_billing import (
    SubscriptionPlan,
    DoctorSubscription,
    PromotionPackage,
    DoctorPromotion,
)

__all__ = [
    "Base",
    "User",
    "Doctor",
    "Availability",
    "Appointment",
    "Wallet",
    "Transaction",
    "DoctorWallet",
    "DoctorWalletTransaction",
    "SubscriptionPlan",
    "DoctorSubscription",
    "PromotionPackage",
    "DoctorPromotion",
]
