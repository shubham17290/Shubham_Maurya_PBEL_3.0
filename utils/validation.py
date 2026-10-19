"""Shared input validation helpers."""

from typing import Optional, Tuple


def validate_news_text(text: str, min_length: int = 50, max_length: int = 50000) -> Optional[str]:
    """Validate a news article string.

    Returns an error message if invalid, otherwise ``None``.
    """
    if not text or not isinstance(text, str):
        return "Please enter some news text to analyze."

    text = text.strip()

    if len(text) == 0:
        return "Please enter some news text to analyze."

    if len(text) < min_length:
        return f"Please enter a longer text (at least {min_length} characters) for accurate prediction."

    if len(text) > max_length:
        return f"Text is too long. Please enter less than {max_length:,} characters."

    if not any(char.isalnum() for char in text):
        return "Please enter valid text with alphanumeric characters."

    return None