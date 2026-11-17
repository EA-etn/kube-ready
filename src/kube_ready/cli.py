"""Command-line interface.

Exit codes: 0 ready, 1 findings at or above ``--fail-on``, 2 usage or configuration error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console

from kube_ready import __version__, baseline
from kube_ready.config import FAIL_ON_CHOICES, Config, ConfigError, load_config
from kube_ready.loader import load
from kube_ready.model import Finding, Report, Resource, Severity
from kube_ready.report import (
    render_github,
    render_json,
    render_rules,
    render_sarif,
    render_text,
)
from kube_ready.rules import RULES, run

EXIT_OK, EXIT_FINDINGS, EXIT_USAGE = 0, 1, 2


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("paths", nargs="+", metavar="PATH")
    parser.add_argument(
        "-c", "--config", metavar="FILE", help="config file (default: .kube-ready.yaml if present)"
    )
    parser.add_argument(
        "--disable",
        action="append",
        default=[],
        metavar="RULES",
        help="comma-separated rule ids to skip (repeatable)",
    )
    parser.add_argument("--no-color", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kube-ready",
        description="Is this Kubernetes manifest ready for production?",
    )
    parser.add_argument("--version", action="version", version=f"kube-ready {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="check manifests (files, directories or - for stdin)")
    _add_common(check)
    check.add_argument(
        "-f",
        "--format",
        choices=("text", "json", "sarif", "github"),
        default="text",
        help="github prints GitHub Actions annotations (inline on the PR diff)",
    )
    check.add_argument("-o", "--output", metavar="FILE", help="write the report to FILE")
    check.add_argument(
        "--fail-on",
        choices=FAIL_ON_CHOICES,
        help="lowest severity that makes the exit code 1 (default: error)",
    )
    check.add_argument(
        "--baseline",
        metavar="FILE",
        help="hide the findings recorded in FILE (see `kube-ready baseline`)",
    )
    check.add_argument("-v", "--verbose", action="store_true", help="show how to fix findings")

    base = sub.add_parser(
        "baseline",
        help="record today's findings so that `check --baseline` only reports new ones",
    )
    _add_common(base)
    base.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        default=baseline.DEFAULT_FILE,
        help=f"where to write the baseline (default: {baseline.DEFAULT_FILE})",
    )

    sub.add_parser("rules", help="list every rule with its severity and rationale")
    return parser


def _collect(
    args: argparse.Namespace, err: Console
) -> tuple[Config, list[Resource], list[Finding], list[str]] | int:
    """Load config and manifests and run the rules. Returns an exit code on error."""
    try:
        cfg = load_config(args.config, set(RULES))
    except ConfigError as exc:
        err.print(f"[red]error:[/] {exc}")
        return EXIT_USAGE

    disabled = set(cfg.disable)
    for item in args.disable:
        for rid in item.split(","):
            rid = rid.strip()
            if rid and rid not in RULES:
                err.print(f"[red]error:[/] unknown rule id '{rid}' in --disable")
                return EXIT_USAGE
            if rid:
                disabled.add(rid)

    try:
        resources, load_errors, files = load(args.paths)
    except FileNotFoundError as exc:
        err.print(f"[red]error:[/] no such file or directory: {exc}")
        return EXIT_USAGE
    if not files:
        err.print("[red]error:[/] no YAML files found")
        return EXIT_USAGE

    findings = load_errors + run(resources, disabled=disabled, severities=cfg.severity)
    findings.sort(key=lambda f: (f.resource.source, f.resource.line, f.rule_id))
    return cfg, resources, findings, files


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    console = Console(no_color=getattr(args, "no_color", False), highlight=False, soft_wrap=True)
    err = Console(stderr=True, highlight=False)

    if args.command == "rules":
        render_rules(console)
        return EXIT_OK

    collected = _collect(args, err)
    if isinstance(collected, int):
        return collected
    cfg, resources, findings, files = collected

    if args.command == "baseline":
        n = baseline.write(findings, args.output)
        console.print(
            f"[bold]{n}[/] finding{'s' if n != 1 else ''} recorded in [cyan]{args.output}[/]. "
            f"Commit it and run `kube-ready check ... --baseline {args.output}`."
        )
        return EXIT_OK

    report = Report(findings=findings, resources=resources, files=files)
    baseline_file = args.baseline or cfg.baseline
    if baseline_file:
        try:
            known = baseline.read(baseline_file)
        except baseline.BaselineError as exc:
            err.print(f"[red]error:[/] {exc}")
            return EXIT_USAGE
        report.findings, report.suppressed = baseline.apply(findings, known)
        report.baseline_file = baseline_file

    fail_on = args.fail_on or cfg.fail_on
    if args.format == "text":
        if args.output:
            with Path(args.output).open("w", encoding="utf-8") as fh:
                file_console = Console(file=fh, no_color=True, highlight=False, width=120)
                render_text(report, file_console, verbose=args.verbose)
        else:
            render_text(report, console, verbose=args.verbose)
    else:
        renderers = {"json": render_json, "sarif": render_sarif, "github": render_github}
        text = renderers[args.format](report)
        if args.output:
            Path(args.output).write_text(text + "\n", encoding="utf-8")
        else:
            sys.stdout.write(text + "\n")

    if fail_on == "never":
        return EXIT_OK
    threshold = Severity(fail_on).rank
    worst = report.worst()
    return EXIT_FINDINGS if worst is not None and worst.rank >= threshold else EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
