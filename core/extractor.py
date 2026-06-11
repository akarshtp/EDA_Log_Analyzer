"""
LLM-powered EDA log extraction engine.

Replaces ALL regex-based parsing with structured LLM extraction.
Uses LangChain's `with_structured_output()` to force Gemini to return
valid Pydantic models — no string matching needed.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from tenacity import retry, wait_exponential, stop_after_attempt
from langchain_google_genai import ChatGoogleGenerativeAI

from models.schemas import LogClassification, TimingReport
from core.prompts import CLASSIFY_PROMPT, EXTRACT_TIMING_PROMPT

# Load API key from .env
load_dotenv()


def _get_llm(temperature: float = 0) -> ChatGoogleGenerativeAI:
    """Create a Gemini LLM instance.

    Uses gemini-2.5-flash (free tier: 15 RPM, 1M tokens/day).
    Temperature 0 for deterministic extraction.
    """
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=temperature,
    )


@retry(wait=wait_exponential(multiplier=1, min=10, max=60), stop=stop_after_attempt(5))
def classify_log(raw_text: str) -> LogClassification:
    """Stage 1: Identify the EDA tool, vendor, and report type.

    Sends the raw log text to the LLM with the classification prompt.
    The LLM is forced to return a valid LogClassification object.

    Args:
        raw_text: Raw log file content as a string.

    Returns:
        LogClassification with tool_name, tool_vendor, report_type,
        and confidence score.

    Raises:
        Exception: If the LLM fails to return valid structured output.
    """
    llm = _get_llm(temperature=0)
    structured_llm = llm.with_structured_output(LogClassification)

    prompt = CLASSIFY_PROMPT.format(log_content=raw_text)
    result = structured_llm.invoke(prompt)

    return result


@retry(wait=wait_exponential(multiplier=1, min=10, max=60), stop=stop_after_attempt(5))
def extract_timing(raw_text: str) -> TimingReport:
    """Stage 2: Extract structured timing data from any EDA log format.

    Uses `with_structured_output()` to force the LLM to return a valid
    TimingReport. Works for PrimeTime, Tempus, DC, ICC2, OpenSTA —
    any format the LLM can read.

    Args:
        raw_text: Raw timing report content as a string.

    Returns:
        TimingReport with all extracted fields validated by Pydantic.

    Raises:
        Exception: If the LLM fails to extract valid timing data.
    """
    llm = _get_llm(temperature=0)
    structured_llm = llm.with_structured_output(TimingReport)

    prompt = EXTRACT_TIMING_PROMPT.format(log_content=raw_text)
    result = structured_llm.invoke(prompt)

    return result


def parse_log(file_path: str) -> tuple[LogClassification, TimingReport]:
    """Main entry point: classify and extract data from an EDA log file.

    Two-stage pipeline:
      1. Classify the log (which tool? which report type?)
      2. Extract structured data (timing path, slack, etc.)

    Args:
        file_path: Path to the log file.

    Returns:
        Tuple of (LogClassification, TimingReport).

    Raises:
        FileNotFoundError: If the log file doesn't exist.
        ValueError: If the log is not a supported timing report.
        Exception: If LLM extraction fails.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {file_path}")

    raw_text = path.read_text(encoding="utf-8", errors="replace")

    if not raw_text.strip():
        raise ValueError(f"Log file is empty: {file_path}")

    # Stage 1: Classify
    classification = classify_log(raw_text)

    # Check if it's a timing report (only type supported in v1)
    if classification.report_type != "timing":
        raise ValueError(
            f"Unsupported report type: '{classification.report_type}' "
            f"(detected as {classification.tool_name} from {classification.tool_vendor}). "
            f"Only timing reports are supported in v1."
        )

    # Stage 2: Extract timing data
    timing_report = extract_timing(raw_text)

    return classification, timing_report
