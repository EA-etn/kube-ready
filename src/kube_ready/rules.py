"""The rules. Each one is a small function registered with ``@rule``.

A rule receives one resource and the full set of loaded resources (so it can look at
related objects, e.g. a PodDisruptionBudget for a Deployment) and yields findings.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from kube_ready.model import BATCH_KINDS, SCALABLE_KINDS, Finding, Resource, Severity

RuleFn = Callable[[Resource, "Context"], Iterable[Finding]]


@dataclass(frozen=True)
class Rule:
    id: str
    severity: Severity
    title: str
    description: str
    fn: RuleFn


@dataclass
class Context:
    resources: list[Resource]

    def find(self, kind: str) -> list[Resource]:
        return [r for r in self.resources if r.kind == kind]


RULES: dict[str, Rule] = {}


def rule(id: str, severity: Severity, title: str, description: str) -> Callable[[RuleFn], RuleFn]:
    def register(fn: RuleFn) -> RuleFn:
        if id in RULES:
            raise ValueError(f"duplicate rule id {id}")
        RULES[id] = Rule(id=id, severity=severity, title=title, description=description, fn=fn)
        return fn

    return register


def _finding(res: Resource, rule_id: str, message: str, hint: str = "") -> Finding:
    return Finding(
        rule_id=rule_id, severity=RULES[rule_id].severity, message=message, resource=res, hint=hint
    )


def _replicas(res: Resource) -> int:
    value = res.spec.get("replicas", 1)
    return value if isinstance(value, int) else 1


def _selector_matches(selector: Any, labels: dict[str, Any]) -> bool:
    """True if a ``matchLabels`` selector (the common case) selects ``labels``."""
    if not isinstance(selector, dict):
        return False
    match = selector.get("matchLabels")
    if not isinstance(match, dict) or not match:
        return False
    return all(labels.get(k) == v for k, v in match.items())


# --------------------------------------------------------------------------- images


@rule(
    "RDY001",
    Severity.ERROR,
    "Image tag is mutable",
    "Images must use an explicit, immutable tag or a digest. `latest` (or no tag) means "
    "you cannot tell what is running, and rollbacks do not roll anything back.",
)
def image_tag(res: Resource, _: Context) -> Iterator[Finding]:
    for role, c in res.containers():
        image = str(c.get("image", ""))
        if not image:
            continue
        if "@sha256:" in image:
            continue
        name_part = image.rsplit("/", 1)[-1]
        tag = name_part.split(":", 1)[1] if ":" in name_part else ""
        if tag in ("", "latest"):
            yield _finding(
                res,
                "RDY001",
                f'{role} "{c.get("name", "?")}" uses image "{image}" '
                f"{'with no tag' if not tag else 'with tag latest'}",
                "Pin a version (`app:1.4.2`) or a digest (`app@sha256:…`).",
            )


# ------------------------------------------------------------------------ resources


@rule(
    "RDY002",
    Severity.WARNING,
    "Missing resource requests",
    "Without CPU and memory requests the scheduler cannot place pods sensibly and "
    "they fall into the BestEffort QoS class: first to be evicted under pressure.",
)
def resource_requests(res: Resource, _: Context) -> Iterator[Finding]:
    for role, c in res.containers():
        requests = (c.get("resources") or {}).get("requests") or {}
        missing = [k for k in ("cpu", "memory") if k not in requests]
        if missing:
            yield _finding(
                res,
                "RDY002",
                f'{role} "{c.get("name", "?")}" has no {" or ".join(missing)} request',
                "Set `resources.requests.cpu` and `resources.requests.memory`.",
            )


@rule(
    "RDY003",
    Severity.WARNING,
    "Missing memory limit",
    "A container without a memory limit can take the whole node down with it. "
    "CPU limits are deliberately not required: they cause throttling and are often "
    "counter-productive.",
)
def memory_limit(res: Resource, _: Context) -> Iterator[Finding]:
    for role, c in res.containers():
        limits = (c.get("resources") or {}).get("limits") or {}
        if "memory" not in limits:
            yield _finding(
                res,
                "RDY003",
                f'{role} "{c.get("name", "?")}" has no memory limit',
                "Set `resources.limits.memory`.",
            )


# --------------------------------------------------------------------------- probes


@rule(
    "RDY004",
    Severity.WARNING,
    "Missing liveness probe",
    "Without a liveness probe a hung process keeps running forever. Not required for "
    "Jobs and CronJobs.",
)
def liveness_probe(res: Resource, _: Context) -> Iterator[Finding]:
    if res.kind in BATCH_KINDS:
        return
    for _role, c in res.containers(include_init=False):
        if "livenessProbe" not in c:
            yield _finding(
                res,
                "RDY004",
                f'container "{c.get("name", "?")}" has no livenessProbe',
                "Add a `livenessProbe` that fails only when a restart would help.",
            )


@rule(
    "RDY005",
    Severity.WARNING,
    "Missing readiness probe",
    "Without a readiness probe traffic reaches the pod before it can serve, and a "
    "rolling update can replace healthy pods with broken ones. Not required for Jobs "
    "and CronJobs.",
)
def readiness_probe(res: Resource, _: Context) -> Iterator[Finding]:
    if res.kind in BATCH_KINDS:
        return
    for _role, c in res.containers(include_init=False):
        if "readinessProbe" not in c:
            yield _finding(
                res,
                "RDY005",
                f'container "{c.get("name", "?")}" has no readinessProbe',
                "Add a `readinessProbe` so the Service only routes to ready pods.",
            )


# ---------------------------------------------------------------------- availability


def _hpa_min_replicas(res: Resource, ctx: Context) -> int | None:
    for hpa in ctx.find("HorizontalPodAutoscaler"):
        target = hpa.spec.get("scaleTargetRef") or {}
        if (
            target.get("kind") == res.kind
            and target.get("name") == res.name
            and hpa.namespace == res.namespace
        ):
            value = hpa.spec.get("minReplicas", 1)
            return value if isinstance(value, int) else 1
    return None


@rule(
    "RDY006",
    Severity.WARNING,
    "Single replica",
    "One replica means downtime on every rollout, node drain or crash. Satisfied by a "
    "HorizontalPodAutoscaler with `minReplicas >= 2` in the same set of manifests.",
)
def single_replica(res: Resource, ctx: Context) -> Iterator[Finding]:
    if res.kind not in SCALABLE_KINDS:
        return
    replicas = _replicas(res)
    hpa_min = _hpa_min_replicas(res, ctx)
    effective = hpa_min if hpa_min is not None else replicas
    if effective < 2:
        yield _finding(
            res,
            "RDY006",
            f"runs {effective} replica",
            "Set `spec.replicas: 2` or more, or add an HPA with `minReplicas: 2`.",
        )


@rule(
    "RDY007",
    Severity.INFO,
    "No PodDisruptionBudget",
    "With several replicas but no PodDisruptionBudget, a node drain can evict all of "
    "them at once. Looks for a PDB in the same namespace whose selector matches the pod "
    "labels.",
)
def pod_disruption_budget(res: Resource, ctx: Context) -> Iterator[Finding]:
    if res.kind not in {"Deployment", "StatefulSet"}:
        return
    hpa_min = _hpa_min_replicas(res, ctx)
    if (hpa_min if hpa_min is not None else _replicas(res)) < 2:
        return
    labels = res.pod_labels()
    for pdb in ctx.find("PodDisruptionBudget"):
        if pdb.namespace == res.namespace and _selector_matches(pdb.spec.get("selector"), labels):
            return
    yield _finding(
        res,
        "RDY007",
        "has several replicas but no PodDisruptionBudget",
        "Add a PodDisruptionBudget with `minAvailable: 1` (or `maxUnavailable`).",
    )


@rule(
    "RDY008",
    Severity.INFO,
    "Replicas not spread across nodes",
    "Several replicas on the same node die together. Use topologySpreadConstraints or "
    "podAntiAffinity so they land on different nodes.",
)
def spread(res: Resource, ctx: Context) -> Iterator[Finding]:
    if res.kind not in {"Deployment", "StatefulSet"}:
        return
    hpa_min = _hpa_min_replicas(res, ctx)
    if (hpa_min if hpa_min is not None else _replicas(res)) < 2:
        return
    spec = res.pod_spec() or {}
    affinity = spec.get("affinity") or {}
    if spec.get("topologySpreadConstraints") or affinity.get("podAntiAffinity"):
        return
    yield _finding(
        res,
        "RDY008",
        "has several replicas but no spread rule",
        "Add `topologySpreadConstraints` (topologyKey: kubernetes.io/hostname).",
    )


# --------------------------------------------------------------------------- security


@rule(
    "RDY009",
    Severity.ERROR,
    "Privileged or host namespace",
    "A privileged container, or one sharing the host network/PID/IPC namespaces, is "
    "effectively root on the node.",
)
def privileged(res: Resource, _: Context) -> Iterator[Finding]:
    spec = res.pod_spec()
    if spec is None:
        return
    for key in ("hostNetwork", "hostPID", "hostIPC"):
        if spec.get(key) is True:
            yield _finding(
                res,
                "RDY009",
                f"pod sets {key}: true",
                f"Remove `{key}` unless this is a node-level agent.",
            )
    for role, c in res.containers():
        if (c.get("securityContext") or {}).get("privileged") is True:
            yield _finding(
                res,
                "RDY009",
                f'{role} "{c.get("name", "?")}" is privileged',
                "Drop `privileged: true`; add specific capabilities instead.",
            )


@rule(
    "RDY010",
    Severity.WARNING,
    "Privilege escalation allowed",
    "`allowPrivilegeEscalation` defaults to true, which lets a process gain more "
    "privileges than its parent (setuid binaries, etc.).",
)
def privilege_escalation(res: Resource, _: Context) -> Iterator[Finding]:
    for role, c in res.containers():
        if (c.get("securityContext") or {}).get("allowPrivilegeEscalation") is not False:
            yield _finding(
                res,
                "RDY010",
                f'{role} "{c.get("name", "?")}" does not set allowPrivilegeEscalation: false',
                "Set `securityContext.allowPrivilegeEscalation: false`.",
            )


@rule(
    "RDY011",
    Severity.WARNING,
    "May run as root",
    "Neither the pod nor the container declares `runAsNonRoot: true` (or a non-zero "
    "`runAsUser`), so the image's default user, often root, is used.",
)
def run_as_non_root(res: Resource, _: Context) -> Iterator[Finding]:
    spec = res.pod_spec()
    if spec is None:
        return
    pod_sc = spec.get("securityContext") or {}
    for role, c in res.containers():
        sc = c.get("securityContext") or {}
        non_root = sc.get("runAsNonRoot", pod_sc.get("runAsNonRoot"))
        user = sc.get("runAsUser", pod_sc.get("runAsUser"))
        if non_root is True or (isinstance(user, int) and user > 0):
            continue
        yield _finding(
            res,
            "RDY011",
            f'{role} "{c.get("name", "?")}" may run as root',
            "Set `securityContext.runAsNonRoot: true` (pod or container level).",
        )


@rule(
    "RDY012",
    Severity.INFO,
    "Writable root filesystem",
    "A read-only root filesystem stops an attacker from modifying the container's "
    "binaries. Mount an emptyDir where the app really needs to write.",
)
def read_only_root(res: Resource, _: Context) -> Iterator[Finding]:
    for role, c in res.containers(include_init=False):
        if (c.get("securityContext") or {}).get("readOnlyRootFilesystem") is not True:
            yield _finding(
                res,
                "RDY012",
                f'{role} "{c.get("name", "?")}" has a writable root filesystem',
                "Set `securityContext.readOnlyRootFilesystem: true`.",
            )


@rule(
    "RDY013",
    Severity.ERROR,
    "hostPath volume",
    "hostPath volumes expose the node's filesystem to the pod and tie the pod to one "
    "node. Use a PersistentVolumeClaim.",
)
def host_path(res: Resource, _: Context) -> Iterator[Finding]:
    spec = res.pod_spec() or {}
    for v in spec.get("volumes") or []:
        if isinstance(v, dict) and "hostPath" in v:
            path = (v.get("hostPath") or {}).get("path", "?")
            yield _finding(
                res,
                "RDY013",
                f'volume "{v.get("name", "?")}" is a hostPath ({path})',
                "Use a PersistentVolumeClaim, or a DaemonSet if it is a node agent.",
            )


@rule(
    "RDY014",
    Severity.WARNING,
    "Secret committed in plain text",
    "A Secret manifest with data is only base64, not encrypted. Anyone with read access "
    "to the repository has the secret.",
)
def secret_in_git(res: Resource, _: Context) -> Iterator[Finding]:
    if res.kind != "Secret":
        return
    if res.raw.get("data") or res.raw.get("stringData"):
        yield _finding(
            res,
            "RDY014",
            "contains secret data",
            "Use Sealed Secrets, External Secrets, SOPS or the cloud provider's secret manager.",
        )


# ----------------------------------------------------------------------- hygiene

REMOVED_APIS: dict[tuple[str, str], str] = {
    ("extensions/v1beta1", "Deployment"): "apps/v1",
    ("extensions/v1beta1", "DaemonSet"): "apps/v1",
    ("extensions/v1beta1", "ReplicaSet"): "apps/v1",
    ("extensions/v1beta1", "Ingress"): "networking.k8s.io/v1",
    ("extensions/v1beta1", "NetworkPolicy"): "networking.k8s.io/v1",
    ("extensions/v1beta1", "PodSecurityPolicy"): "Pod Security Admission",
    ("apps/v1beta1", "*"): "apps/v1",
    ("apps/v1beta2", "*"): "apps/v1",
    ("networking.k8s.io/v1beta1", "Ingress"): "networking.k8s.io/v1",
    ("networking.k8s.io/v1beta1", "IngressClass"): "networking.k8s.io/v1",
    ("policy/v1beta1", "PodDisruptionBudget"): "policy/v1",
    ("policy/v1beta1", "PodSecurityPolicy"): "Pod Security Admission",
    ("autoscaling/v2beta1", "HorizontalPodAutoscaler"): "autoscaling/v2",
    ("autoscaling/v2beta2", "HorizontalPodAutoscaler"): "autoscaling/v2",
    ("batch/v1beta1", "CronJob"): "batch/v1",
    ("rbac.authorization.k8s.io/v1beta1", "*"): "rbac.authorization.k8s.io/v1",
    ("apiextensions.k8s.io/v1beta1", "CustomResourceDefinition"): "apiextensions.k8s.io/v1",
    ("admissionregistration.k8s.io/v1beta1", "*"): "admissionregistration.k8s.io/v1",
    ("storage.k8s.io/v1beta1", "*"): "storage.k8s.io/v1",
    ("flowcontrol.apiserver.k8s.io/v1beta1", "*"): "flowcontrol.apiserver.k8s.io/v1",
    ("flowcontrol.apiserver.k8s.io/v1beta2", "*"): "flowcontrol.apiserver.k8s.io/v1",
}


@rule(
    "RDY015",
    Severity.ERROR,
    "Removed API version",
    "This apiVersion was removed from Kubernetes; the apply will fail on a current cluster.",
)
def removed_api(res: Resource, _: Context) -> Iterator[Finding]:
    key = (res.api_version, res.kind)
    replacement = REMOVED_APIS.get(key) or REMOVED_APIS.get((res.api_version, "*"))
    if replacement:
        yield _finding(
            res,
            "RDY015",
            f"uses removed apiVersion {res.api_version}",
            f"Migrate to `{replacement}`.",
        )


@rule(
    "RDY016",
    Severity.INFO,
    "Missing recommended labels",
    "`app.kubernetes.io/name` is the standard label that dashboards, cost tools and "
    "network policies key on.",
)
def recommended_labels(res: Resource, _: Context) -> Iterator[Finding]:
    if not res.is_workload:
        return
    if "app.kubernetes.io/name" not in res.labels:
        yield _finding(
            res,
            "RDY016",
            "has no app.kubernetes.io/name label",
            "Add `app.kubernetes.io/name` (and ideally /instance, /version, /part-of).",
        )


@rule(
    "RDY017",
    Severity.INFO,
    "No namespace",
    "Resources without `metadata.namespace` land wherever kubectl's context points, "
    "usually `default`. Harmless for Helm charts (the release sets it) and Argo CD; "
    "worth disabling there.",
)
def no_namespace(res: Resource, _: Context) -> Iterator[Finding]:
    cluster_scoped = {
        "Namespace",
        "Node",
        "PersistentVolume",
        "ClusterRole",
        "ClusterRoleBinding",
        "StorageClass",
        "CustomResourceDefinition",
        "PriorityClass",
        "IngressClass",
        "ValidatingWebhookConfiguration",
        "MutatingWebhookConfiguration",
        "RuntimeClass",
        "CSIDriver",
        "CSINode",
    }
    if res.kind in cluster_scoped or res.namespace:
        return
    yield _finding(
        res,
        "RDY017",
        "has no metadata.namespace",
        "Set `metadata.namespace` explicitly, or disable RDY017 for Helm charts.",
    )


@rule(
    "RDY018",
    Severity.WARNING,
    "CronJob without concurrency policy",
    "A CronJob that runs longer than its schedule starts overlapping copies by default.",
)
def cronjob_concurrency(res: Resource, _: Context) -> Iterator[Finding]:
    if res.kind != "CronJob":
        return
    if res.spec.get("concurrencyPolicy") in (None, "Allow"):
        yield _finding(
            res,
            "RDY018",
            "allows overlapping runs (concurrencyPolicy: Allow)",
            "Set `concurrencyPolicy: Forbid` (or `Replace`).",
        )


# ---------------------------------------------------------------------- engine

IGNORE_ANNOTATION = "kube-ready/ignore"


def ignored_rules(res: Resource) -> set[str]:
    value = res.annotations.get(IGNORE_ANNOTATION)
    if value is None:
        return set()
    return {item.strip() for item in str(value).split(",") if item.strip()}


def run(
    resources: list[Resource],
    disabled: set[str] | None = None,
    severities: dict[str, Severity] | None = None,
) -> list[Finding]:
    """Run every enabled rule over every resource."""
    disabled = disabled or set()
    severities = severities or {}
    ctx = Context(resources=resources)
    findings: list[Finding] = []
    for res in resources:
        ignored = ignored_rules(res)
        if "*" in ignored:
            continue
        for rid, r in RULES.items():
            if rid in disabled or rid in ignored:
                continue
            for f in r.fn(res, ctx):
                if rid in severities:
                    f.severity = severities[rid]
                findings.append(f)
    findings.sort(key=lambda f: (f.resource.source, f.resource.line, f.rule_id))
    return findings
