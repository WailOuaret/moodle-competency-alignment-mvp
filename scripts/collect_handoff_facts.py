"""Collect verifiable facts about this repository into ``docs/handoff/facts.json``.

Every number that appears in the handoff pack must come from here (or from the
frozen report file this script cites), never from memory.

Usage
-----
    python scripts/collect_handoff_facts.py [--out docs/handoff/facts.json] [--skip-tests]

Side outputs, written next to ``--out``:
    loc_by_file.csv       per-file line counts
    licenses_direct.csv   declared direct dependencies
    licenses_all.csv      the whole installed environment
    facts_run_info.json   timestamps / machine info ONLY (R7)

The script is read-only: it never writes inside the repository except into the
handoff output directory.  It makes no network call and installs nothing.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# generic helpers
# --------------------------------------------------------------------------

CODE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".php", ".html", ".css", ".sql", ".sh", ".ps1"}
CONFIG_EXTENSIONS = {".toml", ".cfg", ".ini", ".yml", ".yaml", ".json"}
DOC_EXTENSIONS = {".md", ".tex", ".rst", ".txt"}
NOTEBOOK_EXTENSIONS = {".ipynb"}

LINE_COMMENT_MARKERS = {
    ".py": ("#",),
    ".sh": ("#",),
    ".ps1": ("#",),
    ".sql": ("--",),
    ".js": ("//",),
    ".jsx": ("//",),
    ".ts": ("//",),
    ".tsx": ("//",),
    ".php": ("//", "#"),
    ".css": (),
    ".html": (),
}

LANGUAGE_BY_EXT = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".php": "PHP",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
    ".sh": "Shell",
    ".ps1": "PowerShell",
}

COPYLEFT_TOKENS = ("GPL", "AGPL", "LGPL", "MPL", "EPL", "EUPL", "CDDL")


def rounded(value, digits: int = 6):
    if isinstance(value, float):
        return round(value, digits)
    return value


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def git(args: list[str]) -> str | None:
    """Run a read-only git command without a shell.  Returns None on failure."""
    try:
        done = subprocess.run(
            ["git", *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    return done.stdout.strip()


CREDENTIAL_URL = re.compile(r"(?P<scheme>[a-zA-Z][a-zA-Z0-9+.\-]*://)[^/@\s]+@")


def sanitize_url(url: str) -> str:
    """Strip embedded credentials: https://user:token@host/x -> https://host/x."""
    return CREDENTIAL_URL.sub(lambda m: m.group("scheme"), url)


# --------------------------------------------------------------------------
# 1. snapshot
# --------------------------------------------------------------------------

MANIFEST_PATH = ROOT / "reports" / "frozen_manifest_strengthening.json"


def collect_snapshot() -> dict:
    head = git(["rev-parse", "HEAD"])
    manifest_files: list[str] = []
    if MANIFEST_PATH.exists():
        manifest_files = sorted(read_json(MANIFEST_PATH).get("files", {}))

    porcelain = git(["status", "--porcelain"]) or ""
    uncommitted = sorted(line[3:].strip().strip('"') for line in porcelain.splitlines() if line.strip())

    return {
        "git_repository": git(["rev-parse", "--is-inside-work-tree"]) == "true",
        "head_commit": head,
        "head_commit_short": head[:12] if head else None,
        "has_commits": head is not None,
        "branch": git(["rev-parse", "--abbrev-ref", "HEAD"]),
        "commit_date": git(["log", "-1", "--format=%cI"]),
        "dirty": bool(uncommitted),
        "uncommitted_path_count": len(uncommitted),
        "uncommitted_paths": uncommitted,
        "frozen_manifest_path": rel(MANIFEST_PATH) if MANIFEST_PATH.exists() else None,
        "frozen_manifest_file_count": len(manifest_files),
        "note": (
            "The git repository exists but contains NO commits: there is no HEAD, no commit "
            "history and no author list. Every file is therefore untracked ('??') in git status."
            if head is None
            else None
        ),
        "source": "git rev-parse / git status --porcelain; reports/frozen_manifest_strengthening.json",
    }


# --------------------------------------------------------------------------
# 2. identity
# --------------------------------------------------------------------------

def _grep_first(path: Path, pattern: str) -> str | None:
    if not path.exists():
        return None
    match = re.search(pattern, read_text(path), re.MULTILINE)
    return match.group(1) if match else None


def collect_identity() -> dict:
    pyproject = ROOT / "pyproject.toml"
    readme = ROOT / "README.md"
    app = ROOT / "app.py"

    name = _grep_first(pyproject, r'^\s*name\s*=\s*"([^"]+)"')
    version = _grep_first(pyproject, r'^\s*version\s*=\s*"([^"]+)"')
    description = _grep_first(pyproject, r'^\s*description\s*=\s*"([^"]+)"')

    dunder_version = None
    for candidate in sorted((ROOT / "src").rglob("__init__.py")):
        found = _grep_first(candidate, r'^__version__\s*=\s*["\']([^"\']+)["\']')
        if found:
            dunder_version = {"value": found, "source": rel(candidate)}
            break

    page_title = None
    for candidate in [app, *sorted((ROOT / "pages").glob("*.py"))] if app.exists() else []:
        found = _grep_first(candidate, r'page_title\s*=\s*["\']([^"\']+)["\']')
        if found:
            page_title = {"value": found, "source": rel(candidate)}
            break

    readme_title = None
    if readme.exists():
        for line in read_text(readme).splitlines():
            if line.startswith("# "):
                readme_title = {"value": line[2:].strip(), "source": f"{rel(readme)}:1"}
                break

    tags = git(["tag", "--list"])

    return {
        "package_name": {"value": name, "source": f"{rel(pyproject)} [project].name"} if name else None,
        "package_version": {"value": version, "source": f"{rel(pyproject)} [project].version"} if version else None,
        "package_description": {"value": description, "source": f"{rel(pyproject)} [project].description"} if description else None,
        "dunder_version": dunder_version,
        "app_page_title": page_title,
        "readme_title": readme_title,
        "git_tags": sorted(t for t in (tags or "").splitlines() if t.strip()),
        "note": "No name or version is proposed by this script. Candidates only.",
        "source": "pyproject.toml, README.md, app.py, pages/*.py, git tag --list",
    }


