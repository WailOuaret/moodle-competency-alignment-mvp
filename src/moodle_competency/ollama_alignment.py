"""Run constrained Moodle competency-alignment tasks with local Ollama.

This is a separate optional experiment. It must never write Gemini
checkpoints or overwrite frozen core metric files.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

import requests

from moodle_competency.gemini_alignment import (
    build_request_prompt,
    build_response_schema,
    exponential_backoff_seconds,
)


WINDOWS_CURL = Path("/mnt/c/Windows/System32/curl.exe")
JSON_FENCE_RE = re.compile(
    r"^```(?:json)?\s*(.*?)\s*```$",
    re.IGNORECASE | re.DOTALL,
)


class OllamaAlignmentError(RuntimeError):
    """Raised when a local Ollama alignment request cannot be completed."""


@dataclass(frozen=True, slots=True)
class OllamaUsage:
    """Token-usage metadata returned by Ollama."""

    prompt_tokens: int | None
    candidate_tokens: int | None
    total_tokens: int | None

    def to_dict(self) -> dict[str, int | None]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "candidate_tokens": self.candidate_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass(frozen=True, slots=True)
class _HttpResult:
    status_code: int
    text: str
    payload: Any

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> Any:
        return self.payload


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from model text, including markdown fences."""

    cleaned = str(text or "").strip()
    fenced = JSON_FENCE_RE.match(cleaned)

    if fenced:
        cleaned = fenced.group(1).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start < 0 or end <= start:
            raise OllamaAlignmentError(
                "Ollama output is not a JSON object. "
                f"Preview: {cleaned[:1000]!r}"
            )

        parsed = json.loads(cleaned[start : end + 1])

    if not isinstance(parsed, dict):
        raise OllamaAlignmentError(
            "Ollama output is not a JSON object."
        )

    return parsed


def parse_usage(response_data: Mapping[str, Any]) -> OllamaUsage:
    def optional_int(value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    prompt = optional_int(response_data.get("prompt_eval_count"))
    candidate = optional_int(response_data.get("eval_count"))
    total = None

    if prompt is not None or candidate is not None:
        total = (prompt or 0) + (candidate or 0)

    return OllamaUsage(
        prompt_tokens=prompt,
        candidate_tokens=candidate,
        total_tokens=total,
    )


def default_ollama_host() -> str:
    return os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").strip().rstrip(
        "/"
    ) or "http://127.0.0.1:11434"


def default_ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "mistral:latest").strip() or (
        "mistral:latest"
    )


def _windows_temp_dir() -> Path | None:
    preferred = Path("/mnt/c/Users/wailo/AppData/Local/Temp")

    try:
        if preferred.is_dir():
            return preferred
    except OSError:
        pass

    users = Path("/mnt/c/Users")

    if not users.exists():
        return None

    skip = {"public", "default", "default user", "all users"}

    try:
        children = list(users.iterdir())
    except OSError:
        return None

    for child in sorted(children):
        if child.name.lower() in skip:
            continue

        temp = child / "AppData" / "Local" / "Temp"

        try:
            if temp.is_dir():
                return temp
        except OSError:
            continue

    return None


def _windows_path_for(path: Path) -> str:
    parts = path.resolve().parts

    if len(parts) >= 4 and parts[1] == "mnt" and len(parts[2]) == 1:
        drive = parts[2].upper()
        rest = "\\".join(parts[3:])
        return f"{drive}:\\{rest}"

    return str(path)


