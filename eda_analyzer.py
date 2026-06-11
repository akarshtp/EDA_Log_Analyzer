#!/usr/bin/env python3
"""
EDA Log Analyzer v2 - Universal, LLM-Powered

Analyzes timing reports from ANY EDA tool (PrimeTime, Tempus, Design
Compiler, ICC2, OpenSTA) using structured LLM extraction. Zero regex.

Usage:
    python eda_analyzer.py analyze <log_file> [--json] [-v]
    python eda_analyzer.py classify <log_file>
"""

from __future__ import annotations

import argparse
import json
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from core.extractor import parse_log, classify_log
from core.diagnostics import diagnose
from models.schemas import TimingReport, LogClassification

console = Console(highlight=False)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def display_classification(classification: LogClassification) -> None:
    """Show the log classification result in a styled panel."""
    confidence_pct = f"{classification.confidence * 100:.0f}%"

    if classification.confidence >= 0.8:
        conf_style = "bold green"
    elif classification.confidence >= 0.5:
        conf_style = "bold yellow"
    else:
        conf_style = "bold red"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="dim")
    table.add_column("Value", style="bold")
    table.add_row("Tool", classification.tool_name)
    table.add_row("Vendor", classification.tool_vendor)
    table.add_row("Report Type", classification.report_type)
    table.add_row("Confidence", Text(confidence_pct, style=conf_style))

    console.print(Panel(
        table,
        title="[bold cyan]:: Log Classification ::[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    ))


def display_timing_report(report: TimingReport) -> None:
    """Show the extracted timing report with rich formatting."""

    # ── Header panel ──
    header_table = Table(show_header=False, box=None, padding=(0, 2))
    header_table.add_column("Field", style="dim", width=20)
    header_table.add_column("Value", style="bold")

    header_table.add_row("Tool", report.tool_name)
    header_table.add_row("Design", report.design_name or "-")
    header_table.add_row("Path Type",
                         "Setup (max)" if report.path_type == "max" else "Hold (min)")
    header_table.add_row("Clock Domain", report.path_group)
    header_table.add_row("Startpoint", report.startpoint)
    header_table.add_row("Endpoint", report.endpoint)

    console.print(Panel(
        header_table,
        title="[bold blue]:: Timing Report ::[/bold blue]",
        border_style="blue",
        padding=(1, 2),
    ))

    # ── Timing path table ──
    if report.timing_path:
        path_table = Table(
            title="Timing Path",
            box=box.ROUNDED,
            show_lines=False,
            header_style="bold magenta",
            border_style="dim",
        )
        path_table.add_column("#", style="dim", width=4, justify="right")
        path_table.add_column("Instance", style="cyan", min_width=25)
        path_table.add_column("Cell", style="white", min_width=12)
        path_table.add_column("Incr (ns)", justify="right", min_width=10)
        path_table.add_column("Path (ns)", justify="right", min_width=10)
        path_table.add_column("Edge", justify="center", min_width=6)

        # Find the bottleneck (highest incr delay) for highlighting
        max_incr = max(
            (p.incr_delay for p in report.timing_path),
            default=0,
        )

        for i, point in enumerate(report.timing_path, 1):
            cell = point.cell_type or "-"
            edge = point.edge or "-"
            incr_str = f"{point.incr_delay:.3f}"
            path_str = f"{point.cumulative_delay:.3f}"

            # Highlight the bottleneck cell
            if point.incr_delay == max_incr and max_incr > 0:
                style = "bold red"
                incr_str += " <<<"
            else:
                style = ""

            path_table.add_row(
                str(i), point.instance, cell,
                incr_str, path_str, edge,
                style=style,
            )

        console.print(path_table)

    # ── Slack summary ──
    if report.data_arrival_time is not None:
        console.print(f"  Data Arrival Time:  [bold]{report.data_arrival_time:.3f} ns[/bold]")
    if report.data_required_time is not None:
        console.print(f"  Data Required Time: [bold]{report.data_required_time:.3f} ns[/bold]")

    slack_str = f"{report.slack:.3f} ns"
    if report.status == "VIOLATED":
        console.print(
            f"\n  Slack: [bold red]{slack_str}[/bold red]  "
            f"[white on red] X VIOLATED [/white on red]\n"
        )
    else:
        console.print(
            f"\n  Slack: [bold green]{slack_str}[/bold green]  "
            f"[white on green] OK MET [/white on green]\n"
        )


def display_diagnostics(diagnostics_text: str) -> None:
    """Show the AI diagnostics in a styled panel."""
    console.print(Panel(
        diagnostics_text,
        title="[bold red]:: AI Diagnostics ::[/bold red]",
        border_style="red",
        padding=(1, 2),
    ))


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

def cmd_analyze(args: argparse.Namespace) -> None:
    """Full analysis pipeline: classify → extract → diagnose."""

    console.print(f"\n[dim]Analyzing:[/dim] [bold]{args.file}[/bold]\n")

    try:
        # Stage 1 & 2: Classify and extract
        with console.status("[bold cyan]Classifying log...[/bold cyan]"):
            from core.extractor import classify_log as _classify
            from pathlib import Path
            raw_text = Path(args.file).read_text(encoding="utf-8", errors="replace")
            classification = _classify(raw_text)

        if args.verbose:
            display_classification(classification)

        if classification.report_type != "timing":
            console.print(
                f"[bold yellow]⚠️  Unsupported report type:[/bold yellow] "
                f"'{classification.report_type}' from {classification.tool_name}. "
                f"Only timing reports are supported in v1."
            )
            sys.exit(1)

        with console.status("[bold magenta]Extracting timing data...[/bold magenta]"):
            from core.extractor import extract_timing as _extract
            timing_report = _extract(raw_text)

        # JSON output mode
        if args.json:
            output = {
                "classification": classification.model_dump(),
                "timing_report": timing_report.model_dump(),
            }
            console.print_json(json.dumps(output, indent=2))
            return

        # Rich display
        display_timing_report(timing_report)

        # Stage 3: Diagnostics (only if violated)
        if timing_report.status == "VIOLATED":
            with console.status("[bold red]Generating AI diagnostics...[/bold red]"):
                diagnostics_text = diagnose(timing_report)
            display_diagnostics(diagnostics_text)
        else:
            console.print(
                "[bold green]✅ No timing violations found. "
                "Design meets constraints.[/bold green]\n"
            )

    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[bold yellow]Warning:[/bold yellow] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if args.verbose:
            console.print_exception()
        sys.exit(1)


def cmd_classify(args: argparse.Namespace) -> None:
    """Classify-only mode: identify the tool and report type."""

    console.print(f"\n[dim]Classifying:[/dim] [bold]{args.file}[/bold]\n")

    try:
        from pathlib import Path
        raw_text = Path(args.file).read_text(encoding="utf-8", errors="replace")

        with console.status("[bold cyan]Classifying log...[/bold cyan]"):
            classification = classify_log(raw_text)

        display_classification(classification)

        # Also output as JSON if requested
        if args.json:
            console.print_json(json.dumps(classification.model_dump(), indent=2))

    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="eda_analyzer",
        description=(
            "EDA Log Analyzer v2 - Universal, LLM-Powered\n"
            "Analyzes timing reports from ANY EDA tool using "
            "structured LLM extraction. Zero regex."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── analyze command ──
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Full analysis: classify → extract → diagnose",
    )
    analyze_parser.add_argument("file", help="Path to the EDA log file")
    analyze_parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON",
    )
    analyze_parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Show classification details and debug info",
    )

    # ── classify command ──
    classify_parser = subparsers.add_parser(
        "classify",
        help="Identify the EDA tool and report type (1 API call)",
    )
    classify_parser.add_argument("file", help="Path to the EDA log file")
    classify_parser.add_argument(
        "--json", action="store_true",
        help="Output classification as JSON",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    # Banner
    console.print(Panel(
        "[bold]EDA Log Analyzer v2[/bold]",
        border_style="bright_blue",
        padding=(0, 2),
    ))

    if args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "classify":
        cmd_classify(args)


if __name__ == "__main__":
    main()