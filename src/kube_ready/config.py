"""Configuration: ``.kube-ready.yaml`` in the working directory or ``--config``."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from kube_ready.model import Severity

DEFAULT_FILE = ".kube-ready.yaml"
FAIL_ON_CHOICES = ("error", "warning", "info", "never")


class ConfigError(Exception):
    pass


@dataclass
class Config:
    disable: set[str] = field(default_factory=set)
    severity: dict[str, Severity] = field(default_factory=dict)
    fail_on: str = "error"


def load_config(path: str | None, known_rules: set[str]) -> Config:
    file = Path(path) if path else Path(DEFAULT_FILE)
    if not file.exists():
        if path:
            raise ConfigError(f"config file not found: {path}")
        return Config()
    try:
        data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{file}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{file}: expected a mapping at the top level")

    cfg = Config()
    disable = data.get("disable") or []
    if not isinstance(disable, list):
        raise ConfigError(f"{file}: 'disable' must be a list of rule ids")
    for rid in disable:
        _check_rule(str(rid), known_rules, file)
        cfg.disable.add(str(rid))

    severity = data.get("severity") or {}
    if not isinstance(severity, dict):
        raise ConfigError(f"{file}: 'severity' must be a mapping of rule id to level")
    for rid, level in severity.items():
        _check_rule(str(rid), known_rules, file)
        try:
            cfg.severity[str(rid)] = Severity(str(level))
        except ValueError as exc:
            raise ConfigError(f"{file}: unknown severity '{level}' for {rid}") from exc

    fail_on = data.get("fail-on", data.get("fail_on"))
    if fail_on is not None:
        if str(fail_on) not in FAIL_ON_CHOICES:
            raise ConfigError(f"{file}: 'fail-on' must be one of {', '.join(FAIL_ON_CHOICES)}")
        cfg.fail_on = str(fail_on)
    return cfg


def _check_rule(rid: str, known: set[str], file: Path) -> None:
    if rid not in known:
        raise ConfigError(f"{file}: unknown rule id '{rid}'")
