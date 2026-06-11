"""
Integration tests for the LLM extraction engine.

These tests require a valid GOOGLE_API_KEY in .env and make real API calls.
Run with: python -m pytest tests/test_extractor.py -v
"""

import pytest
from pathlib import Path

from core.extractor import classify_log, extract_timing, parse_log
from models.schemas import LogClassification, TimingReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLES_DIR = Path(__file__).parent.parent / "samples"
ORIGINAL_LOG = Path(__file__).parent.parent / "sta_timing_report.log"


def _read_sample(filename: str) -> str:
    return (SAMPLES_DIR / filename).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Classification tests
# ---------------------------------------------------------------------------

class TestClassifyLog:
    """Test log classification across different tool formats."""

    def test_classify_synopsys_dc(self):
        """Original log should be classified as Synopsys timing report."""
        raw_text = ORIGINAL_LOG.read_text(encoding="utf-8")
        result = classify_log(raw_text)

        assert isinstance(result, LogClassification)
        assert result.tool_vendor == "Synopsys"
        assert result.report_type == "timing"
        assert result.confidence >= 0.7

    def test_classify_primetime(self):
        raw_text = _read_sample("primetime_setup.rpt")
        result = classify_log(raw_text)

        assert result.tool_vendor == "Synopsys"
        assert result.report_type == "timing"
        assert "PrimeTime" in result.tool_name or "primetime" in result.tool_name.lower()

    def test_classify_tempus(self):
        raw_text = _read_sample("tempus_timing.rpt")
        result = classify_log(raw_text)

        assert result.tool_vendor == "Cadence"
        assert result.report_type == "timing"

    def test_classify_opensta(self):
        raw_text = _read_sample("opensta_timing.rpt")
        result = classify_log(raw_text)

        assert result.report_type == "timing"


# ---------------------------------------------------------------------------
# Extraction tests
# ---------------------------------------------------------------------------

class TestExtractTiming:
    """Test timing data extraction across different formats."""

    def test_extract_original_log(self):
        """Verify LLM extraction matches the old regex results."""
        raw_text = ORIGINAL_LOG.read_text(encoding="utf-8")
        result = extract_timing(raw_text)

        assert isinstance(result, TimingReport)
        assert "reg_A_0_" in result.startpoint
        assert "out_combo_3_" in result.endpoint
        assert result.path_group == "clk_main"
        assert result.slack == pytest.approx(-0.25, abs=0.01)
        assert result.status == "VIOLATED"

    def test_extract_primetime(self):
        raw_text = _read_sample("primetime_setup.rpt")
        result = extract_timing(raw_text)

        assert result.status == "MET"
        assert result.slack > 0
        assert result.path_type == "max"
        assert len(result.timing_path) > 0

    def test_extract_tempus(self):
        raw_text = _read_sample("tempus_timing.rpt")
        result = extract_timing(raw_text)

        assert result.status == "VIOLATED"
        assert result.slack < 0
        assert len(result.timing_path) > 0

    def test_extract_opensta(self):
        raw_text = _read_sample("opensta_timing.rpt")
        result = extract_timing(raw_text)

        assert result.status == "VIOLATED"
        assert result.slack == pytest.approx(-0.15, abs=0.02)
        assert len(result.timing_path) > 0


# ---------------------------------------------------------------------------
# Full pipeline tests
# ---------------------------------------------------------------------------

class TestParseLog:
    """Test the full parse_log pipeline."""

    def test_full_pipeline_original(self):
        classification, report = parse_log(str(ORIGINAL_LOG))

        assert classification.report_type == "timing"
        assert report.status == "VIOLATED"
        assert report.slack < 0

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_log("nonexistent_file.log")
