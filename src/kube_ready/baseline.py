"""Baselines: accept today's findings, fail only on new ones.

``kube-ready baseline manifests/`` writes the fingerprints of every current finding.
``kube-ready check manifests/ --baseline FILE`` then hides those and reports only what
is new. Fingerprints ignore file and line, so moving a manifest does not resurrect it.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from kube_ready import __version__
from kube_ready.model import Finding

DEFAULT_FILE = ".kube-ready-baseline.json"


class BaselineError(Exception):
    pass


def write(findings: list[Finding], path: str) -> int:
    fingerprints = sorted({f.fingerprint for f in findings})
    doc = {
        "kube-ready": __version__,
        "generated": date.today().isoformat(),
        "findings": fingerprints,
    }
    Path(path).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return len(fingerprints)


def read(path: str) -> set[str]:
    file = Path(path)
    if not file.exists():
        raise BaselineError(f"baseline file not found: {path}")
    try:
        doc = json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BaselineError(f"{path}: invalid JSON: {exc}") from exc
    items = doc.get("findings") if isinstance(doc, dict) else None
    if not isinstance(items, list) or not all(isinstance(i, str) for i in items):
        raise BaselineError(f"{path}: expected a 'findings' list of strings")
    return set(items)


def apply(findings: list[Finding], known: set[str]) -> tuple[list[Finding], int]:
    """Split findings into (new, number suppressed)."""
    kept = [f for f in findings if f.fingerprint not in known]
    return kept, len(findings) - len(kept)
