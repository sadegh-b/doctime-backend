from app.services.payments.base import BasePaymentGateway, PaymentInitResult
from app.services.payments.mellat import MellatPaymentGateway
from app.services.payments.parsian import ParsianPaymentGateway


def get_payment_gateway() -> BasePaymentGateway:
    if settings.PAYMENT_GATEWAY.lower() == "parsian":
        return ParsianPaymentGateway()
    return MellatPaymentGateway()
