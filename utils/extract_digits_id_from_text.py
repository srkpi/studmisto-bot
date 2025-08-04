import re

def extract_digits_id_from_text(text: str):
    match = re.search(r"#(R\d+)", text)

    return match.group(1) if match else None
