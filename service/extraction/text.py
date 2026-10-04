"""Plain text and Markdown. Markdown is not rendered."""

from __future__ import annotations

import re

from service.extraction.errors import DocumentError
from service.extraction.limits import MAX_EXTRACTED_CHARS


def decode_text(data: bytes) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DocumentError(
            "document_malformed",
            "The text file is not valid UTF-8.",
        ) from exc

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x00", "")
    if len(text) > MAX_EXTRACTED_CHARS:
        raise DocumentError("document_too_large", "The document is too large for analysis.")

    return text.strip()


def markdown_to_plain(text: str) -> str:
    """Drop Markdown markers. Nothing is executed or fetched."""

    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_]{1,3}", "", text)
    return text.strip()
