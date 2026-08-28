import re

def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\x00", "")
    # Replace OCR/PDF tick symbol with proper tick
    text = text.replace("\uf0fc", "✓")
    text = re.sub(r"\s+", " ", text)

    return text.strip()
