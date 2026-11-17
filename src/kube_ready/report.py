"""Output formats: human-readable text, JSON and SARIF 2.1.0 (GitHub code scanning)."""

from __future__ import annotations

import json
from itertools import groupby
from typing import Any

from rich.console import Console

from kube_ready import __version__
from kube_ready.model import Report, Severity
from kube_ready.rules import RULES

ICON = {
    Severity.ERROR: "[bold red]✖[/]",
    Severity.WARNING: "[bold yellow]▲[/]",
    Severity.INFO: "[bold blue]ℹ[/]",
}
COLOR = {Severity.ERROR: "red", Severity.WARNING: "yellow", Severity.INFO: "blue"}


def _baseline_note(report: Report) -> str:
    if not report.baseline_file:
        return ""
    return (
        f" [dim]({report.suppressed} known finding{'s' if report.suppressed != 1 else ''} "
        f"hidden by baseline {report.baseline_file})[/]"
    )


def render_text(report: Report, console: Console, verbose: bool = False) -> None:
    if not report.findings:
        console.print(
            f"[bold green]✔ Ready.[/] {len(report.resources)} resources in "
            f"{len(report.files)} files, no{' new' if report.baseline_file else ''} findings."
            + _baseline_note(report)
        )
        return
    for source, group in groupby(report.findings, key=lambda f: f.resource.source):
        console.print(f"\n[bold]{source}[/]")
        for f in group:
            res = f.resource
            console.print(
                f"  {ICON[f.severity]} [{COLOR[f.severity]}]{f.rule_id}[/]  "
                f"[cyan]{res.ref}[/] [dim](line {res.line})[/]  "
                f"{f.message}"
            )
            if verbose and f.hint:
                console.print(f"       [dim]↳ {f.hint}[/]")
    e, w, i = (report.count(s) for s in (Severity.ERROR, Severity.WARNING, Severity.INFO))
    console.print(
        f"\n[bold]{e} error{'s' if e != 1 else ''}[/], "
        f"[bold]{w} warning{'s' if w != 1 else ''}[/], "
        f"[bold]{i} info[/] "
        f"across {len(report.resources)} resources in {len(report.files)} files."
        + _baseline_note(report)
    )
    if not verbose:
        console.print(
            "[dim]Run with --verbose to see how to fix each finding, "
            "or `kube-ready rules` for the full list.[/]"
        )


def render_json(report: Report) -> str:
    return json.dumps(
        {
            "version": __version__,
            "summary": {
                "files": len(report.files),
                "resources": len(report.resources),
                "errors": report.count(Severity.ERROR),
                "warnings": report.count(Severity.WARNING),
                "info": report.count(Severity.INFO),
                "baselined": report.suppressed,
            },
            "findings": [f.to_dict() for f in report.findings],
        },
        indent=2,
    )


def render_sarif(report: Report) -> str:
    used = sorted({f.rule_id for f in report.findings})
    rules: list[dict[str, Any]] = []
    index = {}
    for n, rid in enumerate(used):
        index[rid] = n
        if rid == "RDY000":
            rules.append(
                {
                    "id": rid,
                    "shortDescription": {"text": "Invalid YAML"},
                    "defaultConfiguration": {"level": "error"},
                }
            )
            continue
        r = RULES[rid]
        rules.append(
            {
                "id": rid,
                "name": r.title.replace(" ", ""),
                "shortDescription": {"text": r.title},
                "fullDescription": {"text": r.description},
                "help": {"text": r.description},
                "defaultConfiguration": {"level": r.severity.sarif_level},
            }
        )
    results = []
    for f in report.findings:
        results.append(
            {
                "ruleId": f.rule_id,
                "ruleIndex": index[f.rule_id],
                "level": f.severity.sarif_level,
                "message": {"text": f"{f.resource.ref}: {f.message}. {f.hint}".strip()},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": f.resource.source,
                                "uriBaseId": "%SRCROOT%",
                            },
                            "region": {"startLine": max(f.resource.line, 1)},
                        }
                    }
                ],
            }
        )
    doc = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "kube-ready",
                        "version": __version__,
                        "informationUri": "https://github.com/EA-etn/kube-ready",
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(doc, indent=2)


GITHUB_LEVEL = {Severity.ERROR: "error", Severity.WARNING: "warning", Severity.INFO: "notice"}


def _gh_escape(value: str, prop: bool = False) -> str:
    """Escape for GitHub Actions workflow commands (data vs. property values)."""
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if prop:
        value = value.replace(":", "%3A").replace(",", "%2C")
    return value


def render_github(report: Report) -> str:
    """One ``::level file=...,line=...,title=...::message`` per finding.

    GitHub Actions turns these into annotations on the check and inline on the PR diff.
    """
    lines = []
    for f in report.findings:
        title = f.rule_id if f.rule_id == "RDY000" else f"{f.rule_id} {RULES[f.rule_id].title}"
        props = (
            f"file={_gh_escape(f.resource.source, prop=True)},"
            f"line={max(f.resource.line, 1)},"
            f"title={_gh_escape(title, prop=True)}"
        )
        message = f"{f.resource.ref}: {f.message}. {f.hint}".strip()
        lines.append(f"::{GITHUB_LEVEL[f.severity]} {props}::{_gh_escape(message)}")
    e, w, i = (report.count(s) for s in (Severity.ERROR, Severity.WARNING, Severity.INFO))
    lines.append(
        f"kube-ready: {e} errors, {w} warnings, {i} info across {len(report.resources)} "
        f"resources in {len(report.files)} files"
        + (f" ({report.suppressed} hidden by baseline)" if report.baseline_file else "")
    )
    return "\n".join(lines)


def render_rules(console: Console) -> None:
    from rich.table import Table

    table = Table(title=f"kube-ready {__version__} rules", show_lines=False)
    table.add_column("Rule", style="bold")
    table.add_column("Severity")
    table.add_column("Title")
    table.add_column("Why", max_width=80)
    for r in RULES.values():
        table.add_row(r.id, f"[{COLOR[r.severity]}]{r.severity.value}[/]", r.title, r.description)
    console.print(table)