# --------------------------------------------------------------------------
# 3. loc
# --------------------------------------------------------------------------

LOC_RULE = (
    "blank = line whose strip() is empty; comment = line whose first non-space characters "
    "are the language's line-comment marker (# for Python/Shell/PowerShell, -- for SQL, "
    "// for JS/TS/PHP); docstrings count as CODE; code = total - blank - comment. "
    "Scope = files in the frozen manifest with a code extension. Data, reports, virtualenvs, "
    "caches and vendored folders are never counted."
)

VENDORED_PREFIXES = ("data/source/",)

#: Files written for the Part A handoff pack itself.  They are NOT part of the
#: MVP, so they are counted in their own group and excluded from the MVP totals.
HANDOFF_TOOLING = frozenset(
    {
        "scripts/verify_frozen.py",
        "scripts/collect_handoff_facts.py",
        "scripts/ui_smoke_check.py",
        "scripts/build_handoff_zip.py",
        "tests/test_verify_frozen.py",
        "tests/test_handoff_facts.py",
        "tests/test_handoff_zip.py",
    }
)


def group_of(relpath: str) -> str:
    if relpath in HANDOFF_TOOLING:
        return "handoff_tooling"
    if relpath == "app.py" or relpath.startswith("pages/"):
        return "ui"
    if relpath.startswith("src/"):
        return "src"
    if relpath.startswith("scripts/"):
        return "scripts"
    if relpath.startswith("tests/"):
        return "tests"
    return "other"


def count_lines(path: Path, ext: str) -> dict:
    markers = LINE_COMMENT_MARKERS.get(ext, ())
    total = blank = comment = 0
    try:
        text = read_text(path)
    except OSError:
        return {"total": 0, "blank": 0, "comment": 0, "code": 0}
    for line in text.splitlines():
        total += 1
        stripped = line.strip()
        if not stripped:
            blank += 1
        elif markers and stripped.startswith(markers):
            comment += 1
    return {"total": total, "blank": blank, "comment": comment, "code": total - blank - comment}


def collect_loc(out_dir: Path) -> dict:
    if not MANIFEST_PATH.exists():
        return {"error": "frozen manifest missing; run scripts/verify_frozen.py --snapshot first"}

    manifest_paths = set(read_json(MANIFEST_PATH)["files"])

    rows: list[dict] = []
    per_group: dict[str, Counter] = defaultdict(Counter)
    per_language: dict[str, Counter] = defaultdict(Counter)
    config_counter = Counter()
    doc_counter = Counter()
    notebook_counter = Counter()
    vendored_skipped = 0

    for relpath in sorted(manifest_paths):
        if relpath.startswith(VENDORED_PREFIXES):
            vendored_skipped += 1
            continue
        ext = Path(relpath).suffix.lower()
        path = ROOT / relpath
        if not path.is_file():
            continue
        if ext in CODE_EXTENSIONS:
            counts = count_lines(path, ext)
            group = group_of(relpath)
            language = LANGUAGE_BY_EXT.get(ext, ext.lstrip("."))
            rows.append({"path": relpath, "group": group, "language": language, **counts})
            per_group[group].update(counts)
            per_group[group]["files"] += 1
            per_language[language].update(counts)
            per_language[language]["files"] += 1
        elif ext in CONFIG_EXTENSIONS and not relpath.startswith(("data/", "reports/")):
            config_counter.update(count_lines(path, ext))
            config_counter["files"] += 1
        elif ext in DOC_EXTENSIONS:
            doc_counter.update(count_lines(path, ext))
            doc_counter["files"] += 1
        elif ext in NOTEBOOK_EXTENSIONS:
            notebook_counter["files"] += 1

    # code files present on disk but NOT in the frozen manifest (added after snapshot)
    outside: list[dict] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in CODE_EXTENSIONS:
            continue
        relpath = rel(path)
        if relpath in manifest_paths or relpath.startswith(VENDORED_PREFIXES):
            continue
        if any(part in {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", "_handoff_dist"} for part in path.parts):
            continue
        counts = count_lines(path, path.suffix.lower())
        outside.append({"path": relpath, "group": group_of(relpath), "language": LANGUAGE_BY_EXT.get(path.suffix.lower(), ""), **counts})

    csv_path = out_dir / "loc_by_file.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["path", "group", "language", "total", "blank", "comment", "code"])
        for row in rows + outside:
            writer.writerow([row["path"], row["group"], row["language"], row["total"], row["blank"], row["comment"], row["code"]])

    def flat(counter: Counter) -> dict:
        return {
            "files": counter.get("files", 0),
            "total": counter.get("total", 0),
            "blank": counter.get("blank", 0),
            "comment": counter.get("comment", 0),
            "code": counter.get("code", 0),
        }

    groups = {name: flat(counter) for name, counter in sorted(per_group.items())}
    languages = {name: flat(counter) for name, counter in sorted(per_language.items())}
    code_tooling = groups.get("handoff_tooling", {}).get("code", 0)
    code_all = sum(g["code"] for g in groups.values()) - code_tooling
    code_tests = groups.get("tests", {}).get("code", 0)

    return {
        "rule": LOC_RULE,
        "handoff_tooling_excluded": {
            "files": sorted(HANDOFF_TOOLING),
            "code": code_tooling,
            "note": "Part A pack tooling, not part of the MVP; excluded from the totals below.",
        },
        "per_file_csv": csv_path.name,
        "by_group": groups,
        "by_language": languages,
        "code_including_tests": code_all,
        "code_excluding_tests": code_all - code_tests,
        "file_count": len(rows),
        "config_files": flat(config_counter),
        "documentation_files": flat(doc_counter),
        "notebooks": flat(notebook_counter),
        "vendored_files_skipped": vendored_skipped,
        "vendored_prefixes": list(VENDORED_PREFIXES),
        "code_files_outside_frozen_manifest": outside,
        "source": "counted from the files listed in reports/frozen_manifest_strengthening.json",
    }


# --------------------------------------------------------------------------
# 4. dependencies
# --------------------------------------------------------------------------

REQ_LINE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._\-]*)\s*(.*)$")


