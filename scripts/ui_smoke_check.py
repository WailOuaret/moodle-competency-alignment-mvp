"""Headless render check of the Streamlit interface, with the network blocked.

Loads ``app.py`` and every file under ``pages/`` through ``streamlit.testing.v1.AppTest``
and records whether each one renders without raising.  It only RENDERS: no button is
clicked, no widget is set, nothing is written to ``data/``.

Outbound sockets are monkeypatched to raise, so a page that tries to reach Gemini,
Ollama or Moodle fails loudly here instead of silently making a live call (R3).

    python scripts/ui_smoke_check.py [--out docs/handoff/ui_smoke_results.json]

This script fixes nothing.  A failing page is reported, not repaired (R1).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class NetworkBlocked(RuntimeError):
    """Raised instead of opening a socket during the smoke check."""


def block_network() -> None:
    """Make every outbound connection attempt fail immediately."""

    def refuse(*args, **kwargs):
        raise NetworkBlocked("network access is blocked during the UI smoke check")

    socket.socket.connect = refuse          # type: ignore[method-assign]
    socket.socket.connect_ex = refuse       # type: ignore[method-assign]
    socket.create_connection = refuse       # type: ignore[assignment]
    if hasattr(socket, "create_server"):
        socket.create_server = refuse       # type: ignore[assignment]
    socket.getaddrinfo = refuse             # type: ignore[assignment]


def discover_pages() -> list[Path]:
    """Both interfaces: the runtime app at the root and the corpus app in app/.

    Files starting with ``_`` are shared helpers, not pages, so they are skipped.
    """

    targets = [ROOT / "app.py"]

    pages_dir = ROOT / "pages"
    if pages_dir.is_dir():
        targets.extend(sorted(p for p in pages_dir.glob("*.py") if not p.name.startswith("_")))

    corpus_app = ROOT / "app" / "Home.py"
    if corpus_app.is_file():
        targets.append(corpus_app)

    corpus_pages = ROOT / "app" / "pages"
    if corpus_pages.is_dir():
        targets.extend(
            sorted(p for p in corpus_pages.glob("*.py") if not p.name.startswith("_"))
        )

    return [p for p in targets if p.is_file()]


def run_checks(timeout: float) -> dict:
    try:
        from streamlit.testing.v1 import AppTest
    except Exception as exc:  # pragma: no cover - depends on the environment
        return {
            "status": "NOT_RUN",
            "reason": f"streamlit.testing.v1.AppTest unavailable: {type(exc).__name__}: {exc}",
            "pages": [],
        }

    import streamlit as st

    block_network()

    results = []
    for path in discover_pages():
        relpath = path.relative_to(ROOT).as_posix()
        entry: dict = {"page": relpath, "status": "UNKNOWN"}
        try:
            app = AppTest.from_file(str(path), default_timeout=timeout)
            app.run()
            exceptions = [
                {"type": getattr(e, "type", None), "message": str(getattr(e, "value", e))[:500]}
                for e in app.exception
            ]
            entry["status"] = "OK" if not exceptions else "EXCEPTION"
            entry["exceptions"] = exceptions
            entry["widget_counts"] = {
                "button": len(app.button),
                "selectbox": len(app.selectbox),
                "radio": len(app.radio),
                "text_input": len(app.text_input),
                "markdown_blocks": len(app.markdown),
                "dataframe": len(app.dataframe),
            }
            entry["error_blocks"] = [str(e.value)[:300] for e in app.error]
            entry["warning_blocks"] = [str(w.value)[:300] for w in app.warning]
        except Exception as exc:
            entry["status"] = "LOAD_FAILED"
            entry["exceptions"] = [{"type": type(exc).__name__, "message": str(exc)[:500]}]
            entry["traceback_tail"] = traceback.format_exc().strip().splitlines()[-4:]
        results.append(entry)

    overall = "OK" if all(r["status"] == "OK" for r in results) else "ISSUES_FOUND"
    return {
        "status": overall,
        "reason": None,
        "streamlit_version": getattr(st, "__version__", None),
        "network": "blocked (socket.connect / create_connection / getaddrinfo patched to raise)",
        "note": "Render-only check. No widget was interacted with and no data file was written.",
        "pages": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="docs/handoff/ui_smoke_results.json")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(argv)

    os.environ.pop("LBG_ALLOW_LIVE", None)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    started = datetime.now(timezone.utc)
    payload = run_checks(args.timeout)
    payload["run_info"] = {
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }

    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")

    print(f"UI smoke check: {payload['status']}")
    if payload.get("reason"):
        print(f"  reason: {payload['reason']}")
    for row in payload["pages"]:
        detail = ""
        if row["status"] != "OK":
            first = (row.get("exceptions") or [{}])[0]
            detail = f"  <- {first.get('type')}: {str(first.get('message'))[:140]}"
        print(f"  {row['status']:<13} {row['page']}{detail}")
    try:
        written = out_path.relative_to(ROOT).as_posix()
    except ValueError:
        # --out may point outside the repository; show it as given.
        written = out_path.as_posix()

    print(f"written: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