class OllamaAlignmentClient:
    """HTTP client for constrained Ollama alignment requests."""

    def __init__(
        self,
        *,
        host: str | None = None,
        model: str | None = None,
        timeout: float = 180.0,
        maximum_attempts: int = 6,
        session: requests.Session | None = None,
        allow_windows_curl_fallback: bool = True,
    ) -> None:
        if maximum_attempts <= 0:
            raise ValueError("maximum_attempts must be positive.")

        self.host = (host or default_ollama_host()).rstrip("/")
        self.model = (model or default_ollama_model()).strip()
        self.timeout = timeout
        self.maximum_attempts = maximum_attempts
        self.session = session or requests.Session()
        self._owns_session = session is None
        self.allow_windows_curl_fallback = allow_windows_curl_fallback
        self.last_http_retries = 0
        self.last_transport = "requests"

        parsed = urlparse(self.host)

        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(
                f"OLLAMA_HOST is invalid: {self.host}"
            )

        if not self.model:
            raise ValueError("OLLAMA_MODEL cannot be empty.")

    @property
    def chat_endpoint(self) -> str:
        return f"{self.host}/api/chat"

    @property
    def tags_endpoint(self) -> str:
        return f"{self.host}/api/tags"

    def close(self) -> None:
        if self._owns_session:
            self.session.close()

    def __enter__(self) -> "OllamaAlignmentClient":
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()

    def list_model_names(self) -> list[str]:
        result = self._request("GET", self.tags_endpoint)

        if not result.ok:
            raise OllamaAlignmentError(
                f"Ollama /api/tags returned HTTP {result.status_code}: "
                f"{result.text[:1000]}"
            )

        models = result.json().get("models") or []
        names: list[str] = []

        for item in models:
            if not isinstance(item, Mapping):
                continue

            for key in ("name", "model"):
                value = str(item.get(key, "")).strip()

                if value:
                    names.append(value)
                    break

        return names

    def require_model(self) -> None:
        names = self.list_model_names()
        allowed = set(names)
        allowed.update(name.split(":", 1)[0] for name in names)

        if self.model not in allowed and self.model not in names:
            raise OllamaAlignmentError(
                f"Ollama model {self.model!r} is not installed. "
                f"Available: {', '.join(names) or '(none)'}"
            )

    def align(
        self,
        task: Mapping[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], OllamaUsage]:
        """Run one constrained task against local Ollama."""

        fragment_id = str(task.get("fragment_id", "")).strip()
        prompt = build_request_prompt(task)
        schema = build_response_schema(task)
        request_body = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "stream": False,
            "format": schema,
            "options": {
                "temperature": 0,
                "num_predict": 2048,
            },
        }

        last_error = ""
        self.last_http_retries = 0

        for attempt in range(1, self.maximum_attempts + 1):
            try:
                result = self._request(
                    "POST",
                    self.chat_endpoint,
                    payload=request_body,
                )
            except OllamaAlignmentError as error:
                last_error = str(error)

                if attempt < self.maximum_attempts:
                    self.last_http_retries += 1
                    time.sleep(exponential_backoff_seconds(attempt))
                    continue

                raise

            if result.status_code == 400 and request_body.get("format") != "json":
                request_body = dict(request_body)
                request_body["format"] = "json"
                last_error = result.text[:1000]
                self.last_http_retries += 1
                continue

            if not result.ok:
                last_error = (
                    f"HTTP {result.status_code}: {result.text[:1000]}"
                )

                if (
                    result.status_code in {429, 500, 502, 503, 504}
                    and attempt < self.maximum_attempts
                ):
                    self.last_http_retries += 1
                    time.sleep(exponential_backoff_seconds(attempt))
                    continue

                raise OllamaAlignmentError(
                    f"Ollama request failed for {fragment_id}: {last_error}"
                )

            response_data = result.json()

            if not isinstance(response_data, dict):
                raise OllamaAlignmentError(
                    "Ollama returned a non-object JSON payload."
                )

            message = response_data.get("message") or {}
            content = ""

            if isinstance(message, Mapping):
                content = str(message.get("content") or "")

            if not content.strip():
                content = str(response_data.get("response") or "")

            try:
                parsed_response = extract_json_object(content)
            except (OllamaAlignmentError, json.JSONDecodeError) as error:
                raise OllamaAlignmentError(
                    f"Ollama structured output could not be decoded "
                    f"for {fragment_id}: {content[:1000]!r}"
                ) from error

            parsed_response["model_provider"] = "ollama"
            parsed_response["model_name"] = self.model
            return parsed_response, response_data, parse_usage(response_data)

        raise OllamaAlignmentError(
            f"Ollama failed after {self.maximum_attempts} attempts: "
            f"{last_error}"
        )

    def _request(
        self,
        method: str,
        url: str,
        payload: Mapping[str, Any] | None = None,
    ) -> _HttpResult:
        try:
            response = self.session.request(
                method,
                url,
                json=dict(payload) if payload is not None else None,
                timeout=self.timeout,
            )
            self.last_transport = "requests"

            try:
                parsed = response.json()
            except ValueError:
                parsed = {}

            return _HttpResult(
                status_code=response.status_code,
                text=response.text,
                payload=parsed,
            )
        except requests.RequestException as error:
            if not self.allow_windows_curl_fallback or not WINDOWS_CURL.exists():
                raise OllamaAlignmentError(
                    f"Cannot reach Ollama at {self.host}: {error}"
                ) from error

            self.last_transport = "windows_curl"
            return self._windows_curl_request(method, url, payload)

    def _windows_curl_request(
        self,
        method: str,
        url: str,
        payload: Mapping[str, Any] | None,
    ) -> _HttpResult:
        """Reach Windows-localhost Ollama from WSL via curl.exe."""

        command = [
            str(WINDOWS_CURL),
            "-sS",
            "-X",
            method,
            "--max-time",
            str(max(int(self.timeout), 1)),
            "-w",
            "\n__HTTP_STATUS__:%{http_code}",
        ]
        body_path: Path | None = None

        if payload is not None:
            temp_dir = _windows_temp_dir()

            if temp_dir is None:
                raise OllamaAlignmentError(
                    "Ollama is not reachable from WSL, and no Windows "
                    "temp directory was found for curl.exe fallback."
                )

            handle = tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".json",
                prefix="moodle_ollama_",
                dir=temp_dir,
                delete=False,
            )
            body_path = Path(handle.name)

            with handle:
                json.dump(dict(payload), handle, ensure_ascii=False)

            command.extend(
                [
                    "-H",
                    "Content-Type: application/json",
                    "--data-binary",
                    f"@{_windows_path_for(body_path)}",
                ]
            )

        command.append(url)

        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
        finally:
            if body_path is not None and body_path.exists():
                body_path.unlink()

        if completed.returncode != 0 and not completed.stdout.strip():
            raise OllamaAlignmentError(
                "Windows curl.exe could not reach Ollama: "
                + (completed.stderr.strip() or completed.stdout.strip())
            )

        stdout = completed.stdout
        status_code = 0
        marker = "\n__HTTP_STATUS__:"

        if marker in stdout:
            stdout, status_text = stdout.rsplit(marker, 1)
            try:
                status_code = int(status_text.strip())
            except ValueError:
                status_code = 0

        try:
            parsed = json.loads(stdout) if stdout.strip() else {}
        except json.JSONDecodeError:
            parsed = {}

        return _HttpResult(
            status_code=status_code or (200 if parsed else 502),
            text=stdout,
            payload=parsed,
        )
