import re


def is_valid_ukraine_phone(phone: str) -> bool:
    pattern = r"^\+380\d{9}$"
    return bool(re.match(pattern, phone))
