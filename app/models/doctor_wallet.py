from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class DoctorWallet(Base):
    __tablename__ = "doctor_wallets"

    id = Column(Integer, primary_key=True, index=True)

    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    balance = Column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    currency = Column(
        String(10),
        nullable=False,
        default="IRR",
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    doctor = relationship(
        "Doctor",
        backref="wallet",
    )

    transactions = relationship(
        "DoctorWalletTransaction",
        back_populates="wallet",
        cascade="all, delete-orphan",
    )


class DoctorWalletTransaction(Base):
    __tablename__ = "doctor_wallet_transactions"

    id = Column(Integer, primary_key=True, index=True)

    wallet_id = Column(
        Integer,
        ForeignKey("doctor_wallets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    amount = Column(
        Numeric(12, 2),
        nullable=False,
    )

    transaction_type = Column(
        String(50),
        nullable=False,
    )

    reference_id = Column(
        String(255),
        nullable=True,
        index=True,
    )

    description = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    wallet = relationship(
        "DoctorWallet",
        back_populates="transactions",
    )
