"""One test (at least) per rule: the bad case fires, the good case does not."""

from __future__ import annotations

import pytest


def test_good_deployment_is_clean(check, good_deployment):
    assert check(good_deployment) == []


def _deployment(
    container: str = "",
    pod: str = "",
    spec: str = "replicas: 2",
    kind: str = "Deployment",
    meta: str = "",
) -> str:
    """Build a Deployment-like manifest that passes everything except what you inject."""
    return f"""
apiVersion: apps/v1
kind: {kind}
metadata:
  name: app
  namespace: ns
  labels: {{app.kubernetes.io/name: app}}
  {meta}
spec:
  {spec}
  selector: {{matchLabels: {{app: app}}}}
  template:
    metadata:
      labels: {{app: app}}
    spec:
      securityContext: {{runAsNonRoot: true}}
      topologySpreadConstraints:
        - {{maxSkew: 1, topologyKey: kubernetes.io/hostname, whenUnsatisfiable: DoNotSchedule,
           labelSelector: {{matchLabels: {{app: app}}}}}}
      {pod}
      containers:
        - name: app
          image: example/app:1.0.0
          resources: {{requests: {{cpu: 10m, memory: 16Mi}}, limits: {{memory: 32Mi}}}}
          livenessProbe: {{httpGet: {{path: /, port: 80}}}}
          readinessProbe: {{httpGet: {{path: /, port: 80}}}}
          securityContext: {{allowPrivilegeEscalation: false, readOnlyRootFilesystem: true}}
          {container}
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: {{name: app, namespace: ns}}
spec:
  minAvailable: 1
  selector: {{matchLabels: {{app: app}}}}
"""


def test_baseline_fixture_is_clean(check):
    assert check(_deployment()) == []


# RDY001 image tag
@pytest.mark.parametrize(
    "image,expected",
    [
        ("nginx", True),
        ("nginx:latest", True),
        ("registry.example.com:5000/team/nginx", True),  # port is not a tag
        ("nginx:1.27", False),
        ("registry.example.com:5000/team/nginx:1.27", False),
        ("nginx@sha256:" + "a" * 64, False),
    ],
)
def test_image_tag(check, image, expected):
    found = "RDY001" in check(_deployment(container=f"image: {image}"))
    assert found is expected


def test_image_tag_checks_init_containers(check):
    pod = (
        "initContainers: [{name: init, image: busybox, securityContext: "
        "{allowPrivilegeEscalation: false}, resources: {requests: {cpu: 1m, memory: 1Mi}, "
        "limits: {memory: 1Mi}}}]"
    )
    assert "RDY001" in check(_deployment(pod=pod))


# RDY002 / RDY003 resources
def test_missing_requests(check):
    ids = check(_deployment(container="resources: {limits: {memory: 32Mi}}"))
    assert ids.count("RDY002") == 1
    assert "RDY003" not in ids


def test_missing_memory_limit_only(check):
    ids = check(_deployment(container="resources: {requests: {cpu: 1m, memory: 1Mi}}"))
    assert "RDY003" in ids and "RDY002" not in ids


def test_cpu_limit_not_required(check):
    assert check(_deployment()) == []  # baseline has no CPU limit on purpose


# RDY004 / RDY005 probes
def test_missing_probes(check):
    text = _deployment()
    for probe in ("livenessProbe", "readinessProbe"):
        text = text.replace(f"{probe}: {{httpGet: {{path: /, port: 80}}}}", "")
    ids = check(text)
    assert "RDY004" in ids and "RDY005" in ids


def test_probes_not_required_for_jobs(check):
    job = """
apiVersion: batch/v1
kind: Job
metadata: {name: once, namespace: ns, labels: {app.kubernetes.io/name: once}}
spec:
  template:
    spec:
      restartPolicy: Never
      securityContext: {runAsNonRoot: true}
      containers:
        - name: once
          image: example/once:1.0.0
          resources: {requests: {cpu: 1m, memory: 1Mi}, limits: {memory: 1Mi}}
          securityContext: {allowPrivilegeEscalation: false, readOnlyRootFilesystem: true}
"""
    assert check(job) == []


# RDY006 / RDY007 / RDY008 availability
def test_single_replica(check):
    ids = check(_deployment(spec="replicas: 1"))
    assert "RDY006" in ids
    assert "RDY007" not in ids and "RDY008" not in ids  # only relevant with >1 replica


def test_replicas_default_to_one(check):
    assert "RDY006" in check(_deployment(spec=""))


def test_hpa_satisfies_replicas(check):
    hpa = """
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: {name: app, namespace: ns}
spec:
  minReplicas: 2
  maxReplicas: 5
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: app}
"""
    assert "RDY006" not in check(_deployment(spec="replicas: 1") + hpa)


def test_hpa_in_other_namespace_does_not_count(check):
    hpa = """
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: {name: app, namespace: other}
spec:
  minReplicas: 2
  maxReplicas: 5
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: app}
"""
    assert "RDY006" in check(_deployment(spec="replicas: 1") + hpa)


def test_missing_pdb(check):
    text = _deployment().split("\n---\n")[0]
    assert "RDY007" in check(text)


def test_pdb_selector_must_match(check):
    text = _deployment().replace(
        "minAvailable: 1\n  selector: {matchLabels: {app: app}}",
        "minAvailable: 1\n  selector: {matchLabels: {app: other}}",
    )
    assert "RDY007" in check(text)


SPREAD = (
    "topologySpreadConstraints:\n"
    "        - {maxSkew: 1, topologyKey: kubernetes.io/hostname, "
    "whenUnsatisfiable: DoNotSchedule,\n"
    "           labelSelector: {matchLabels: {app: app}}}"
)


