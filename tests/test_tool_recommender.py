from __future__ import annotations

from ui.tool_recommender import _recommendation


DEFAULTS = {
    "problem_type": "Not sure — I just know something is wrong",
    "data_availability": "Some data — a few weeks / small sample",
    "scope": "End-to-end process (multiple steps or departments)",
    "urgency": "Medium-term — 1-3 months project",
    "measurement_confidence": "We measure but haven't validated the measurement system",
    "root_cause_status": "Have some hunches but not confirmed",
    "experience": "Yellow Belt — familiar with basics",
}


def recommend(**overrides):
    values = {**DEFAULTS, **overrides}
    return _recommendation(**values)


def test_known_solution_routes_to_control_plan() -> None:
    recommendation = recommend(
        root_cause_status="Root cause and solution are known — need to implement and sustain"
    )

    assert recommendation["tool"] == "Control Plan"


def test_data_rich_defect_problem_requires_msa_before_capability() -> None:
    recommendation = recommend(
        problem_type="Too many defects or errors",
        data_availability="Good data — months of history, 30+ data points",
        measurement_confidence="We measure but haven't validated the measurement system",
    )

    assert recommendation["tool"] == "MSA / Gauge R&R"


def test_validated_measurement_routes_data_rich_defects_to_capability() -> None:
    recommendation = recommend(
        problem_type="Too many defects or errors",
        data_availability="Lots of data — automated / ongoing process data",
        measurement_confidence="Measurement system is validated (MSA / Gauge R&R done)",
    )

    assert recommendation["tool"] == "Process Capability"


def test_limited_data_variation_routes_to_root_cause_hypotheses() -> None:
    recommendation = recommend(
        problem_type="Results are inconsistent / too much variation",
        data_availability="None yet — haven't started measuring",
    )

    assert recommendation["tool"] == "Root Cause Analysis"


def test_urgent_unspecified_problem_routes_to_kaizen() -> None:
    recommendation = recommend(
        urgency="Immediate — something needs fixing this week"
    )

    assert recommendation["tool"] == "Kaizen / Rapid Improvement"
