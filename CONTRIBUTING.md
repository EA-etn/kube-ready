# Contributing

Thanks for taking a look. Small, focused pull requests are easiest to review.

## Set up

```bash
git clone https://github.com/EA-etn/kube-ready && cd kube-ready
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
make lint test
```

## Add a rule

1. Pick the next free id (`kube-ready rules` shows them) and a severity:
   - **error**: will break or is a security hole (`latest`, privileged, removed API)
   - **warning**: will hurt on a bad day (no probes, one replica, no limits)
   - **info**: best practice that most teams phase in (labels, read-only root FS)
2. Write one function in `src/kube_ready/rules.py` decorated with `@rule(...)`. The
   description must say *why*; that text ends up in `kube-ready rules` and in SARIF.
3. Add the bad case and the good case to `tests/test_rules.py`. `_deployment()` builds a
   clean fixture you can break on purpose.
4. Keep `examples/good` passing at `--fail-on info` and add the bad case to `examples/bad`
   if it is a common mistake.
5. Add a row to the rules table in `README.md` and `README.es.md`, and a line to
   `CHANGELOG.md`.

Rules must not need a cluster, the network, or more than the manifests of the run.
A rule that cannot be sure should stay quiet: a false positive costs more trust than a
missed finding.

## Conventions

- Python 3.10+, `ruff` for lint and format, `mypy --strict` on `src/`.
- Commit messages: `feat:`, `fix:`, `docs:`, `ci:`, `test:`. One topic per commit.
- Every change goes through a pull request and the CI must be green.
