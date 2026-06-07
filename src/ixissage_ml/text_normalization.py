"""Text normalization shared by baseline training/export.

URL-like spans are stripped so the baseline focuses on surrounding message
intent instead of treating URL shape itself as a proxy for risk.
"""

from __future__ import annotations

import re


URL_LIKE_PATTERN = re.compile(
    r"(?i)\b(?:https?://|www\.)[^\s]+|"
    r"\b[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\."
    r"(?:com|net|org|kr|co\.kr|go\.kr|or\.kr|ne\.kr|io|me|ly|live|site|xyz)\b[^\s]*"
)
WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_for_intent_model(text: str) -> str:
    """Remove URL-like spans before text classification.

    This is not a URL safety rule. It is uniform preprocessing that prevents
    the model from relying on URL syntax alone when classifying message intent.
    """
    without_urls = URL_LIKE_PATTERN.sub(" ", text)
    return WHITESPACE_PATTERN.sub(" ", without_urls).strip()


NORMALIZATION_METADATA = {
    "name": "intent_without_url_surface",
    "strip_url_like_spans": True,
    "description": (
        "URL-like spans are removed before baseline vectorization so URL syntax "
        "alone is not used as a smishing signal."
    ),
}
