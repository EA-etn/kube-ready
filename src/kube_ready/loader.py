"""Load Kubernetes resources from files, directories or stdin.

Multi-document YAML is supported, as is ``kind: List``. Each resource remembers the
file and line it came from, so reports (and SARIF) can point at it.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Iterator
from pathlib import Path

import yaml

from kube_ready.model import Finding, Resource, Severity

YAML_SUFFIXES = {".yaml", ".yml"}
STDIN = "-"


class LoadError(Exception):
    """A file could not be parsed. Reported as finding RDY000."""

    def __init__(self, source: str, line: int, message: str) -> None:
        super().__init__(message)
        self.source = source
        self.line = line
        self.message = message


def iter_files(paths: Iterable[str]) -> Iterator[str]:
    """Expand paths into YAML files. ``-`` means stdin and is yielded as-is."""
    seen: set[str] = set()
    for raw in paths:
        if raw == STDIN:
            if STDIN not in seen:
                seen.add(STDIN)
                yield STDIN
            continue
        path = Path(raw)
        if path.is_dir():
            candidates = sorted(p for p in path.rglob("*") if p.suffix.lower() in YAML_SUFFIXES)
        elif path.is_file():
            candidates = [path]
        else:
            raise FileNotFoundError(raw)
        for candidate in candidates:
            key = str(candidate)
            if key not in seen:
                seen.add(key)
                yield key


def parse_documents(text: str, source: str) -> list[Resource]:
    """Parse every YAML document in ``text`` that looks like a Kubernetes object."""
    resources: list[Resource] = []
    loader = yaml.SafeLoader(text)
    try:
        while loader.check_node():
            node = loader.get_node()
            if node is None:  # pragma: no cover - check_node() guarantees a node
                break
            line = node.start_mark.line + 1
            data = loader.construct_document(node)
            resources.extend(_as_resources(data, source, line))
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        line = mark.line + 1 if mark is not None else 1
        problem = getattr(exc, "problem", None) or str(exc)
        raise LoadError(source, line, f"invalid YAML: {problem}") from exc
    finally:
        loader.dispose()
    return resources


def _as_resources(data: object, source: str, line: int) -> list[Resource]:
    if not isinstance(data, dict) or "kind" not in data:
        return []
    if data.get("kind") == "List":
        items = data.get("items")
        if not isinstance(items, list):
            return []
        return [Resource(raw=i, source=source, line=line) for i in items if isinstance(i, dict)]
    return [Resource(raw=data, source=source, line=line)]


def load(paths: Iterable[str]) -> tuple[list[Resource], list[Finding], list[str]]:
    """Load all resources. Returns ``(resources, load_errors_as_findings, files)``."""
    resources: list[Resource] = []
    errors: list[Finding] = []
    files: list[str] = []
    for file in iter_files(paths):
        files.append(file)
        text = sys.stdin.read() if file == STDIN else Path(file).read_text(encoding="utf-8")
        try:
            resources.extend(parse_documents(text, file))
        except LoadError as exc:
            placeholder = Resource(
                raw={"kind": "File", "metadata": {"name": file}}, source=file, line=exc.line
            )
            errors.append(
                Finding(
                    rule_id="RDY000",
                    severity=Severity.ERROR,
                    message=exc.message,
                    resource=placeholder,
                    hint="Fix the YAML syntax; nothing in this file was checked.",
                )
            )
    return resources, errors, files
