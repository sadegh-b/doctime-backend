from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree as ET

from fastapi import HTTPException, status

from app.core.config import settings
from app.services.payments.base import BasePaymentGateway, PaymentInitResult

try:
    from zeep import Client
except Exception:  # pragma: no cover
    Client = None


class MellatPaymentGateway(BasePaymentGateway):
    def __init__(self) -> None:
        if Client is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="کتابخانه zeep نصب نیست",
            )

        if not settings.MELLAT_TERMINAL_ID or not settings.MELLAT_USERNAME or not settings.MELLAT_PASSWORD:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="تنظیمات درگاه ملت کامل نیست",
            )

        self.client = Client(settings.MELLAT_OPERATIONAL_WSDL)

    def create_payment(
        self,
        amount: int,
        order_id: str,
        callback_url: str,
        additional_data: str | None = None,
        payer_id: str | None = None,
    ) -> PaymentInitResult:
        try:
            result = self.client.service.bpPayRequest(
                terminalId=settings.MELLAT_TERMINAL_ID,
                userName=settings.MELLAT_USERNAME,
                userPassword=settings.MELLAT_PASSWORD,
                orderId=order_id,
                amount=amount,
                localDate=None,
                localTime=None,
                additionalData=additional_data or "",
                callBackUrl=callback_url,
                payerId=payer_id or "",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="خطا در ارتباط با درگاه ملت",
            ) from exc

        # Mellat returns: "0,AUTHCODE"
        if not result:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="پاسخ نامعتبر از درگاه ملت",
            )

        if isinstance(result, str):
            parts = [p.strip() for p in result.split(",")]
            if len(parts) != 2:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="فرمت پاسخ درگاه ملت نامعتبر است",
                )

            response_code, reference = parts
            if response_code != "0":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"خطا از درگاه ملت: {response_code}",
                )

            return PaymentInitResult(
                authority=reference,
                payment_url=f"{settings.MELLAT_STARTPAY_URL}/{reference}",
            )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="نوع پاسخ درگاه ملت نامعتبر است",
        )

    def verify_payment(
        self,
        order_id: str,
        sale_order_id: str,
        sale_reference_id: str,
    ) -> bool:
        try:
            result = self.client.service.bpVerifyRequest(
                terminalId=settings.MELLAT_TERMINAL_ID,
                userName=settings.MELLAT_USERNAME,
                userPassword=settings.MELLAT_PASSWORD,
                orderId=order_id,
                saleOrderId=sale_order_id,
                saleReferenceId=sale_reference_id,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="خطا در تایید تراکنش از درگاه ملت",
            ) from exc

        return str(result).strip() == "0"
