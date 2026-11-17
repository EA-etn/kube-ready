"""The YAML loader: real-world inputs are messier than the examples."""

from __future__ import annotations

from pathlib import Path

from kube_ready.cli import EXIT_OK, main
from kube_ready.loader import iter_files, parse_documents


def test_helm_template_output_with_source_comments():
    text = """---
# Source: web/templates/service.yaml
apiVersion: v1
kind: Service
metadata: {name: web, namespace: shop}
spec: {selector: {app: web}, ports: [{port: 80}]}
---
# Source: web/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata: {name: web, namespace: shop}
spec: {replicas: 2, template: {metadata: {labels: {app: web}}, spec: {containers: []}}}
"""
    resources = parse_documents(text, "helm.yaml")
    assert [(r.kind, r.line) for r in resources] == [("Service", 3), ("Deployment", 9)]


def test_empty_and_comment_only_documents_are_skipped():
    assert parse_documents("", "e.yaml") == []
    assert parse_documents("---\n---\n# nothing here\n---\n", "e.yaml") == []
    assert parse_documents("null\n---\n~\n", "e.yaml") == []


def test_windows_line_endings():
    text = "apiVersion: v1\r\nkind: Namespace\r\nmetadata:\r\n  name: a\r\n"
    assert [r.kind for r in parse_documents(text, "w.yaml")] == ["Namespace"]


def test_kind_without_metadata_does_not_crash():
    res = parse_documents("kind: Weird\napiVersion: v1\n", "x.yaml")
    assert res[0].name == "<unnamed>" and res[0].namespace is None


def test_iter_files_recurses_dedupes_and_ignores_other_files(tmp_path):
    (tmp_path / "a.yaml").write_text("")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.yml").write_text("")
    (tmp_path / "sub" / "notes.txt").write_text("")
    (tmp_path / "sub" / "c.json").write_text("{}")
    files = list(iter_files([str(tmp_path), str(tmp_path / "a.yaml"), str(tmp_path / "sub")]))
    assert [Path(f).name for f in files] == ["a.yaml", "b.yml"]


def test_stdin_is_read_once(monkeypatch, capsys):
    import io

    monkeypatch.setattr(
        "sys.stdin", io.StringIO("apiVersion: v1\nkind: Namespace\nmetadata: {name: a}\n")
    )
    assert main(["check", "-", "-", "--fail-on", "info"]) == EXIT_OK
    assert "1 resources in 1 files" in capsys.readouterr().out


def test_directory_without_yaml_is_usage_error(tmp_path):
    (tmp_path / "readme.txt").write_text("hi")
    assert main(["check", str(tmp_path)]) == 2
