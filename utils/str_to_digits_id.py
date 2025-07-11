from hashlib import sha256


def srt_to_digits_id(string: str) -> str:
    hash_object = sha256(string.encode())
    hash_hex = hash_object.hexdigest()
    hash_int = int(hash_hex, 16)
    six_digit_id = hash_int % 1000000

    return f"R{six_digit_id:06d}"
