"""Errors a teacher can be told about, without a parser traceback."""

from __future__ import annotations


class DocumentError(Exception):
    """A document that cannot be turned into alignment text."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
