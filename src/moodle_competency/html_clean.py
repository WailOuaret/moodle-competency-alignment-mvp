"""Utilities for converting Moodle HTML into normalized plain text."""

from __future__ import annotations

import html
import re
import unicodedata

from bs4 import BeautifulSoup


WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_whitespace(value: str | None) -> str:
    """Normalize Unicode and collapse repeated whitespace."""

    if value is None:
        return ""

    text = html.unescape(str(value))
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00a0", " ")

    return WHITESPACE_PATTERN.sub(" ", text).strip()


def html_to_text(value: str | None) -> str:
    """Convert HTML content into normalized plain text."""

    if value is None or not str(value).strip():
        return ""

    soup = BeautifulSoup(str(value), "lxml")

    for unwanted in soup(
        ["script", "style", "noscript", "template"]
    ):
        unwanted.decompose()

    return normalize_whitespace(
        soup.get_text(separator=" ")
    )


def combine_text(*parts: str | None) -> str:
    """Combine non-empty text parts without exact duplicates."""

    unique_parts: list[str] = []
    seen: set[str] = set()

    for part in parts:
        normalized = normalize_whitespace(part)

        if not normalized:
            continue

        comparison_key = normalized.casefold()

        if comparison_key in seen:
            continue

        seen.add(comparison_key)
        unique_parts.append(normalized)

    return "\n\n".join(unique_parts)
