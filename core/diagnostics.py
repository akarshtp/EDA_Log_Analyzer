"""
AI-powered diagnostics engine for EDA timing violations.

Takes a validated TimingReport and generates tool-specific fix
suggestions using the full timing path data for accurate analysis.
"""

from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from tenacity import retry, wait_exponential, stop_after_attempt

from models.schemas import TimingReport
from core.prompts import DIAGNOSTICS_PROMPT

load_dotenv()


def _format_path_detail(report: TimingReport) -> str:
    """Format the timing path as a readable table for the diagnostics prompt."""
    if not report.timing_path:
        return "  (No detailed path data available)"

    lines = []
    lines.append(f"  {'Instance':<30} {'Cell':<15} {'Incr':>8} {'Path':>8} {'Edge':<6}")
    lines.append(f"  {'-' * 30} {'-' * 15} {'-' * 8} {'-' * 8} {'-' * 6}")

    for point in report.timing_path:
        cell = point.cell_type or "-"
        edge = point.edge or "-"
        lines.append(
            f"  {point.instance:<30} {cell:<15} {point.incr_delay:>8.3f} "
            f"{point.cumulative_delay:>8.3f} {edge:<6}"
        )

    return "\n".join(lines)


def _find_bottleneck_cells(report: TimingReport, top_n: int = 3) -> str:
    """Identify the cells with the highest incremental delay."""
    if not report.timing_path:
        return "  (No path data to analyze)"

    # Sort by incremental delay, descending
    sorted_points = sorted(
        report.timing_path,
        key=lambda p: abs(p.incr_delay),
        reverse=True,
    )

    lines = []
    for i, point in enumerate(sorted_points[:top_n], 1):
        cell = point.cell_type or "unknown"
        lines.append(
            f"  {i}. {point.instance} ({cell}) - "
            f"{point.incr_delay:.3f} ns incremental delay"
        )

    return "\n".join(lines)


@retry(wait=wait_exponential(multiplier=1, min=10, max=60), stop=stop_after_attempt(5))
def diagnose(report: TimingReport) -> str:
    """Generate AI-powered fix suggestions for a timing violation.

    Uses the full timing path to identify bottlenecks and generates
    tool-specific TCL commands for investigation and fixes.

    Args:
        report: A validated TimingReport with status == "VIOLATED".

    Returns:
        Formatted string with root cause analysis and fix suggestions.
        Returns a simple pass message if no violation is found.
    """
    if report.status != "VIOLATED":
        return "[PASS] No timing violations found. Design meets constraints."

    # Determine analysis type description
    if report.path_type == "max":
        analysis_type = "Setup Violation"
        path_type_desc = "data arrives too late"
    else:
        analysis_type = "Hold Violation"
        path_type_desc = "data arrives too early"

    # Build the prompt with full context
    prompt = DIAGNOSTICS_PROMPT.format(
        tool_name=report.tool_name,
        analysis_type=analysis_type,
        path_type_desc=path_type_desc,
        design_name=report.design_name or "unknown",
        startpoint=report.startpoint,
        endpoint=report.endpoint,
        path_group=report.path_group,
        data_arrival_time=report.data_arrival_time or "N/A",
        data_required_time=report.data_required_time or "N/A",
        slack=report.slack,
        status=report.status,
        path_detail=_format_path_detail(report),
        bottleneck_cells=_find_bottleneck_cells(report),
    )

    # Call the LLM for diagnostics
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.2,  # Slight creativity for suggestions
    )

    response = llm.invoke(prompt)
    return response.content
