import re


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def lower_no_punct(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9\s\-/+.]", " ", text or "")
    return normalize_whitespace(value).lower()


def safe_truncate(text: str, max_chars: int = 300) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3]}..."
