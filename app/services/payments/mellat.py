# Path: app/services/payments/mellat.py

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from app.core.config import settings
from app.services.payments.base import BasePaymentGateway, PaymentInitResult

try:
    from zeep import Client
except Exception:  # pragma: no cover
    Client = None


class MellatPaymentGateway(BasePaymentGateway):
    """
    سرویس درگاه پرداخت به پرداخت ملت با پشتیبانی از درخواست، تایید و تسویه تراکنش.
    """

    def __init__(self) -> None:
        if Client is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="کتابخانه zeep برای اتصال به وب‌سرویس درگاه ملت نصب نیست",
            )

        if not settings.MELLAT_TERMINAL_ID or not settings.MELLAT_USERNAME or not settings.MELLAT_PASSWORD:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="تنظیمات احراز هویت درگاه ملت (TerminalID/Username/Password) کامل نیست",
            )

        try:
            self.client = Client(settings.MELLAT_OPERATIONAL_WSDL)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="امکان اتصال به WSDL درگاه پرداخت ملت وجود ندارد",
            ) from exc

    def create_payment(
        self,
        amount: int,
        order_id: str,
        callback_url: str,
        additional_data: str | None = None,
        payer_id: str | None = None,
    ) -> PaymentInitResult:
        """
        ارسال درخواست اولیه به درگاه ملت (bpPayRequest) جهت دریافت RefId / Authority.
        """
        now = datetime.now()
        local_date = now.strftime("%Y%m%d")
        local_time = now.strftime("%H%M%S")

        try:
            result = self.client.service.bpPayRequest(
                terminalId=int(settings.MELLAT_TERMINAL_ID),
                userName=settings.MELLAT_USERNAME,
                userPassword=settings.MELLAT_PASSWORD,
                orderId=int(order_id),
                amount=int(amount),
                localDate=local_date,
                localTime=local_time,
                additionalData=additional_data or "",
                callBackUrl=callback_url,
                payerId=payer_id or "0",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"خطا در برقراری ارتباط با وب‌سرویس درگاه ملت: {str(exc)}",
            ) from exc

        if not result:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="پاسخ نامعتبر یا خالی از درگاه ملت دریافت شد",
            )

        if isinstance(result, str):
            parts = [p.strip() for p in result.split(",")]
            if len(parts) != 2:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"فرمت پاسخ دریافتی از درگاه ملت نامعتبر است: {result}",
                )

            response_code, reference = parts
            if response_code != "0":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"خطای پرداخت از سمت درگاه ملت. کد خطا: {response_code}",
                )

            return PaymentInitResult(
                authority=reference,
                payment_url=f"{settings.MELLAT_STARTPAY_URL}",
            )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="نوع داده خروجی از درگاه ملت پشتیبانی نمی‌شود",
        )

    def verify_payment(
        self,
        order_id: str,
        sale_order_id: str,
        sale_reference_id: str,
    ) -> bool:
        """
        تایید تراکنش پرداخت شده (bpVerifyRequest).
        کد 0 به معنای تایید موفق تراکنش است.
        """
        try:
            result = self.client.service.bpVerifyRequest(
                terminalId=int(settings.MELLAT_TERMINAL_ID),
                userName=settings.MELLAT_USERNAME,
                userPassword=settings.MELLAT_PASSWORD,
                orderId=int(order_id),
                saleOrderId=int(sale_order_id),
                saleReferenceId=int(sale_reference_id),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="خطا در فراخوانی سرویس تایید تراکنش درگاه ملت",
            ) from exc

        return str(result).strip() == "0"

    def settle_payment(
        self,
        order_id: str,
        sale_order_id: str,
        sale_reference_id: str,
    ) -> bool:
        """
        تسویه و واریز قطعی مبلغ به حساب (bpSettleRequest).
        کد 0: تسویه موفق
        کد 45: تراکنش قبلاً با موفقیت تسویه شده است (Idempotent)
        """
        try:
            result = self.client.service.bpSettleRequest(
                terminalId=int(settings.MELLAT_TERMINAL_ID),
                userName=settings.MELLAT_USERNAME,
                userPassword=settings.MELLAT_PASSWORD,
                orderId=int(order_id),
                saleOrderId=int(sale_order_id),
                saleReferenceId=int(sale_reference_id),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="خطا در فراخوانی سرویس تسویه تراکنش درگاه ملت",
            ) from exc

        res_str = str(result).strip()
        return res_str in ("0", "45")
