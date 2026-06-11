"""Unit tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from models.schemas import LogClassification, TimingPathPoint, TimingReport


# ---------------------------------------------------------------------------
# LogClassification tests
# ---------------------------------------------------------------------------

class TestLogClassification:
    """Tests for the LogClassification schema."""

    def test_valid_classification(self):
        data = LogClassification(
            tool_name="PrimeTime",
            tool_vendor="Synopsys",
            report_type="timing",
            confidence=0.95,
        )
        assert data.tool_name == "PrimeTime"
        assert data.tool_vendor == "Synopsys"
        assert data.report_type == "timing"
        assert data.confidence == 0.95

    def test_confidence_bounds(self):
        """Confidence must be between 0.0 and 1.0."""
        with pytest.raises(ValidationError):
            LogClassification(
                tool_name="Tempus",
                tool_vendor="Cadence",
                report_type="timing",
                confidence=1.5,  # Invalid: > 1.0
            )

        with pytest.raises(ValidationError):
            LogClassification(
                tool_name="Tempus",
                tool_vendor="Cadence",
                report_type="timing",
                confidence=-0.1,  # Invalid: < 0.0
            )

    def test_serialization_roundtrip(self):
        data = LogClassification(
            tool_name="OpenSTA",
            tool_vendor="OpenSource",
            report_type="timing",
            confidence=0.88,
        )
        dumped = data.model_dump()
        restored = LogClassification(**dumped)
        assert restored == data


# ---------------------------------------------------------------------------
# TimingPathPoint tests
# ---------------------------------------------------------------------------

class TestTimingPathPoint:
    """Tests for the TimingPathPoint schema."""

    def test_full_point(self):
        point = TimingPathPoint(
            instance="reg_A_0_/Q",
            cell_type="DFFRX1",
            incr_delay=0.12,
            cumulative_delay=0.17,
            edge="rise",
        )
        assert point.instance == "reg_A_0_/Q"
        assert point.cell_type == "DFFRX1"
        assert point.incr_delay == 0.12
        assert point.cumulative_delay == 0.17
        assert point.edge == "rise"

    def test_optional_fields_default_none(self):
        point = TimingPathPoint(
            instance="clk (rise edge)",
            incr_delay=0.0,
            cumulative_delay=0.0,
        )
        assert point.cell_type is None
        assert point.edge is None

    def test_negative_delay(self):
        """Negative delays are valid (e.g., clock uncertainty)."""
        point = TimingPathPoint(
            instance="clock uncertainty",
            incr_delay=-0.05,
            cumulative_delay=0.50,
        )
        assert point.incr_delay == -0.05


# ---------------------------------------------------------------------------
# TimingReport tests
# ---------------------------------------------------------------------------

class TestTimingReport:
    """Tests for the TimingReport schema."""

    def test_violated_report(self):
        report = TimingReport(
            tool_name="PrimeTime",
            design_name="alu_core",
            startpoint="reg_A_0_",
            endpoint="out_combo_3_",
            path_group="clk_main",
            path_type="max",
            slack=-0.25,
            status="VIOLATED",
            data_arrival_time=0.75,
            data_required_time=0.50,
        )
        assert report.status == "VIOLATED"
        assert report.slack == -0.25
        assert report.timing_path == []  # Default empty list

    def test_met_report(self):
        report = TimingReport(
            tool_name="Tempus",
            startpoint="reg_a",
            endpoint="reg_b",
            path_group="clk",
            path_type="max",
            slack=1.5,
            status="MET",
        )
        assert report.status == "MET"
        assert report.design_name is None
        assert report.clock_period is None

    def test_report_with_timing_path(self):
        path = [
            TimingPathPoint(
                instance="reg_A/Q", cell_type="DFFRX1",
                incr_delay=0.12, cumulative_delay=0.17, edge="rise",
            ),
            TimingPathPoint(
                instance="U45/Y", cell_type="AND2X2",
                incr_delay=0.22, cumulative_delay=0.39, edge="fall",
            ),
        ]
        report = TimingReport(
            tool_name="Design Compiler",
            startpoint="reg_A",
            endpoint="reg_B",
            path_group="clk",
            path_type="max",
            slack=-0.10,
            status="VIOLATED",
            timing_path=path,
        )
        assert len(report.timing_path) == 2
        assert report.timing_path[0].instance == "reg_A/Q"
        assert report.timing_path[1].incr_delay == 0.22

    def test_hold_analysis(self):
        report = TimingReport(
            tool_name="PrimeTime",
            startpoint="reg_a",
            endpoint="reg_b",
            path_group="clk",
            path_type="min",
            slack=0.05,
            status="MET",
        )
        assert report.path_type == "min"

    def test_json_export(self):
        report = TimingReport(
            tool_name="OpenSTA",
            startpoint="_518_",
            endpoint="_622_",
            path_group="core_clk",
            path_type="max",
            slack=-0.15,
            status="VIOLATED",
            data_arrival_time=2.46,
            data_required_time=2.31,
        )
        json_str = report.model_dump_json(indent=2)
        assert '"tool_name": "OpenSTA"' in json_str
        assert '"slack": -0.15' in json_str
