"""A tiny programmatic API: one call, plain dictionaries in and out.

Used by the browser playground (Pyodide) and handy for scripts. It does not import rich.
"""

from __future__ import annotations

from typing import Any

from kube_ready import __version__
from kube_ready.loader import LoadError, parse_documents
from kube_ready.model import Severity
from kube_ready.rules import RULES, run


def check_text(
    text: str, source: str = "manifest.yaml", disabled: list[str] | None = None
) -> dict[str, Any]:
    """Check one YAML document (or several, ``---`` separated) and return a JSON-able report."""
    try:
        resources = parse_documents(text, source)
    except LoadError as exc:
        return {
            "version": __version__,
            "error": exc.message,
            "line": exc.line,
            "summary": {"resources": 0, "errors": 1, "warnings": 0, "info": 0},
            "findings": [],
        }
    findings = run(resources, disabled=set(disabled or []))
    out = []
    for f in findings:
        d = f.to_dict()
        d["title"] = RULES[f.rule_id].title
        out.append(d)
    return {
        "version": __version__,
        "summary": {
            "resources": len(resources),
            "errors": sum(1 for f in findings if f.severity == Severity.ERROR),
            "warnings": sum(1 for f in findings if f.severity == Severity.WARNING),
            "info": sum(1 for f in findings if f.severity == Severity.INFO),
        },
        "findings": out,
    }


def rules() -> list[dict[str, str]]:
    return [
        {"id": r.id, "severity": r.severity.value, "title": r.title, "description": r.description}
        for r in RULES.values()
    ]
