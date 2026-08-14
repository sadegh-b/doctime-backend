from fastapi import HTTPException, status

from app.services.payments.base import BasePaymentGateway, PaymentInitResult


class ParsianPaymentGateway(BasePaymentGateway):
    def create_payment(
        self,
        amount: int,
        order_id: str,
        callback_url: str,
        additional_data: str | None = None,
        payer_id: str | None = None,
    ) -> PaymentInitResult:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="درگاه پارسیان هنوز پیاده‌سازی نشده است",
        )

    def verify_payment(
        self,
        order_id: str,
        sale_order_id: str,
        sale_reference_id: str,
    ) -> bool:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="درگاه پارسیان هنوز پیاده‌سازی نشده است",
        )
