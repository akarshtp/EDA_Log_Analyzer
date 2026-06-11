"""
Centralized prompt templates for LLM-powered EDA log analysis.

Each prompt is carefully engineered to guide Gemini toward accurate,
structured extraction from diverse EDA tool log formats.
"""

# ---------------------------------------------------------------------------
# Stage 1 — Log Classification
# ---------------------------------------------------------------------------

CLASSIFY_PROMPT = """\
You are an expert VLSI/EDA engineer. Examine the following EDA tool log and \
classify it.

Identify:
1. **tool_name** — The specific EDA tool (e.g. "PrimeTime", "Tempus", \
"Design Compiler", "ICC2", "Innovus", "OpenSTA").
2. **tool_vendor** — The vendor ("Synopsys", "Cadence", "Siemens", \
"OpenSource", or "Unknown").
3. **report_type** — The report type ("timing", "drc", "lvs", "power", \
"synthesis", or "unknown").
4. **confidence** — Your confidence in this classification (0.0 to 1.0).

Classification hints:
- Synopsys tools (PrimeTime, DC, ICC2): Use "********" star-line headers, \
  columns "Point / Incr / Path", and "Report : timing".
- Cadence tools (Tempus, Innovus): Use "Beginpoint:" (not "Startpoint:"), \
  columns "Instance / Cell / Arc", and "Path N:" headers.
- OpenSTA: Uses columns "Delay / Time / Description" with "^" and "v" \
  for rise/fall edges.
- Design Compiler may use "Pathgroup:" (one word) instead of "Path Group:".

--- BEGIN LOG ---
{log_content}
--- END LOG ---
"""

# ---------------------------------------------------------------------------
# Stage 2 — Timing Report Extraction
# ---------------------------------------------------------------------------

EXTRACT_TIMING_PROMPT = """\
You are an expert VLSI Static Timing Analysis (STA) engineer. Extract ALL \
timing information from the following EDA tool log into a structured format.

Instructions:
1. **tool_name**: Identify the EDA tool (PrimeTime, Tempus, Design Compiler, \
   ICC2, OpenSTA, Innovus, etc.).
2. **design_name**: The design/module name from the report header.
3. **startpoint**: The full startpoint description (called "Beginpoint" in \
   Cadence tools).
4. **endpoint**: The full endpoint description.
5. **path_group**: Clock domain name (may be labeled "Path Group" or \
   "Pathgroup").
6. **path_type**: "max" for setup analysis, "min" for hold analysis.
7. **slack**: The numeric slack value in nanoseconds (negative = violation).
8. **status**: "VIOLATED" if slack is negative, "MET" if positive/zero.
9. **data_arrival_time**: The data arrival time value.
10. **data_required_time**: The data required time value.
11. **timing_path**: Extract each row of the timing path table as a list:
    - **instance**: Pin/cell instance name
    - **cell_type**: Library cell (e.g. "DFFRX1"), null if not shown
    - **incr_delay**: Incremental delay
    - **cumulative_delay**: Cumulative delay
    - **edge**: Normalize to "rise" or "fall" (from r/f, R/F, ^/v)
12. **clock_period**: Clock period if determinable from clock edges.

Important:
- Extract the DATA path points (from launch clock to data arrival).
- Include clock network entries as path points too.
- If a field is not present in the log, use null.
- Always return numeric values as floats, not strings.

--- BEGIN TIMING REPORT ---
{log_content}
--- END TIMING REPORT ---
"""

# ---------------------------------------------------------------------------
# Stage 3 — AI Diagnostics
# ---------------------------------------------------------------------------

DIAGNOSTICS_PROMPT = """\
You are an expert VLSI CAD & Physical Design Engineer. Analyze the following \
Static Timing Analysis data and provide actionable fix suggestions.

**Report Source**: {tool_name}
**Analysis Type**: {analysis_type} ({path_type_desc})
**Design**: {design_name}

**Timing Path Summary**:
- Startpoint: {startpoint}
- Endpoint: {endpoint}
- Clock Domain: {path_group}
- Data Arrival Time: {data_arrival_time} ns
- Data Required Time: {data_required_time} ns
- Slack: {slack} ns ({status})

**Critical Path Detail**:
{path_detail}

**Bottleneck Cells** (highest incremental delay):
{bottleneck_cells}

Provide:
1. A **root cause analysis** of why this path is failing (be specific about \
   which cells/nets are the bottleneck).
2. **3-5 actionable fixes**, ordered by effectiveness. For each fix:
   - Describe the technique (RTL, synthesis constraint, or P&R)
   - Provide the exact {tool_name} TCL command to investigate or apply it
   - Estimate the expected improvement
3. A **quick-win recommendation** — the single change most likely to fix \
   this with minimal effort.

Do not use conversational filler. Be technically precise.
"""