def parse_requirements(path: Path) -> list[tuple[str, str]]:
    out = []
    if not path.exists():
        return out
    for line in read_text(path).splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        match = REQ_LINE.match(line)
        if match:
            out.append((match.group(1), match.group(2).strip()))
    return out


def select_license(license_expr: str | None, license_field: str | None, classifiers: list[str]) -> tuple[str, str]:
    """Resolve a distribution's license, in the documented fallback order.

    License-Expression -> License -> ``License ::`` classifiers -> UNKNOWN.
    A ``License`` field holding the full license text (long or multi-line) is not
    a usable value, so it falls through to the classifiers.
    """
    if license_expr and license_expr.strip():
        return license_expr.strip(), "License-Expression"
    short_field = bool(license_field and len(license_field.strip()) < 200 and "\n" not in license_field.strip())
    if short_field:
        return license_field.strip(), "License"
    if classifiers:
        return "; ".join(c.split("::")[-1].strip() for c in classifiers), "License :: classifier"
    if license_field and license_field.strip():
        return "UNKNOWN (license text inlined in metadata)", "License (full text)"
    return "UNKNOWN", "none"


def is_copyleft(license_value: str) -> bool:
    return any(token in license_value.upper() for token in COPYLEFT_TOKENS)


def installed_distributions() -> dict:
    from importlib import metadata

    result = {}
    for dist in metadata.distributions():
        try:
            meta = dist.metadata
            name = (meta["Name"] or "").strip()
        except Exception:  # pragma: no cover - broken dist metadata
            continue
        if not name:
            continue
        classifiers = [c for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
        license_value, license_source = select_license(
            meta.get("License-Expression"), meta.get("License"), classifiers
        )
        homepage = meta.get("Home-page") or ""
        if not homepage:
            for entry in meta.get_all("Project-URL") or []:
                if entry.lower().startswith(("homepage", "source", "repository")):
                    homepage = entry.split(",", 1)[-1].strip()
                    break
        result[name.lower().replace("_", "-")] = {
            "name": name,
            "version": dist.version,
            "license": license_value,
            "license_source": license_source,
            "homepage": sanitize_url(homepage),
            "copyleft": is_copyleft(license_value),
        }
    return result


def collect_dependencies(out_dir: Path) -> dict:
    installed = installed_distributions()

    declared: dict[str, dict] = {}
    for source_name in ("requirements.txt", "requirements-lock.txt"):
        for pkg, spec in parse_requirements(ROOT / source_name):
            key = pkg.lower().replace("_", "-")
            entry = declared.setdefault(key, {"package": pkg, "specs": [], "declared_in": []})
            entry["specs"].append(spec or "(any)")
            entry["declared_in"].append(source_name)

    pyproject = ROOT / "pyproject.toml"
    pyproject_deps: list[str] = []
    if pyproject.exists():
        block = re.search(r"^dependencies\s*=\s*\[(.*?)\]", read_text(pyproject), re.S | re.M)
        if block:
            pyproject_deps = re.findall(r'"([^"]+)"', block.group(1))
            for raw in pyproject_deps:
                match = REQ_LINE.match(raw)
                if match:
                    key = match.group(1).lower().replace("_", "-")
                    entry = declared.setdefault(key, {"package": match.group(1), "specs": [], "declared_in": []})
                    entry["specs"].append(match.group(2).strip() or "(any)")
                    entry["declared_in"].append("pyproject.toml")

    direct = []
    for key in sorted(declared):
        entry = declared[key]
        info = installed.get(key, {})
        direct.append(
            {
                "package": entry["package"],
                "spec": " | ".join(dict.fromkeys(entry["specs"])),
                "declared_in": sorted(set(entry["declared_in"])),
                "installed_version": info.get("version"),
                "license": info.get("license", "UNKNOWN (not installed)"),
                "license_source": info.get("license_source", "not installed"),
                "homepage": info.get("homepage", ""),
                "copyleft": bool(info.get("copyleft", False)),
            }
        )

    with (out_dir / "licenses_direct.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["package", "spec", "declared_in", "installed_version", "license", "license_source", "copyleft", "homepage"])
        for row in direct:
            writer.writerow([row["package"], row["spec"], ";".join(row["declared_in"]), row["installed_version"] or "",
                             row["license"], row["license_source"], str(row["copyleft"]).lower(), row["homepage"]])

    with (out_dir / "licenses_all.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["package", "version", "license", "license_source", "copyleft", "homepage"])
        for key in sorted(installed):
            row = installed[key]
            writer.writerow([row["name"], row["version"], row["license"], row["license_source"], str(row["copyleft"]).lower(), row["homepage"]])

    package_json = ROOT / "package.json"

    return {
        "direct": direct,
        "direct_count": len(direct),
        "copyleft": sorted(d["package"] for d in direct if d["copyleft"]),
        "unknown_license": sorted(d["package"] for d in direct if d["license"].upper().startswith("UNKNOWN")),
        "installed_total": len(installed),
        "javascript": {"package_json_present": package_json.exists()},
        "source": "requirements.txt, requirements-lock.txt, pyproject.toml + importlib.metadata of the running interpreter",
    }


# --------------------------------------------------------------------------
# 5. external services
# --------------------------------------------------------------------------

def collect_external_services() -> dict:
    services = []

    gemini_manifest = ROOT / "data" / "interim" / "gemini_run_manifest.json"
    ollama_manifest = ROOT / "data" / "experiments" / "ollama_constrained_manifest.json"

    def default_model(path: Path, pattern: str) -> dict | None:
        if not path.exists():
            return None
        for number, line in enumerate(read_text(path).splitlines(), 1):
            match = re.search(pattern, line)
            if match:
                return {"value": match.group(1), "source": f"{rel(path)}:{number}"}
        return None

    gemini_default = default_model(ROOT / "src" / "moodle_competency" / "settings.py", r'GEMINI_MODEL[^"\']*["\']([^"\']+)["\']')
    ollama_default = default_model(ROOT / "src" / "moodle_competency" / "settings.py", r'OLLAMA_MODEL[^"\']*["\']([^"\']+)["\']')

    if gemini_manifest.exists():
        manifest = read_json(gemini_manifest)
        services.append(
            {
                "provider": "Google Gemini",
                "frozen_run_model": manifest.get("model_id"),
                "frozen_run_model_source": f"{rel(gemini_manifest)} #model_id",
                "code_default_model": gemini_default,
                "temperature": manifest.get("temperature"),
                "max_selections": manifest.get("max_selections"),
                "prompt_version": manifest.get("prompt_version"),
                "sdk": "google-genai",
                "endpoint_type": "Gemini API (remote HTTPS)",
                "locality": "remote",
                "key_required": True,
                "key_env_var_name": "GEMINI_API_KEY",
                "configured_in": "src/moodle_competency/settings.py, .env (not committed), .env.example",
                "used_by": ["src/moodle_competency/gemini_alignment.py", "scripts/10_run_gemini_alignments.py",
                            "src/moodle_competency/runtime_analysis.py"],
                "token_usage_recorded": manifest.get("current_session_usage"),
            }
        )

    if ollama_manifest.exists():
        manifest = read_json(ollama_manifest)
        services.append(
            {
                "provider": "Ollama (local server)",
                "frozen_run_model": manifest.get("model_name"),
                "frozen_run_model_source": f"{rel(ollama_manifest)} #model_name",
                "code_default_model": ollama_default,
                "temperature": manifest.get("temperature"),
                "max_selections": manifest.get("max_selections"),
                "sdk": "HTTP requests to the local Ollama server",
                "endpoint_type": f"local Ollama HTTP server ({manifest.get('host')})",
                "locality": "local",
                "key_required": False,
                "key_env_var_name": None,
                "configured_in": "src/moodle_competency/settings.py, .env (not committed), .env.example",
                "used_by": ["src/moodle_competency/ollama_alignment.py", "scripts/29_run_ollama_constrained.py",
                            "src/moodle_competency/runtime_analysis.py"],
                "token_usage_recorded": None,
            }
        )

    moodle_env_vars = sorted(
        set(re.findall(r"^(MOODLE_[A-Z_]+|DATABASE_[A-Z_]+|COMPETENCY_[A-Z_]+)=", read_text(ROOT / ".env.example"), re.M))
    ) if (ROOT / ".env.example").exists() else []

    services.append(
        {
            "provider": "Moodle instance",
            "frozen_run_model": None,
            "sdk": "requests (REST web services) + SQL extraction",
            "endpoint_type": "Moodle web-service REST API and/or Moodle database",
            "locality": "remote",
            "key_required": True,
            "key_env_var_name": "MOODLE_TOKEN",
            "configured_in": ".env.example / .env (not committed)",
            "used_by": ["src/moodle_competency/moodle_client.py", "scripts/01_extract_moodle_rest.py",
                        "scripts/02_extract_moodle_sql.py"],
            "other_env_var_names": moodle_env_vars,
        }
    )

    return {"services": services, "count": len(services),
            "source": "run manifests + settings.py + .env.example (NAMES only, no values)"}


# --------------------------------------------------------------------------
# 6. corpus  (through the existing loaders, R5)
# --------------------------------------------------------------------------

def collect_corpus() -> dict:
    sys.path.insert(0, str(ROOT / "src"))
    from moodle_competency.annotation import load_jsonl, read_csv  # existing loaders (R5)
    from moodle_competency.graph_checks import build_hierarchy_index

    fragments_path = ROOT / "data" / "processed" / "fragments.jsonl"
    resources_path = ROOT / "data" / "processed" / "resources.jsonl"
    # Authoritative competency file: the one the retrieval, graph and evaluation
    # scripts actually load (scripts/06 and scripts/23 both point here).
    competencies_path = ROOT / "data" / "processed" / "competencies.jsonl"
    ontology_subset_path = ROOT / "data" / "interim" / "competencies_subset.jsonl"
    gold_path = ROOT / "data" / "gold" / "manual_fragment_annotations.csv"
    candidates_path = ROOT / "data" / "interim" / "bm25_candidates.jsonl"

    out: dict = {"loaders": {
        "fragments": "moodle_competency.annotation.load_jsonl",
        "resources": "moodle_competency.annotation.load_jsonl",
        "competencies": "moodle_competency.annotation.load_jsonl",
        "reference": "moodle_competency.annotation.read_csv",
        "hierarchy": "moodle_competency.graph_checks.build_hierarchy_index",
    }}

    fragments = load_jsonl(fragments_path)
    out["fragment_count"] = len(fragments)
    out["fragments_source"] = rel(fragments_path)
    out["fragment_fields"] = sorted(fragments[0].keys()) if fragments else []
    out["fragments_per_course"] = dict(sorted(Counter(f.get("course_shortname") or f.get("course") for f in fragments).items()))
    out["fragments_per_resource_type"] = dict(sorted(Counter(f.get("resource_type") for f in fragments).items()))
    out["distinct_resource_ids_in_fragments"] = len({f.get("resource_id") for f in fragments})

    resources = load_jsonl(resources_path)
    out["resource_count"] = len(resources)
    out["resources_source"] = rel(resources_path)
    out["resources_per_type"] = dict(sorted(Counter(r.get("resource_type") for r in resources).items()))
    out["resources_per_course"] = dict(sorted(Counter(r.get("course_shortname") or r.get("course") for r in resources).items()))

    competencies = load_jsonl(competencies_path)
    out["competency_count"] = len(competencies)
    out["competencies_source"] = rel(competencies_path)
    out["competency_fields"] = sorted(competencies[0].keys()) if competencies else []
    out["competency_id_field"] = "idnumber"
    out["competency_ids"] = [c.get("idnumber") for c in competencies if c.get("idnumber")]
    out["competency_framework_idnumber"] = sorted({c.get("framework_idnumber") for c in competencies if c.get("framework_idnumber")})
    out["competency_titles"] = {c["idnumber"]: c.get("shortname") for c in competencies if c.get("idnumber")}

    index = build_hierarchy_index(competencies)
    parents = dict(index.get("parent_of", {}))
    depths = {}

    def depth_of(cid: str, seen=()) -> int:
        if cid in depths:
            return depths[cid]
        parent = parents.get(cid)
        value = 1 if not parent or parent in seen else depth_of(parent, (*seen, cid)) + 1
        depths[cid] = value
        return value

    for cid in out["competency_ids"]:
        depth_of(cid)
    out["hierarchy_edges"] = len(parents)
    out["hierarchy_max_depth"] = max(depths.values()) if depths else 0
    out["hierarchy_roots"] = list(index.get("roots", []))
    out["hierarchy_children"] = list(index.get("children", []))
    out["hierarchy_parent_of"] = dict(sorted(parents.items()))
    out["hierarchy_children_of"] = {k: v for k, v in sorted(index.get("children_of", {}).items()) if v}

    if ontology_subset_path.exists():
        subset = load_jsonl(ontology_subset_path)
        out["ontology_subset"] = {
            "path": rel(ontology_subset_path),
            "count": len(subset),
            "fields": sorted(subset[0].keys()) if subset else [],
            "uri_prefix_example": subset[0].get("uri") if subset else None,
            "labels_fr": {r.get("competency_id"): r.get("label_fr") for r in subset if r.get("competency_id")},
            "labels_en": {r.get("competency_id"): r.get("label_en") for r in subset if r.get("competency_id")},
            "note": "Ontology-derived intermediate. Hierarchy here is in the 'neighbors' field; the "
                    "pipeline's authoritative hierarchy is parent_idnumber in data/processed/competencies.jsonl.",
        }

    rows = read_csv(gold_path)
    out["reference_source"] = rel(gold_path)
    out["reference_row_count"] = len(rows)
    out["reference_columns"] = list(rows[0].keys()) if rows else []
    label_col = next((c for c in ("final_competency_ids", "competency_ids", "gold_competency_ids") if rows and c in rows[0]), None)
    out["reference_label_column"] = label_col
    if label_col:
        per_fragment = []
        total_labels = 0
        label_counter = Counter()
        for row in rows:
            raw = (row.get(label_col) or "").strip()
            labels = [part.strip() for part in re.split(r"[;,|]", raw) if part.strip()]
            per_fragment.append(len(labels))
            total_labels += len(labels)
            label_counter.update(labels)
        out["reference_label_total"] = total_labels
        out["reference_labels_per_fragment_distribution"] = dict(sorted(Counter(per_fragment).items()))
        out["reference_label_frequency"] = dict(sorted(label_counter.items()))
        out["reference_distinct_labels_used"] = len(label_counter)

    if candidates_path.exists():
        candidates = load_jsonl(candidates_path)
        out["bm25_candidate_rows"] = len(candidates)
        out["bm25_candidates_source"] = rel(candidates_path)
        out["bm25_candidate_fields"] = sorted(candidates[0].keys()) if candidates else []

    return out


# --------------------------------------------------------------------------
# 7. metrics  (PARSED from frozen files -- never recomputed)
# --------------------------------------------------------------------------

METRIC_SOURCES = [
    ("bm25_top1", "fragment", "reports/metrics/bm25_metrics.json", {
        "micro_precision": "top1_micro.precision", "micro_recall": "top1_micro.recall",
        "micro_f1": "top1_micro.f1", "macro_f1": "top1_macro.f1",
        "true_positives": "top1_micro.true_positives", "false_positives": "top1_micro.false_positives",
        "false_negatives": "top1_micro.false_negatives"}),
    ("bm25_retrieval", "fragment", "reports/metrics/bm25_metrics.json", {
        "recall_at_1": "recall_at_1", "recall_at_3": "recall_at_3", "recall_at_5": "recall_at_5",
        "hit_at_1": "hit_at_1", "hit_at_3": "hit_at_3", "hit_at_5": "hit_at_5", "mrr": "mrr"}),
    ("gemini_top5_constrained", "fragment", "reports/metrics/constrained_llm_metrics.json", {
        "micro_precision": "micro_precision", "micro_recall": "micro_recall", "micro_f1": "micro_f1",
        "macro_f1": "macro_f1", "exact_set_match": "exact_set_match", "coverage": "coverage",
        "abstention_rate": "abstention_rate", "average_predicted_labels": "average_predicted_labels"}),
    ("graph_posthoc", "fragment", "reports/metrics/graph_child_preference_fragment_metrics.json", {
        "micro_precision": "micro_precision", "micro_recall": "micro_recall", "micro_f1": "micro_f1",
        "macro_f1": "macro_f1", "exact_set_match": "exact_set_match", "coverage": "coverage",
        "abstention_rate": "abstention_rate", "average_predicted_labels": "average_predicted_labels",
        "parent_child_redundancy_count": "parent_child_redundancy_count"}),
    ("gemini_resource", "resource", "reports/metrics/resource_level_metrics.json", {
        "micro_precision": "micro_precision", "micro_recall": "micro_recall", "micro_f1": "micro_f1",
        "macro_f1": "macro_f1", "exact_set_match": "exact_set_match", "coverage": "resource_coverage",
        "abstention_rate": "resource_abstention_rate", "true_positives": "micro_true_positives",
        "false_positives": "micro_false_positives", "false_negatives": "micro_false_negatives",
        "resource_count": "resource_count"}),
    ("graph_posthoc_resource", "resource", "reports/metrics/graph_child_preference_resource_metrics.json", {
        "micro_precision": "micro_precision", "micro_recall": "micro_recall", "micro_f1": "micro_f1",
        "macro_f1": "macro_f1", "exact_set_match": "exact_set_match", "coverage": "resource_coverage",
        "abstention_rate": "resource_abstention_rate", "true_positives": "micro_true_positives",
        "false_positives": "micro_false_positives", "false_negatives": "micro_false_negatives",
        "resource_count": "resource_count"}),
]

R6_ANCHORS = {
    ("gemini_top5_constrained", "micro_precision"): 0.7255,
    ("gemini_top5_constrained", "micro_recall"): 0.9737,
    ("gemini_top5_constrained", "micro_f1"): 0.8315,
    ("graph_posthoc", "micro_f1"): 0.9367,
}

OLLAMA_PROMPT_ANCHORS = {"micro_precision": 0.7619, "micro_recall": 0.8421, "micro_f1": 0.8000}


def dig(payload, dotted: str):
    node = payload
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def collect_metrics() -> dict:
    systems = []
    for system, level, relpath, keys in METRIC_SOURCES:
        path = ROOT / relpath
        if not path.exists():
            systems.append({"system": system, "level": level, "status": "SOURCE_FILE_MISSING", "source": relpath})
            continue
        payload = read_json(path)
        values = {}
        for name, dotted in keys.items():
            value = dig(payload, dotted)
            if value is not None:
                values[name] = {"value": rounded(value), "source": f"{relpath} #{dotted}"}
        systems.append({"system": system, "level": level, "source": relpath,
                        "status": payload.get("status", "UNKNOWN"), "values": values})

    # anchor check (R6)
    anchor_check = []
    by_system = {entry["system"]: entry for entry in systems}
    for (system, metric), expected in sorted(R6_ANCHORS.items()):
        actual = by_system.get(system, {}).get("values", {}).get(metric, {}).get("value")
        ok = actual is not None and abs(actual - expected) <= 1e-4
        anchor_check.append({"system": system, "metric": metric, "anchor": expected,
                             "frozen_value": actual, "within_1e-4": ok})

    ollama_metric_files = sorted(
        rel(p) for p in (ROOT / "reports").rglob("*ollama*") if p.is_file() and p.suffix == ".json"
    )
    ollama = {
        "status": "NOT_PRESENT",
        "explanation": (
            "No frozen Ollama metrics file exists. scripts/30_evaluate_ollama_constrained.py exists but was "
            "not run as part of the frozen evaluation; reports/tables/final_results_summary.csv leaves every "
            "Ollama metric cell as NA."
        ),
        "metric_files_found": ollama_metric_files,
        "checkpoints_present": [
            rel(p) for p in sorted((ROOT / "data" / "experiments").glob("ollama_constrained_*")) if p.is_file()
        ],
        "prompt_anchor_values_not_reproducible": OLLAMA_PROMPT_ANCHORS,
        "source": "reports/tables/final_results_summary.csv; reports/FINAL_INTERNSHIP_REPORT.md section 26",
    }

    evidence_path = ROOT / "reports" / "metrics" / "evidence_review_summary.json"
    evidence = {}
    if evidence_path.exists():
        payload = read_json(evidence_path)
        evidence = {
            "rows": payload.get("rows"),
            "mechanically_valid": payload.get("mechanically_valid"),
            "mechanical_validity_rate": rounded(payload.get("mechanical_validity_rate")),
            "pedagogical_rating_counts": payload.get("pedagogical_rating_counts"),
            "pedagogical_clear_rate": rounded(payload.get("pedagogical_clear_rate")),
            "pedagogical_partial_rate": rounded(payload.get("pedagogical_partial_rate")),
            "pedagogical_unsupported_rate": rounded(payload.get("pedagogical_unsupported_rate")),
            "source": rel(evidence_path),
        }

    human_path = ROOT / "reports" / "metrics" / "human_validation_summary.json"
    human = {}
    if human_path.exists():
        payload = read_json(human_path)
        human = {
            "status": payload.get("status"),
            "message": payload.get("message"),
            "teacher_review_count": payload.get("teacher_review_count"),
            "supervisor_review_count": payload.get("supervisor_review_count"),
            "researcher_review_count": payload.get("researcher_review_count"),
            "teacher_or_supervisor_validation_performed": payload.get("teacher_or_supervisor_validation_performed"),
            "significance_tests": payload.get("significance_tests"),
            "source": rel(human_path),
        }

    graph_path = ROOT / "reports" / "metrics" / "graph_check_summary.json"
    graph = {}
    if graph_path.exists():
        payload = read_json(graph_path)
        graph = {k: payload.get(k) for k in (
            "fragments_checked", "fragments_with_parent_child_redundancy", "redundant_parent_child_pairs",
            "fragments_with_granularity_conflict", "invalid_hierarchy_references", "most_frequent_redundant_parent",
            "original_predictions_modified", "warning_rate")}
        graph["warning_rate"] = rounded(graph.get("warning_rate"))
        graph["source"] = rel(graph_path)

    error_path = ROOT / "reports" / "metrics" / "error_summary.json"
    errors = {}
    if error_path.exists():
        payload = read_json(error_path)
        errors = {"fragments": payload.get("fragments"),
                  "primary_category_counts": payload.get("primary_category_counts"),
                  "category_counts": payload.get("category_counts"),
                  "evidence_quality": payload.get("evidence_quality"),
                  "source": rel(error_path)}

    return {"systems": systems, "r6_anchor_check": anchor_check, "ollama": ollama,
            "evidence_validation": evidence, "human_validation": human,
            "graph_checks": graph, "error_analysis": errors,
            "note": "All values are PARSED from frozen report files. Nothing here is recomputed."}


# --------------------------------------------------------------------------
# 8. tests
# --------------------------------------------------------------------------

PRE_EXISTING_TEST_GLOB = "tests/test_*.py"
NEW_PART_A_TESTS = {"tests/test_verify_frozen.py", "tests/test_handoff_facts.py", "tests/test_handoff_zip.py"}


def collect_tests(skip: bool) -> tuple[dict, dict]:
    manifest_files = set(read_json(MANIFEST_PATH)["files"]) if MANIFEST_PATH.exists() else set()
    pre_existing = sorted(
        rel(p) for p in ROOT.glob(PRE_EXISTING_TEST_GLOB)
        if rel(p) in manifest_files and rel(p) not in NEW_PART_A_TESTS
    )

    function_count = 0
    per_file = {}
    for relpath in pre_existing:
        found = len(re.findall(r"^\s*def (test_\w+)", read_text(ROOT / relpath), re.M))
        per_file[relpath] = found
        function_count += found

    facts = {
        "scope": "pre_existing_regression_subset",
        "scope_note": (
            "This is a SUBSET of the test suite, not the project total. It runs only "
            "the test files present in the frozen manifest at the time of the "
            "hardening phase, excluding test files added afterwards. The "
            "authoritative total comes from `python -m pytest -q` over tests/."
        ),
        "is_project_total": False,
        "authoritative_total_command": "python -m pytest -q",
        "pre_existing_test_files": len(pre_existing),
        "pre_existing_test_functions": function_count,
        "excluded_test_files": sorted(
            rel(p) for p in ROOT.glob(PRE_EXISTING_TEST_GLOB)
            if rel(p) not in set(pre_existing)
        ),
        "test_functions_per_file": per_file,
        "source": "counted from the tests/ files listed in the frozen manifest",
    }
    timing = {}

    if skip:
        facts["run"] = {"status": "SKIPPED", "reason": "--skip-tests"}
        return facts, timing

    env = dict(os.environ)
    env.pop("LBG_ALLOW_LIVE", None)
    started = datetime.now(timezone.utc)
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *pre_existing],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=3600,
    )
    finished = datetime.now(timezone.utc)
    tail = done.stdout.strip().splitlines()[-1] if done.stdout.strip() else ""
    counts = {key: int(value) for value, key in re.findall(r"(\d+) (passed|failed|skipped|error|xfailed|xpassed|warning)", done.stdout)}
    facts["run"] = {
        "status": "PASSED" if done.returncode == 0 else "FAILED",
        "exit_code": done.returncode,
        "passed": counts.get("passed", 0),
        "failed": counts.get("failed", 0) + counts.get("error", 0),
        "skipped": counts.get("skipped", 0),
        "summary_line": tail,
        "command": f"{Path(sys.executable).name} -m pytest -q <{len(pre_existing)} pre-existing test files>",
        "scope": "pre_existing_regression_subset (NOT the project total)",
        "env_note": "LBG_ALLOW_LIVE was unset for this run (R3).",
    }
    timing = {"tests_started_utc": started.isoformat(), "tests_finished_utc": finished.isoformat(),
              "tests_duration_seconds": round((finished - started).total_seconds(), 3)}
    return facts, timing


# --------------------------------------------------------------------------
# 9. git
# --------------------------------------------------------------------------

def collect_git() -> dict:
    head = git(["rev-parse", "HEAD"])
    authors = []
    total_commits = 0
    first_commit = last_commit = None

    if head:
        log = git(["log", "--format=%an%x09%cI"]) or ""
        per_author: dict[str, list[str]] = defaultdict(list)
        for line in log.splitlines():
            if "\t" not in line:
                continue
            name, date = line.split("\t", 1)
            per_author[name.strip()].append(date.strip())
            total_commits += 1
        for name in sorted(per_author):
            dates = sorted(per_author[name])
            authors.append({"name": name, "commits": len(dates), "first_commit": dates[0], "last_commit": dates[-1]})
        all_dates = sorted(d for dates in per_author.values() for d in dates)
        first_commit, last_commit = (all_dates[0], all_dates[-1]) if all_dates else (None, None)

    remotes = []
    raw_remotes = git(["remote", "-v"]) or ""
    for line in raw_remotes.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            remotes.append({"name": parts[0], "url": sanitize_url(parts[1])})
    seen = set()
    remotes = [r for r in remotes if not (r["name"], r["url"]) in seen and not seen.add((r["name"], r["url"]))]

    ci_files = []
    for pattern in (".github/workflows/*.yml", ".github/workflows/*.yaml", ".gitlab-ci.yml", "Jenkinsfile", ".circleci/config.yml", "azure-pipelines.yml"):
        ci_files.extend(rel(p) for p in ROOT.glob(pattern) if p.is_file())

    license_files = [rel(p) for p in ROOT.glob("*") if p.is_file() and p.name.upper().startswith(("LICENSE", "COPYING"))]
    citation_files = [rel(p) for p in ROOT.glob("CITATION*") if p.is_file()]

    return {
        "authors": authors,
        "author_count": len(authors),
        "total_commits": total_commits,
        "first_commit_date": first_commit,
        "last_commit_date": last_commit,
        "local_branches": sorted(b.strip("* ").strip() for b in (git(["branch", "--list"]) or "").splitlines() if b.strip()),
        "remote_branches": sorted(b.strip() for b in (git(["branch", "-r", "--list"]) or "").splitlines() if b.strip()),
        "remotes": remotes,
        "ci_files": sorted(ci_files),
        "ci_present": bool(ci_files),
        "license_file": license_files[0] if license_files else None,
        "license_files": sorted(license_files),
        "citation_files": sorted(citation_files),
        "note": None if head else "No commits exist, so there is no author list and no commit dates in this repository.",
        "privacy": "Author e-mail addresses are deliberately NOT collected.",
        "source": "git log --format=%an%x09%cI, git remote -v (credentials stripped), filesystem checks",
    }


# --------------------------------------------------------------------------
# 10. provenance signals
# --------------------------------------------------------------------------

PROVENANCE_PATTERNS = [
    ("adapted_from", re.compile(r"adapted from", re.I)),
    ("copied_from", re.compile(r"copied from", re.I)),
    ("based_on", re.compile(r"based on", re.I)),
    ("source_comment", re.compile(r"^\s*(#|//|--)\s*source\s*:", re.I)),
    ("inspired_by", re.compile(r"inspired by", re.I)),
    ("spdx", re.compile(r"SPDX-License-Identifier")),
    ("copyright", re.compile(r"\bCopyright\b")),
    ("github_url", re.compile(r"https?://(?:www\.)?github\.com/\S+")),
    ("stackoverflow_url", re.compile(r"https?://\S*stackoverflow\.com/\S+")),
]

SCAN_DIRS = ("src", "scripts", "tests", "pages")


def collect_provenance() -> dict:
    hits = []
    targets = [ROOT / "app.py"]
    for name in SCAN_DIRS:
        targets.extend(p for p in (ROOT / name).rglob("*") if p.is_file() and p.suffix in CODE_EXTENSIONS)

    for path in sorted(targets):
        if not path.exists():
            continue
        for number, line in enumerate(read_text(path).splitlines(), 1):
            for label, pattern in PROVENANCE_PATTERNS:
                if pattern.search(line):
                    hits.append({"path": rel(path), "line": number, "signal": label, "text": line.strip()[:200]})

    vendored = []
    for path in sorted(ROOT.rglob(".git")):
        if path.is_dir() and path.parent.resolve() != ROOT:
            vendored.append({"path": rel(path.parent), "kind": "nested git repository"})

    todos = []
    for path in sorted(targets):
        if not path.exists():
            continue
        for number, line in enumerate(read_text(path).splitlines(), 1):
            if re.search(r"\b(TODO|FIXME|XXX|HACK)\b", line):
                todos.append({"path": rel(path), "line": number, "text": line.strip()[:200]})

    return {"signals": hits, "signal_count": len(hits), "vendored_directories": vendored,
            "todo_comments": todos, "todo_count": len(todos),
            "note": "List only. No judgement about ownership is made here.",
            "source": f"regex scan of app.py and {', '.join(SCAN_DIRS)}/ code files"}


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="docs/handoff/facts.json")
    parser.add_argument("--skip-tests", action="store_true", help="do not run the pre-existing pytest suite")
    args = parser.parse_args(argv)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_dir = out_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    started = datetime.now(timezone.utc)
    tests, timing = collect_tests(args.skip_tests)

    facts = {
        "schema": "handoff_facts/1",
        "snapshot": collect_snapshot(),
        "identity": collect_identity(),
        "loc": collect_loc(out_dir),
        "dependencies": collect_dependencies(out_dir),
        "external_services": collect_external_services(),
        "corpus": collect_corpus(),
        "metrics": collect_metrics(),
        "tests": tests,
        "git": collect_git(),
        "provenance_signals": collect_provenance(),
    }

    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(facts, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")

    run_info = {
        "generated_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cwd": str(ROOT),
        "argv": ["collect_handoff_facts.py", *(argv if argv is not None else sys.argv[1:])],
        **timing,
    }
    with (out_dir / "facts_run_info.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(run_info, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")

    print(f"facts written: {rel(out_path)}")
    print(f"  fragments={facts['corpus'].get('fragment_count')} resources={facts['corpus'].get('resource_count')} "
          f"competencies={facts['corpus'].get('competency_count')}")
    print(f"  code(excl tests)={facts['loc']['code_excluding_tests']} code(incl tests)={facts['loc']['code_including_tests']}")
    print(f"  direct deps={facts['dependencies']['direct_count']} copyleft={facts['dependencies']['copyleft']}")
    for row in facts["metrics"]["r6_anchor_check"]:
        flag = "OK" if row["within_1e-4"] else "MISMATCH"
        print(f"  anchor {flag}: {row['system']}.{row['metric']} anchor={row['anchor']} frozen={row['frozen_value']}")
    run = facts["tests"].get("run", {})
    n_files = facts["tests"].get("pre_existing_test_files", "?")
    print(
        f"  pre-existing regression subset ({n_files} files): "
        f"{run.get('status')} {run.get('summary_line', '')}"
    )
    print(
        "  NOTE: this is a SUBSET, not the project total. "
        "Run `python -m pytest -q` for the authoritative full-suite count."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
