# Changelog

## 0.1.0

First release.

- 22 rules: images, resources, probes, availability (replicas, PDB, spread), security
  (privileged, host namespaces, escalation, root, read-only FS, hostPath, capabilities,
  seccomp), Secrets in Git, removed API versions, labels, namespaces, CronJob concurrency,
  Ingress without TLS, Service selecting no pods.
- `kube-ready baseline` and `check --baseline` to adopt gradually in big repositories.
- Input from files, directories, multi-document YAML, `kind: List` and stdin.
- Output as text, JSON, SARIF 2.1.0 and GitHub Actions annotations.
- Config file, `--disable`, per-resource `kube-ready/ignore` annotation, `--fail-on`.
- GitHub Action, pre-commit hook and multi-arch Docker image.
- `kube_ready.api.check_text()` for scripts and the browser playground (GitHub Pages, Pyodide).
- Diagrams (how it works, scenarios) and an animated terminal demo, in EN and ES.
