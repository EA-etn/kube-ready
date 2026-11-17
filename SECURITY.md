# Security

kube-ready only reads local files or stdin. It makes no network calls and does not talk
to any cluster. YAML is parsed with `yaml.safe_load` only.

If you believe you have found a security issue, open a
[private vulnerability report](https://github.com/EA-etn/kube-ready/security/advisories/new)
rather than a public issue. You should get an answer within a week.

Supported: the latest release. Images are signed with cosign; see the README for how to
verify them before running.
