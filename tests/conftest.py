from __future__ import annotations

import pytest

from kube_ready.loader import parse_documents
from kube_ready.rules import run


@pytest.fixture
def check():
    """Run the rules over an inline YAML string and return the finding ids."""

    def _check(text: str, **kwargs) -> list[str]:
        resources = parse_documents(text, "inline.yaml")
        return [f.rule_id for f in run(resources, **kwargs)]

    return _check


GOOD_DEPLOYMENT = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: shop
  labels: {app.kubernetes.io/name: web}
spec:
  replicas: 2
  selector: {matchLabels: {app: web}}
  template:
    metadata:
      labels: {app: web}
    spec:
      securityContext: {runAsNonRoot: true, seccompProfile: {type: RuntimeDefault}}
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: DoNotSchedule
          labelSelector: {matchLabels: {app: web}}
      containers:
        - name: web
          image: ghcr.io/example/web:1.2.3
          resources:
            requests: {cpu: 100m, memory: 128Mi}
            limits: {memory: 256Mi}
          livenessProbe: {httpGet: {path: /healthz, port: 8080}}
          readinessProbe: {httpGet: {path: /ready, port: 8080}}
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: {drop: [ALL]}
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: {name: web, namespace: shop}
spec:
  minAvailable: 1
  selector: {matchLabels: {app: web}}
"""


@pytest.fixture
def good_deployment() -> str:
    return GOOD_DEPLOYMENT


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    """Tests must not pick up the repo's own .kube-ready.yaml."""
    monkeypatch.chdir(tmp_path)
