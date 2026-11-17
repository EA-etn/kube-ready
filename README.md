<div align="center">

# kube-ready

**Is this Kubernetes manifest ready for production?**

[![CI](https://github.com/EA-etn/kube-ready/actions/workflows/ci.yml/badge.svg)](https://github.com/EA-etn/kube-ready/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%20–%203.13-3776AB?logo=python&logoColor=white)
![SARIF](https://img.shields.io/badge/output-SARIF%202.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**English** · [Español](README.es.md)

</div>

A small, fast, opinionated linter for Kubernetes manifests. It reads plain YAML, Kustomize or
`helm template` output and tells you what will hurt on a bad day: `latest` images, no resource
limits, no probes, one replica, containers running as root, Secrets committed to Git, API
versions that no longer exist.

No cluster needed. Runs in a second. Fails your CI with a clear message and a hint to fix it.

```
$ kube-ready check examples/bad --verbose

examples/bad/deployment.yaml
  ✖ RDY001  Deployment/api (line 2)  container "api" uses image "myregistry/api:latest" with tag latest
       ↳ Pin a version (`app:1.4.2`) or a digest (`app@sha256:…`).
  ▲ RDY002  Deployment/api (line 2)  container "api" has no cpu or memory request
       ↳ Set `resources.requests.cpu` and `resources.requests.memory`.
  ▲ RDY006  Deployment/api (line 2)  runs 1 replica
       ↳ Set `spec.replicas: 2` or more, or add an HPA with `minReplicas: 2`.
  ✖ RDY009  Deployment/api (line 2)  container "api" is privileged
       ↳ Drop `privileged: true`; add specific capabilities instead.
  ✖ RDY013  Deployment/api (line 2)  volume "data" is a hostPath (/var/lib/api)
       ↳ Use a PersistentVolumeClaim, or a DaemonSet if it is a node agent.
  ▲ RDY014  Secret/api-credentials (line 29)  contains secret data
       ↳ Use Sealed Secrets, External Secrets, SOPS or the cloud provider's secret manager.
  ✖ RDY015  CronJob/nightly-report (line 37)  uses removed apiVersion batch/v1beta1
       ↳ Migrate to `batch/v1`.
  …

6 errors, 15 warnings, 13 info across 5 resources in 1 files.
```

## Why another linter?

[kube-score](https://github.com/zegl/kube-score), [kube-linter](https://github.com/stackrox/kube-linter)
and [Polaris](https://github.com/FairwindsOps/polaris) are great and more complete. kube-ready is
the one you read in an afternoon: about a thousand lines of Python, one function per rule, a test per rule,
and every rule explains *why* it exists. It is meant to be adopted in five minutes and extended
in ten.

## Install

```bash
pipx install kube-ready            # or: pip install kube-ready
kube-ready --version
```

Or without installing anything:

```bash
docker run --rm -v "$PWD:/work:ro" ghcr.io/ea-etn/kube-ready check manifests/
```

## Use

```bash
kube-ready check manifests/                          # files or directories, recursive
kube-ready check deploy.yaml svc.yaml                # several files
helm template my-chart | kube-ready check -          # stdin
kustomize build overlays/prod | kube-ready check -

kube-ready check manifests/ --verbose                # show how to fix each finding
kube-ready check manifests/ --fail-on warning        # stricter CI
kube-ready check manifests/ --format json            # for scripts
kube-ready check manifests/ --format sarif -o report.sarif   # for GitHub code scanning
kube-ready rules                                     # the full list, with rationale
```

Exit codes: `0` ready, `1` findings at or above `--fail-on` (default `error`), `2` usage or
config error.

## Rules

| Rule | Severity | Checks that… |
|---|---|---|
| RDY001 | error | images have an immutable tag or digest, not `latest` or no tag |
| RDY002 | warning | every container has CPU and memory **requests** |
| RDY003 | warning | every container has a memory **limit** (CPU limits are deliberately not required) |
| RDY004 | warning | containers have a `livenessProbe` (not Jobs/CronJobs) |
| RDY005 | warning | containers have a `readinessProbe` (not Jobs/CronJobs) |
| RDY006 | warning | Deployments/StatefulSets run ≥ 2 replicas, or an HPA with `minReplicas ≥ 2` targets them |
| RDY007 | info | workloads with several replicas have a matching PodDisruptionBudget |
| RDY008 | info | workloads with several replicas spread across nodes (topologySpreadConstraints or podAntiAffinity) |
| RDY009 | error | no `privileged` containers, no `hostNetwork` / `hostPID` / `hostIPC` |
| RDY010 | warning | `allowPrivilegeEscalation: false` is set |
| RDY011 | warning | `runAsNonRoot: true` or a non-zero `runAsUser` (pod or container level) |
| RDY012 | info | `readOnlyRootFilesystem: true` |
| RDY013 | error | no `hostPath` volumes |
| RDY014 | warning | no `Secret` with `data` / `stringData` committed to Git |
| RDY015 | error | no removed API versions (`extensions/v1beta1`, `batch/v1beta1`, …) |
| RDY016 | info | workloads carry the `app.kubernetes.io/name` label |
| RDY017 | info | namespaced resources set `metadata.namespace` (disable for Helm charts) |
| RDY018 | warning | CronJobs set `concurrencyPolicy` to `Forbid` or `Replace` |
| RDY019 | warning | Ingresses have a `tls` section |
| RDY020 | warning | Services select at least one pod template of the same namespace in the run |
| RDY021 | info | containers drop all Linux capabilities (`capabilities.drop: [ALL]`) |
| RDY022 | info | a seccomp profile is set (`RuntimeDefault`), pod or container level |

Cross-resource rules (RDY006, RDY007, RDY020) look at every manifest you pass in the same run, so
check a whole directory rather than one file at a time to avoid false positives.

## Configure

`.kube-ready.yaml` in the working directory, or `--config FILE`:

```yaml
disable:
  - RDY017        # Helm / Argo CD set the namespace at release time
severity:
  RDY014: error   # a Secret in Git is never acceptable here
fail-on: warning
```

Skip rules for one resource with an annotation (`"*"` skips all of them):

```yaml
metadata:
  annotations:
    kube-ready/ignore: "RDY006, RDY007"   # single replica is fine for this dev tool
```

## Adopt it in a big repository

Hundreds of findings on day one? Record them and only fail on new ones:

```bash
kube-ready baseline manifests/            # writes .kube-ready-baseline.json
git add .kube-ready-baseline.json
kube-ready check manifests/ --baseline .kube-ready-baseline.json --fail-on warning
```

A baseline entry is the rule, the resource and the message, not the file and line, so moving a
manifest does not resurrect it. Fix things over time and regenerate the baseline when you want
to shrink it. `baseline: .kube-ready-baseline.json` in `.kube-ready.yaml` makes it the default.

## In CI

### GitHub Actions

```yaml
- uses: EA-etn/kube-ready@v0.1.0
  with:
    path: manifests/
    fail-on: warning
    sarif-file: kube-ready.sarif    # optional

- uses: github/codeql-action/upload-sarif@v3    # findings appear in the Security tab
  if: always()
  with:
    sarif_file: kube-ready.sarif
```

### pre-commit

```yaml
repos:
  - repo: https://github.com/EA-etn/kube-ready
    rev: v0.1.0
    hooks:
      - id: kube-ready
        files: ^manifests/.*\.ya?ml$
```

### Anything else

```bash
helm template . | docker run --rm -i ghcr.io/ea-etn/kube-ready check - --fail-on warning
```

## Opinions baked in

- **No CPU limits required.** CPU limits throttle; memory limits protect the node. Requests are
  what the scheduler needs. If your platform mandates CPU limits, add a rule (see below).
- **Two replicas is the floor.** A single replica means downtime on every rollout. Jobs and
  DaemonSets are exempt.
- **Warnings do not fail the build by default.** Adopt the tool on day one with `--fail-on error`,
  then tighten to `warning` when the backlog is gone.

## Add a rule

One function in [`src/kube_ready/rules.py`](src/kube_ready/rules.py):

```python
@rule("RDY019", Severity.WARNING, "Image pull policy Always",
      "Pulling on every start slows restarts and depends on the registry being up.")
def pull_policy(res: Resource, ctx: Context) -> Iterator[Finding]:
    for role, c in res.containers():
        if c.get("imagePullPolicy") == "Always":
            yield _finding(res, "RDY019", f'{role} "{c["name"]}" pulls on every start',
                           "Use IfNotPresent with an immutable tag.")
```

Plus a test in `tests/test_rules.py`. `ctx.resources` holds every manifest of the run, for
rules that need to look at related objects.

## Development

```bash
pip install -e ".[dev]"
make lint test check
```

## Roadmap

- [x] 22 rules, SARIF output, GitHub Action, pre-commit hook, multi-arch image
- [x] `Service` without matching pods, `Ingress` without TLS, capabilities, seccomp
- [x] Baseline file to adopt gradually in big repositories (`--baseline`)
- [ ] Publish to PyPI (trusted publishing)
- [ ] Gateway API (`HTTPRoute`) and `NetworkPolicy` coverage

## License

[MIT](LICENSE)
