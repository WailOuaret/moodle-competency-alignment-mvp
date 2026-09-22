"""Write reports/reproducibility_manifest.json without secrets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from moodle_competency.reproducibility import write_reproducibility_manifest


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    path = write_reproducibility_manifest(PROJECT_ROOT)
    payload = json.loads(path.read_text(encoding="utf-8"))
    print("=== REPRODUCIBILITY MANIFEST ===")
    print(f"Python: {payload.get('python_version')}")
    print(f"Resources: {payload.get('resource_count')}")
    print(f"Fragments: {payload.get('fragment_count')}")
    print(f"Gemini validated: {payload.get('validated_gemini_count')}")
    print(f"Wrote: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
