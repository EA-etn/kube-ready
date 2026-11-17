# Changelog

## 0.1.0

First release.

- 18 rules: images, resources, probes, availability (replicas, PDB, spread), security
  (privileged, host namespaces, escalation, root, read-only FS, hostPath), Secrets in Git,
  removed API versions, labels, namespaces, CronJob concurrency.
- Input from files, directories, multi-document YAML, `kind: List` and stdin.
- Output as text, JSON and SARIF 2.1.0.
- Config file, `--disable`, per-resource `kube-ready/ignore` annotation, `--fail-on`.
- GitHub Action, pre-commit hook and multi-arch Docker image.
