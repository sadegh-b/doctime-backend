# C:\PythonProject\PythonProject\doctime-backend-clean\test_id.py
import re


def is_valid_iranian_national_id(value: str) -> bool:
    digits = [int(c) for c in value]
    weighted_sum = sum(digits[i] * (10 - i) for i in range(9))
    remainder = weighted_sum % 11
    control_digit = digits[9]

    if remainder < 2:
        return control_digit == remainder
    else:
        return control_digit == (11 - remainder)


# این کد باید True برگرداند:
print(f"Result 0084121777: {is_valid_iranian_national_id('0084121777')}")
