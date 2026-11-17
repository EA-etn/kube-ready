"""The programmatic API used by the browser playground."""

from __future__ import annotations

import json

from kube_ready import api


def test_check_text_reports_findings_with_titles():
    report = api.check_text(
        "apiVersion: v1\nkind: Secret\nmetadata: {name: s, namespace: ns}\nstringData: {k: v}\n"
    )
    assert report["summary"] == {"resources": 1, "errors": 0, "warnings": 1, "info": 0}
    assert report["findings"][0]["rule"] == "RDY014"
    assert report["findings"][0]["title"] == "Secret committed in plain text"
    json.dumps(report)  # JSON-able


def test_check_text_disabled_rules():
    report = api.check_text(
        "apiVersion: v1\nkind: Secret\nmetadata: {name: s, namespace: ns}\nstringData: {k: v}\n",
        disabled=["RDY014"],
    )
    assert report["findings"] == []


def test_check_text_invalid_yaml():
    report = api.check_text("kind: [\n")
    assert "invalid YAML" in report["error"] and report["line"] >= 1
    assert report["summary"]["errors"] == 1


def test_rules_listing():
    listing = api.rules()
    assert len(listing) >= 22 and listing[0]["id"] == "RDY001"


def test_api_does_not_need_rich():
    """The playground loads the package without rich; the API must not import it."""
    import importlib.util
    from pathlib import Path

    spec = importlib.util.find_spec("kube_ready.api")
    assert spec is not None and spec.origin is not None
    src = Path(spec.origin).read_text(encoding="utf-8")
    assert "import rich" not in src and "from rich" not in src
