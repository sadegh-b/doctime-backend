from abc import ABC, abstractmethod
from dataclasses import dataclass


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
        additional_data: str | None = None,
        payer_id: str | None = None,
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
