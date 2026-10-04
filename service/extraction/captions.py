"""VTT and SRT cues. Times stay with the text so evidence can name them."""

from __future__ import annotations

import re

from service.extraction.errors import DocumentError
from service.extraction.limits import MAX_CAPTION_CUES, MAX_EXTRACTED_CHARS

_VTT_TIME = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2}\.\d{3})"
)
_SRT_TIME = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)
_TAG = re.compile(r"<[^>]+>")


def _clock(value: str) -> str:
    """Show a cue time as HH:MM:SS."""

    value = value.replace(",", ".")
    hours, minutes, seconds = value.split(":")
    return f"{int(hours):02d}:{int(minutes):02d}:{int(float(seconds)):02d}"


def parse_captions(text: str, kind: str) -> list[dict[str, str]]:
    pattern = _VTT_TIME if kind == "vtt" else _SRT_TIME
    lines = text.split("\n")
    cues: list[dict[str, str]] = []
    index = 0

    if kind == "vtt":
        if not lines or not lines[0].lstrip("\ufeff").startswith("WEBVTT"):
            raise DocumentError("document_malformed", "The transcript could not be parsed.")
        index = 1

    while index < len(lines):
        line = lines[index].strip()
        match = pattern.fullmatch(line)
        if match is None:
            index += 1
            continue

        index += 1
        parts: list[str] = []
        while index < len(lines) and lines[index].strip() != "":
            parts.append(_TAG.sub("", lines[index].strip()))
            index += 1

        quote = " ".join(part for part in parts if part).strip()
        if quote:
            cues.append({
                "kind": "cue",
                "start": _clock(match.group("start")),
                "end": _clock(match.group("end")),
                "text": quote,
            })
        if len(cues) > MAX_CAPTION_CUES:
            raise DocumentError("document_too_large", "The transcript is too large for analysis.")

    if not cues:
        raise DocumentError("document_malformed", "The transcript could not be parsed.")

    return cues


def cues_to_text(cues: list[dict[str, str]]) -> str:
    text = "\n\n".join(cue["text"] for cue in cues)
    if len(text) > MAX_EXTRACTED_CHARS:
        raise DocumentError("document_too_large", "The transcript is too large for analysis.")
    return text
