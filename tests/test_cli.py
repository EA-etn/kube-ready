"""End-to-end tests through ``main()``: exit codes, formats, config."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kube_ready.cli import EXIT_FINDINGS, EXIT_OK, EXIT_USAGE, main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_good_examples_are_ready(capsys):
    assert main(["check", str(EXAMPLES / "good"), "--fail-on", "info"]) == EXIT_OK
    assert "Ready" in capsys.readouterr().out


def test_bad_examples_fail(capsys):
    assert main(["check", str(EXAMPLES / "bad"), "--no-color"]) == EXIT_FINDINGS
    out = capsys.readouterr().out
    assert "RDY001" in out and "RDY015" in out and "line 2" in out


def test_fail_on_never_always_succeeds():
    assert main(["check", str(EXAMPLES / "bad"), "--fail-on", "never"]) == EXIT_OK


def test_fail_on_warning(tmp_path):
    (tmp_path / "s.yaml").write_text(
        "apiVersion: v1\nkind: Secret\nmetadata: {name: s, namespace: ns}\nstringData: {k: v}\n"
    )
    assert main(["check", str(tmp_path)]) == EXIT_OK  # a warning does not fail by default
    assert main(["check", str(tmp_path), "--fail-on", "warning"]) == EXIT_FINDINGS


def test_json_output(capsys):
    assert main(["check", str(EXAMPLES / "bad"), "-f", "json"]) == EXIT_FINDINGS
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["errors"] >= 4
    first = data["findings"][0]
    assert {"rule", "severity", "message", "hint", "resource", "file", "line"} <= set(first)


def test_sarif_output(capsys):
    main(["check", str(EXAMPLES / "bad"), "-f", "sarif"])
    sarif = json.loads(capsys.readouterr().out)
    assert sarif["version"] == "2.1.0"
    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "kube-ready"
    rule_ids = {r["id"] for r in run["tool"]["driver"]["rules"]}
    for result in run["results"]:
        assert result["ruleId"] in rule_ids
        assert result["level"] in {"error", "warning", "note"}
        loc = result["locations"][0]["physicalLocation"]
        assert loc["region"]["startLine"] >= 1


def test_output_file(tmp_path):
    out = tmp_path / "report.sarif"
    main(["check", str(EXAMPLES / "bad"), "-f", "sarif", "-o", str(out)])
    assert json.loads(out.read_text())["runs"]


def test_stdin(monkeypatch, capsys):
    import io

    monkeypatch.setattr(
        "sys.stdin", io.StringIO((EXAMPLES / "good" / "deployment.yaml").read_text())
    )
    assert main(["check", "-"]) == EXIT_OK


def test_invalid_yaml_is_reported(tmp_path, capsys):
    (tmp_path / "broken.yaml").write_text("apiVersion: v1\nkind: [\n")
    assert main(["check", str(tmp_path), "--no-color"]) == EXIT_FINDINGS
    assert "RDY000" in capsys.readouterr().out


def test_missing_path():
    assert main(["check", "/nonexistent/path.yaml"]) == EXIT_USAGE


def test_unknown_rule_in_disable():
    assert main(["check", str(EXAMPLES / "good"), "--disable", "RDY999"]) == EXIT_USAGE


def test_disable_flag(capsys):
    main(["check", str(EXAMPLES / "bad"), "-f", "json", "--disable", "RDY001,RDY015"])
    rules = {f["rule"] for f in json.loads(capsys.readouterr().out)["findings"]}
    assert not rules & {"RDY001", "RDY015"}


def test_config_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".kube-ready.yaml").write_text(
        "disable: [RDY017, RDY016]\nseverity:\n  RDY014: error\nfail-on: warning\n"
    )
    (tmp_path / "s.yaml").write_text(
        "apiVersion: v1\nkind: Secret\nmetadata: {name: s}\nstringData: {k: v}\n"
    )
    assert main(["check", "s.yaml", "-f", "json"]) == EXIT_FINDINGS
    findings = json.loads(capsys.readouterr().out)["findings"]
    assert [(f["rule"], f["severity"]) for f in findings] == [("RDY014", "error")]


@pytest.mark.parametrize(
    "body",
    ["disable: [RDY999]\n", "severity: {RDY001: loud}\n", "fail-on: maybe\n", "- not a mapping\n"],
)
def test_bad_config_is_usage_error(tmp_path, body):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(body)
    assert main(["check", str(EXAMPLES / "good"), "--config", str(cfg)]) == EXIT_USAGE


def test_rules_command(capsys):
    assert main(["rules"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "RDY001" in out and "RDY018" in out


# Baselines
def test_baseline_roundtrip(tmp_path, capsys):
    bad = EXAMPLES / "bad"
    base = tmp_path / "base.json"
    assert main(["baseline", str(bad), "-o", str(base)]) == EXIT_OK
    assert "recorded" in capsys.readouterr().out
    doc = json.loads(base.read_text())
    assert doc["findings"] and all("|" in f for f in doc["findings"])

    # Same manifests, baseline applied: nothing new, exit 0 even at --fail-on info
    rc = main(["check", str(bad), "--baseline", str(base), "--fail-on", "info", "--no-color"])
    out = capsys.readouterr().out
    assert rc == EXIT_OK
    assert "no new findings" in out and "hidden by baseline" in out


def test_baseline_reports_only_new_findings(tmp_path, capsys):
    manifest = tmp_path / "s.yaml"
    manifest.write_text(
        "apiVersion: v1\nkind: Secret\nmetadata: {name: s, namespace: ns}\nstringData: {k: v}\n"
    )
    base = tmp_path / "base.json"
    main(["baseline", str(manifest), "-o", str(base)])
    capsys.readouterr()

    # A second, new Secret appears: only that one is reported
    manifest.write_text(
        manifest.read_text()
        + "---\napiVersion: v1\nkind: Secret\nmetadata: {name: new, namespace: ns}\n"
        "stringData: {k: v}\n"
    )
    rc = main(["check", str(manifest), "--baseline", str(base), "-f", "json"])
    data = json.loads(capsys.readouterr().out)
    assert rc == EXIT_OK  # warning only
    assert [f["resource"]["name"] for f in data["findings"]] == ["new"]
    assert data["summary"]["baselined"] == 1


def test_baseline_survives_moving_the_file(tmp_path, capsys):
    (tmp_path / "a.yaml").write_text(
        "apiVersion: v1\nkind: Secret\nmetadata: {name: s, namespace: ns}\nstringData: {k: v}\n"
    )
    base = tmp_path / "base.json"
    main(["baseline", str(tmp_path / "a.yaml"), "-o", str(base)])
    (tmp_path / "a.yaml").rename(tmp_path / "b.yaml")
    rc = main(["check", str(tmp_path / "b.yaml"), "--baseline", str(base), "--fail-on", "info"])
    capsys.readouterr()
    assert rc == EXIT_OK


def test_baseline_from_config(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "s.yaml").write_text(
        "apiVersion: v1\nkind: Secret\nmetadata: {name: s, namespace: ns}\nstringData: {k: v}\n"
    )
    main(["baseline", "s.yaml"])  # default output file
    (tmp_path / ".kube-ready.yaml").write_text("baseline: .kube-ready-baseline.json\n")
    capsys.readouterr()
    assert main(["check", "s.yaml", "--fail-on", "info"]) == EXIT_OK
    assert "hidden by baseline" in capsys.readouterr().out


@pytest.mark.parametrize("body", ["not json", '{"findings": "nope"}', '{"findings": [1]}'])
def test_bad_baseline_is_usage_error(tmp_path, body):
    base = tmp_path / "base.json"
    base.write_text(body)
    assert main(["check", str(EXAMPLES / "good"), "--baseline", str(base)]) == EXIT_USAGE


def test_missing_baseline_is_usage_error(tmp_path):
    assert main(["check", str(EXAMPLES / "good"), "--baseline", str(tmp_path / "x")]) == EXIT_USAGE
