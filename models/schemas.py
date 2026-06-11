"""
Pydantic schemas for universal EDA log data.

These models replace the raw dicts used in v1. Every field is typed,
validated, and documented — making the extracted data reliable regardless
of which EDA tool produced the original log.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Stage 1 output — Log Classification
# ---------------------------------------------------------------------------

class LogClassification(BaseModel):
    """First-pass LLM classification of an unknown log file.

    The LLM reads the raw text and identifies which tool, vendor, and
    report type it belongs to before detailed extraction begins.
    """

    tool_name: str = Field(
        description=(
            "Name of the EDA tool that generated this log. "
            "Examples: 'PrimeTime', 'Tempus', 'Design Compiler', "
            "'ICC2', 'OpenSTA', 'Innovus'."
        )
    )
    tool_vendor: str = Field(
        description=(
            "Vendor of the EDA tool. "
            "One of: 'Synopsys', 'Cadence', 'Siemens', 'OpenSource', 'Unknown'."
        )
    )
    report_type: str = Field(
        description=(
            "Type of report contained in the log. "
            "One of: 'timing', 'drc', 'lvs', 'power', 'synthesis', 'unknown'."
        )
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0 for this classification.",
    )


# ---------------------------------------------------------------------------
# Timing path detail
# ---------------------------------------------------------------------------

class TimingPathPoint(BaseModel):
    """A single row in a timing path table.

    Represents one cell/net/pin in the timing path with its delay
    contribution. Works across all tool formats:
      - Synopsys (Point / Incr / Path)
      - Cadence  (Instance / Cell / Arc / Incr / Path)
      - OpenSTA  (Delay / Time / Description)
    """

    instance: str = Field(
        description=(
            "Instance or pin name in the timing path. "
            "Examples: 'reg_A_0_/CP', 'U45/Y', 'clock clk_main (rise edge)'."
        )
    )
    cell_type: Optional[str] = Field(
        default=None,
        description=(
            "Library cell type, if available. "
            "Examples: 'DFFRX1', 'AND2X2', 'INVX1'. "
            "May be None for clock network entries or ports."
        ),
    )
    incr_delay: float = Field(
        description="Incremental delay added by this element (in ns)."
    )
    cumulative_delay: float = Field(
        description="Cumulative path delay up to this point (in ns)."
    )
    edge: Optional[str] = Field(
        default=None,
        description=(
            "Signal transition at this point. "
            "Normalized to 'rise' or 'fall'. "
            "Mapped from tool-specific indicators: "
            "'r'/'^' → 'rise', 'f'/'v' → 'fall'."
        ),
    )


# ---------------------------------------------------------------------------
# Stage 2 output — Universal Timing Report
# ---------------------------------------------------------------------------

class TimingReport(BaseModel):
    """Universal timing report — works for PrimeTime, Tempus, DC, ICC2, OpenSTA.

    This is the core data model that the LLM extracts from ANY timing
    report format. All fields are tool-agnostic.
    """

    tool_name: str = Field(
        description=(
            "Name of the EDA tool that generated this report. "
            "Examples: 'PrimeTime', 'Tempus', 'Design Compiler', 'OpenSTA'."
        )
    )
    design_name: Optional[str] = Field(
        default=None,
        description="Design or module name reported in the header.",
    )
    startpoint: str = Field(
        description=(
            "Timing path startpoint. "
            "Includes the full description if available, e.g. "
            "'reg_A_0_ (rising edge-triggered flip-flop clocked by clk_main)'."
        )
    )
    endpoint: str = Field(
        description=(
            "Timing path endpoint. "
            "Includes the full description if available."
        )
    )
    path_group: str = Field(
        description=(
            "Clock domain / path group name. "
            "Examples: 'clk_main', 'clk', 'async'."
        )
    )
    path_type: str = Field(
        description=(
            "Analysis type. 'max' for setup analysis, 'min' for hold analysis."
        )
    )
    slack: float = Field(
        description=(
            "Timing slack in nanoseconds. "
            "Negative values indicate a violation."
        )
    )
    status: str = Field(
        description="Timing status: 'VIOLATED' or 'MET'."
    )
    data_arrival_time: Optional[float] = Field(
        default=None,
        description="Data arrival time in nanoseconds.",
    )
    data_required_time: Optional[float] = Field(
        default=None,
        description="Data required time in nanoseconds.",
    )
    timing_path: list[TimingPathPoint] = Field(
        default_factory=list,
        description=(
            "Ordered list of points in the timing path. "
            "Each entry represents a cell/net with its delay contribution."
        ),
    )
    clock_period: Optional[float] = Field(
        default=None,
        description="Clock period in nanoseconds, if determinable from the report.",
    )
