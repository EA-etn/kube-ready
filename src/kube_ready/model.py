"""Data model: the resources we check and the findings we report."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    @property
    def rank(self) -> int:
        return {"error": 3, "warning": 2, "info": 1}[self.value]

    @property
    def sarif_level(self) -> str:
        return {"error": "error", "warning": "warning", "info": "note"}[self.value]


WORKLOAD_KINDS = {"Pod", "Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job", "CronJob"}
SCALABLE_KINDS = {"Deployment", "StatefulSet", "ReplicaSet"}
BATCH_KINDS = {"Job", "CronJob"}


@dataclass
class Resource:
    """One Kubernetes object parsed from a YAML document."""

    raw: dict[str, Any]
    source: str
    line: int = 1

    @property
    def api_version(self) -> str:
        return str(self.raw.get("apiVersion", ""))

    @property
    def kind(self) -> str:
        return str(self.raw.get("kind", ""))

    @property
    def metadata(self) -> dict[str, Any]:
        meta = self.raw.get("metadata")
        return meta if isinstance(meta, dict) else {}

    @property
    def name(self) -> str:
        return str(self.metadata.get("name", "<unnamed>"))

    @property
    def namespace(self) -> str | None:
        ns = self.metadata.get("namespace")
        return str(ns) if ns else None

    @property
    def labels(self) -> dict[str, Any]:
        labels = self.metadata.get("labels")
        return labels if isinstance(labels, dict) else {}

    @property
    def annotations(self) -> dict[str, Any]:
        ann = self.metadata.get("annotations")
        return ann if isinstance(ann, dict) else {}

    @property
    def spec(self) -> dict[str, Any]:
        spec = self.raw.get("spec")
        return spec if isinstance(spec, dict) else {}

    @property
    def ref(self) -> str:
        """Human-readable identifier, e.g. ``Deployment/web`` or ``Deployment/prod/web``."""
        if self.namespace:
            return f"{self.kind}/{self.namespace}/{self.name}"
        return f"{self.kind}/{self.name}"

    @property
    def is_workload(self) -> bool:
        return self.kind in WORKLOAD_KINDS

    def pod_template(self) -> dict[str, Any] | None:
        """The pod template (``metadata`` + ``spec``) of a workload, if any."""
        if self.kind == "Pod":
            return {"metadata": self.metadata, "spec": self.spec}
        if self.kind == "CronJob":
            job = self.spec.get("jobTemplate", {})
            template = job.get("spec", {}).get("template") if isinstance(job, dict) else None
        else:
            template = self.spec.get("template")
        return template if isinstance(template, dict) else None

    def pod_spec(self) -> dict[str, Any] | None:
        template = self.pod_template()
        if template is None:
            return None
        spec = template.get("spec")
        return spec if isinstance(spec, dict) else None

    def pod_labels(self) -> dict[str, Any]:
        template = self.pod_template() or {}
        meta = template.get("metadata") or {}
        labels = meta.get("labels") if isinstance(meta, dict) else None
        return labels if isinstance(labels, dict) else {}

    def containers(self, include_init: bool = True) -> list[tuple[str, dict[str, Any]]]:
        """``(role, container)`` pairs. Role is ``container`` or ``initContainer``."""
        spec = self.pod_spec()
        if spec is None:
            return []
        out: list[tuple[str, dict[str, Any]]] = []
        keys = ["containers", "initContainers"] if include_init else ["containers"]
        for key in keys:
            items = spec.get(key)
            if not isinstance(items, list):
                continue
            role = "container" if key == "containers" else "initContainer"
            out.extend((role, c) for c in items if isinstance(c, dict))
        return out


@dataclass
class Finding:
    rule_id: str
    severity: Severity
    message: str
    resource: Resource
    hint: str = ""

    @property
    def fingerprint(self) -> str:
        """Stable identity of a finding, independent of file and line (for baselines)."""
        r = self.resource
        return f"{self.rule_id}|{r.kind}|{r.namespace or ''}|{r.name}|{self.message}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "hint": self.hint,
            "resource": {
                "kind": self.resource.kind,
                "name": self.resource.name,
                "namespace": self.resource.namespace,
            },
            "file": self.resource.source,
            "line": self.resource.line,
        }


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    resources: list[Resource] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    suppressed: int = 0
    baseline_file: str | None = None

    def count(self, severity: Severity) -> int:
        return sum(1 for f in self.findings if f.severity == severity)

    def worst(self) -> Severity | None:
        if not self.findings:
            return None
        return max((f.severity for f in self.findings), key=lambda s: s.rank)