def test_missing_spread(check):
    text = _deployment()
    assert SPREAD in text
    assert "RDY008" in check(text.replace(SPREAD, ""))


def test_anti_affinity_counts_as_spread(check):
    pod = (
        "affinity: {podAntiAffinity: {requiredDuringSchedulingIgnoredDuringExecution: "
        "[{topologyKey: kubernetes.io/hostname, labelSelector: {matchLabels: {app: app}}}]}}"
    )
    assert "RDY008" not in check(_deployment(pod=pod).replace(SPREAD, ""))


# RDY009-RDY013 security
@pytest.mark.parametrize("pod", ["hostNetwork: true", "hostPID: true", "hostIPC: true"])
def test_host_namespaces(check, pod):
    assert "RDY009" in check(_deployment(pod=pod))


def test_privileged(check):
    sc = (
        "securityContext: {privileged: true, allowPrivilegeEscalation: false, "
        "readOnlyRootFilesystem: true}"
    )
    assert "RDY009" in check(_deployment(container=sc))


def test_privilege_escalation_default_is_flagged(check):
    assert "RDY010" in check(
        _deployment(container="securityContext: {readOnlyRootFilesystem: true}")
    )


def test_run_as_non_root_pod_level(check):
    text = _deployment().replace("securityContext: {runAsNonRoot: true}", "")
    assert "RDY011" in check(text)


def test_run_as_user_counts(check):
    text = _deployment().replace(
        "securityContext: {runAsNonRoot: true}", "securityContext: {runAsUser: 1000}"
    )
    assert "RDY011" not in check(text)


def test_run_as_user_zero_is_root(check):
    text = _deployment().replace(
        "securityContext: {runAsNonRoot: true}", "securityContext: {runAsUser: 0}"
    )
    assert "RDY011" in check(text)


def test_read_only_root(check):
    sc = "securityContext: {allowPrivilegeEscalation: false}"
    assert "RDY012" in check(_deployment(container=sc))


def test_host_path(check):
    assert "RDY013" in check(_deployment(pod="volumes: [{name: d, hostPath: {path: /data}}]"))


def test_secret_with_data(check):
    assert check(
        "apiVersion: v1\nkind: Secret\nmetadata: {name: s, namespace: ns}\ndata: {k: dg==}\n"
    ) == ["RDY014"]


def test_empty_secret_is_fine(check):
    assert check("apiVersion: v1\nkind: Secret\nmetadata: {name: s, namespace: ns}\n") == []


# RDY015-RDY018 hygiene
def test_removed_api(check):
    text = _deployment().replace(
        "apiVersion: apps/v1\nkind: Deployment", "apiVersion: extensions/v1beta1\nkind: Deployment"
    )
    assert "RDY015" in check(text)


def test_removed_api_wildcard(check):
    text = (
        "apiVersion: rbac.authorization.k8s.io/v1beta1\nkind: Role\n"
        "metadata: {name: r, namespace: ns}\n"
    )
    assert check(text) == ["RDY015"]


def test_recommended_labels(check):
    text = _deployment().replace("labels: {app.kubernetes.io/name: app}", "")
    assert "RDY016" in check(text)


def test_no_namespace(check):
    text = _deployment().replace("namespace: ns", "")
    assert "RDY017" in check(text)


def test_cluster_scoped_needs_no_namespace(check):
    assert check("apiVersion: v1\nkind: Namespace\nmetadata: {name: ns}\n") == []


def test_cronjob_concurrency(check):
    cron = """
apiVersion: batch/v1
kind: CronJob
metadata: {name: c, namespace: ns, labels: {app.kubernetes.io/name: c}}
spec:
  schedule: "* * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          securityContext: {runAsNonRoot: true}
          containers:
            - name: c
              image: example/c:1.0.0
              resources: {requests: {cpu: 1m, memory: 1Mi}, limits: {memory: 1Mi}}
              securityContext: {allowPrivilegeEscalation: false, readOnlyRootFilesystem: true}
"""
    assert check(cron) == ["RDY018"]
    assert (
        check(
            cron.replace(
                'schedule: "* * * * *"', 'schedule: "* * * * *"\n  concurrencyPolicy: Forbid'
            )
        )
        == []
    )


# Engine: ignores, disable, severity override
def test_ignore_annotation(check):
    text = _deployment(spec="replicas: 1", meta='annotations: {kube-ready/ignore: "RDY006"}')
    assert "RDY006" not in check(text)


def test_ignore_all_annotation(check):
    text = _deployment(spec="replicas: 1", meta='annotations: {kube-ready/ignore: "*"}')
    assert check(text) == []


def test_disable(check):
    assert "RDY006" not in check(_deployment(spec="replicas: 1"), disabled={"RDY006"})


def test_severity_override(check):
    from kube_ready.loader import parse_documents
    from kube_ready.model import Severity
    from kube_ready.rules import run

    resources = parse_documents(_deployment(spec="replicas: 1"), "x.yaml")
    findings = run(resources, severities={"RDY006": Severity.ERROR})
    assert [f.severity for f in findings if f.rule_id == "RDY006"] == [Severity.ERROR]


def test_list_kind_is_expanded(check):
    text = """
apiVersion: v1
kind: List
items:
  - apiVersion: v1
    kind: Secret
    metadata: {name: s, namespace: ns}
    stringData: {k: v}
"""
    assert check(text) == ["RDY014"]


def test_non_kubernetes_documents_are_skipped(check):
    assert check("just: yaml\n---\n- a\n- b\n---\n") == []
