# Path: app/services/payments/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class PaymentInitResult:
    authority: str
    payment_url: str


class BasePaymentGateway(ABC):
    @abstractmethod
    def create_payment(
        self,
        amount: int,
        order_id: str,
        callback_url: str,
        additional_data: Optional[str] = None,
        payer_id: Optional[str] = None,
    ) -> PaymentInitResult:
        raise NotImplementedError

    @abstractmethod
    def verify_payment(
        self,
        order_id: str,
        sale_order_id: str,
        sale_reference_id: str,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    def settle_payment(
        self,
        order_id: str,
        sale_order_id: str,
        sale_reference_id: str,
    ) -> bool:
        """
        تسویه نهایی تراکنش ملت (bpSettleRequest).
        کدهای قابل‌قبول: '0' (موفق) یا '45' (قبلاً ستل شده).
        """
        raise NotImplementedError
