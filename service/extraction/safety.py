"""Checks applied before a parser is allowed to read a file."""

from __future__ import annotations

import io
import zipfile

from service.extraction.errors import DocumentError
from service.extraction.limits import MAX_ZIP_FILES, MAX_ZIP_UNCOMPRESSED_BYTES


def reject_oversized(data: bytes, limit: int) -> None:
    if len(data) > limit:
        raise DocumentError(
            "document_too_large",
            "The document is too large for analysis.",
        )


def inspect_ooxml(data: bytes) -> None:
    """Refuse a ZIP that is not a bounded Office Open XML package.

    Macros and embedded objects are not executed: the caller only reads XML
    text through a library. This check stops a declared bomb or a path that
    leaves the package before that library opens it.
    """

    if not data.startswith(b"PK"):
        raise DocumentError("document_malformed", "The document could not be read.")

    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise DocumentError("document_malformed", "The document could not be read.") from exc

    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ZIP_FILES:
            raise DocumentError("document_too_large", "The document is too large for analysis.")

        total = 0
        for info in infos:
            name = info.filename.replace("\\", "/")
            parts = [part for part in name.split("/") if part not in ("", ".")]
            if name.startswith("/") or ".." in parts or any(part.startswith("/") for part in parts):
                raise DocumentError("document_malformed", "The document could not be read.")
            total += info.file_size
            if total > MAX_ZIP_UNCOMPRESSED_BYTES:
                raise DocumentError("document_too_large", "The document is too large for analysis.")

        names = {info.filename for info in infos}
        if "[Content_Types].xml" not in names:
            raise DocumentError("document_malformed", "The document could not be read.")
