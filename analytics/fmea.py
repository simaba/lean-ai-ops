"""
Failure Mode and Effects Analysis (FMEA)
=========================================
Implements a complete FMEA workflow: entry creation, post-action update,
DataFrame conversion, and Altair visualisations (risk matrix + Pareto chart).

Severity / Occurrence / Detection are rated 1–10 following the AIAG FMEA-4
reference manual scale.  Risk Priority Number (RPN) = S × O × D.

Usage
-----
    from analytics.fmea import new_entry, update_post_action, fmea_to_dataframe
    from analytics.fmea import fmea_risk_matrix_chart, fmea_pareto_chart

    entry = new_entry(
        process_step="Welding",
        failure_mode="Porosity",
        failure_effect="Weld joint failure under load",
        failure_cause="Shielding gas contamination",
        current_controls="Visual inspection after weld",
        severity=8, occurrence=4, detection=5,
        recommended_action="Add helium leak test inline",
        action_owner="Process Engineer",
        target_date="2026-06-30",
    )
    entry = update_post_action(entry, post_s=8, post_o=2, post_d=3)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import List, Optional

import altair as alt
import pandas as pd


# ---------------------------------------------------------------------------
# Severity interpretation map
# ---------------------------------------------------------------------------

SEVERITY_DESCRIPTIONS: dict[tuple[int, int], str] = {
    (9, 10): "Catastrophic — risk to safety or regulatory compliance",
    (7,  8): "Serious — major process disruption or customer impact",
    (5,  6): "Moderate — significant impact but workaround exists",
    (3,  4): "Minor — slight inconvenience",
    (1,  2): "Negligible — no noticeable effect",
}


def _severity_description(severity: int) -> str:
    for (lo, hi), desc in SEVERITY_DESCRIPTIONS.items():
        if lo <= severity <= hi:
            return desc
    return "Unknown severity level"


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class FMEAEntry:
    """A single FMEA row with pre- and post-action data."""

    id: str
    process_step: str
    failure_mode: str
    failure_effect: str
    failure_cause: str
    current_controls: str

    severity: int                   # 1–10
    occurrence: int                 # 1–10
    detection: int                  # 1–10
    rpn: int                        # S × O × D

    action_priority: str            # "High" | "Medium" | "Low"
    recommended_action: str
    action_owner: str
    target_date: str

    # Post-action fields (populated after implementing the control)
    post_action_severity:   Optional[int]   = None
    post_action_occurrence: Optional[int]   = None
    post_action_detection:  Optional[int]   = None
    post_action_rpn:        Optional[int]   = None
    risk_reduction_pct:     Optional[float] = None


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------

def new_entry(
    process_step: str,
    failure_mode: str,
    failure_effect: str,
    failure_cause: str,
    current_controls: str,
    severity: int,
    occurrence: int,
    detection: int,
    recommended_action: str = "",
    action_owner: str = "",
    target_date: str = "",
) -> FMEAEntry:
    """
    Create a new FMEAEntry, computing RPN and action priority automatically.

    Priority rules (AIAG aligned):
        High   — severity ≥ 9  OR  RPN ≥ 200
        Medium — RPN ≥ 80
        Low    — RPN < 80
    """
    # Validate rating ranges
    for name, val in [("severity", severity), ("occurrence", occurrence), ("detection", detection)]:
        if not (1 <= val <= 10):
            raise ValueError(f"{name} must be between 1 and 10, got {val}.")

    rpn = severity * occurrence * detection

    if severity >= 9 or rpn >= 200:
        action_priority = "High"
    elif rpn >= 80:
        action_priority = "Medium"
    else:
        action_priority = "Low"

    return FMEAEntry(
        id=str(uuid.uuid4()),
        process_step=process_step,
        failure_mode=failure_mode,
        failure_effect=failure_effect,
        failure_cause=failure_cause,
        current_controls=current_controls,
        severity=severity,
        occurrence=occurrence,
        detection=detection,
        rpn=rpn,
        action_priority=action_priority,
        recommended_action=recommended_action,
        action_owner=action_owner,
        target_date=target_date,
    )


def update_post_action(
    entry: FMEAEntry,
    post_s: int,
    post_o: int,
    post_d: int,
) -> FMEAEntry:
    """
    Record post-action ratings and compute post_action_rpn and risk_reduction_pct.

    Note: Severity typically does not decrease unless the product/process design
    changes.  The function allows any rating to be entered to reflect real scenarios.
    """
    for name, val in [("post_s", post_s), ("post_o", post_o), ("post_d", post_d)]:
        if not (1 <= val <= 10):
            raise ValueError(f"{name} must be between 1 and 10, got {val}.")

    post_rpn = post_s * post_o * post_d
    reduction = (1.0 - post_rpn / entry.rpn) * 100.0 if entry.rpn > 0 else 0.0

    entry.post_action_severity   = post_s
    entry.post_action_occurrence = post_o
    entry.post_action_detection  = post_d
    entry.post_action_rpn        = post_rpn
    entry.risk_reduction_pct     = round(reduction, 1)
    return entry


# ---------------------------------------------------------------------------
# DataFrame conversion
# ---------------------------------------------------------------------------

def fmea_to_dataframe(entries: List[FMEAEntry]) -> pd.DataFrame:
    """
    Convert a list of FMEAEntry objects to a DataFrame sorted by RPN descending.
    """
    records = []
    for e in entries:
        severity_desc = _severity_description(e.severity)
        records.append(
            {
                "ID":                    e.id,
                "Process Step":          e.process_step,
                "Failure Mode":          e.failure_mode,
                "Failure Effect":        e.failure_effect,
                "Failure Cause":         e.failure_cause,
                "Current Controls":      e.current_controls,
                "Severity (S)":          e.severity,
                "Severity Description":  severity_desc,
                "Occurrence (O)":        e.occurrence,
                "Detection (D)":         e.detection,
                "RPN":                   e.rpn,
                "Action Priority":       e.action_priority,
                "Recommended Action":    e.recommended_action,
                "Action Owner":          e.action_owner,
                "Target Date":           e.target_date,
                "Post S":                e.post_action_severity,
                "Post O":                e.post_action_occurrence,
                "Post D":                e.post_action_detection,
                "Post RPN":              e.post_action_rpn,
                "Risk Reduction %":      e.risk_reduction_pct,
            }
        )
    df = pd.DataFrame(records)
    df.sort_values("RPN", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


# ---------------------------------------------------------------------------
# Chart: Risk Matrix (Bubble)
# ---------------------------------------------------------------------------

def fmea_risk_matrix_chart(entries: List[FMEAEntry]) -> alt.Chart:
    """
    Bubble chart: Severity (y) vs Occurrence (x).
    Bubble size encodes Detection difficulty (larger = harder to detect = higher risk).
    Color encodes Action Priority.

    Returns
    -------
    alt.Chart
    """
    if not entries:
        return alt.Chart(pd.DataFrame()).mark_text().encode(
            text=alt.value("No FMEA entries to display.")
        )

    records = [
        {
            "Failure Mode":    e.failure_mode,
            "Process Step":    e.process_step,
            "Severity":        e.severity,
            "Occurrence":      e.occurrence,
            "Detection":       e.detection,
            "RPN":             e.rpn,
            "Action Priority": e.action_priority,
        }
        for e in entries
    ]
    df = pd.DataFrame(records)

    # Map detection to bubble size: higher detection score = harder to detect = larger
    # We use a size range of 50–800 proportional to detection^2
    df["BubbleSize"] = df["Detection"] ** 2 * 8

    color_scale = alt.Scale(
        domain=["High", "Medium", "Low"],
        range=["#EF233C", "#FFB703", "#06D6A0"],
    )

    chart = (
        alt.Chart(df)
        .mark_circle(opacity=0.80, stroke="white", strokeWidth=1)
        .encode(
            x=alt.X(
                "Occurrence:Q",
                scale=alt.Scale(domain=[0, 11]),
                axis=alt.Axis(title="Occurrence (1–10)", tickCount=10, grid=True),
            ),
            y=alt.Y(
                "Severity:Q",
                scale=alt.Scale(domain=[0, 11]),
                axis=alt.Axis(title="Severity (1–10)", tickCount=10, grid=True),
            ),
            size=alt.Size(
                "BubbleSize:Q",
                legend=alt.Legend(title="Detection (size)"),
                scale=alt.Scale(range=[50, 900]),
            ),
            color=alt.Color(
                "Action Priority:N",
                scale=color_scale,
                legend=alt.Legend(title="Action Priority"),
            ),
            tooltip=[
                alt.Tooltip("Failure Mode:N"),
                alt.Tooltip("Process Step:N"),
                alt.Tooltip("Severity:Q"),
                alt.Tooltip("Occurrence:Q"),
                alt.Tooltip("Detection:Q"),
                alt.Tooltip("RPN:Q"),
                alt.Tooltip("Action Priority:N"),
            ],
        )
        .properties(
            width=520,
            height=420,
            title="Risk Matrix (Severity vs Occurrence, size = Detection difficulty)",
        )
    )

    # Add quadrant shading reference lines at S=7 and O=4 (common thresholds)
    vline = (
        alt.Chart(pd.DataFrame({"x": [4]}))
        .mark_rule(color="#AAAAAA", strokeDash=[4, 4], strokeWidth=1)
        .encode(x="x:Q")
    )
    hline = (
        alt.Chart(pd.DataFrame({"y": [7]}))
        .mark_rule(color="#AAAAAA", strokeDash=[4, 4], strokeWidth=1)
        .encode(y="y:Q")
    )

    return (chart + vline + hline).configure_view(stroke=None)


# ---------------------------------------------------------------------------
# Chart: Pareto by RPN
# ---------------------------------------------------------------------------

def fmea_pareto_chart(entries: List[FMEAEntry]) -> alt.Chart:
    """
    Pareto chart of failure modes sorted by RPN descending.
    Shows bars (RPN) and cumulative percentage line on a dual-axis layout.

    Returns
    -------
    alt.LayerChart
    """
    if not entries:
        return alt.Chart(pd.DataFrame()).mark_text().encode(
            text=alt.value("No FMEA entries to display.")
        )

    records = [
        {
            "Failure Mode": f"{e.failure_mode}\n({e.process_step})",
            "RPN":          e.rpn,
            "Priority":     e.action_priority,
        }
        for e in entries
    ]
    df = pd.DataFrame(records)
    df.sort_values("RPN", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)

    total_rpn = df["RPN"].sum()
    df["Cumulative RPN"] = df["RPN"].cumsum()
    df["Cumulative %"]   = df["Cumulative RPN"] / total_rpn * 100
    df["Order"]          = range(len(df))
    df["Label"]          = df["Failure Mode"].str.replace("\n", " — ")

    color_scale = alt.Scale(
        domain=["High", "Medium", "Low"],
        range=["#EF233C", "#FFB703", "#06D6A0"],
    )

    bars = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(
                "Label:N",
                sort=list(df["Label"]),
                axis=alt.Axis(labelAngle=-35, title="Failure Mode (Process Step)"),
            ),
            y=alt.Y(
                "RPN:Q",
                axis=alt.Axis(title="RPN", titleColor="#333333"),
            ),
            color=alt.Color("Priority:N", scale=color_scale, legend=alt.Legend(title="Priority")),
            tooltip=[
                alt.Tooltip("Label:N", title="Failure Mode"),
                alt.Tooltip("RPN:Q"),
                alt.Tooltip("Cumulative %:Q", format=".1f", title="Cumulative %"),
                alt.Tooltip("Priority:N"),
            ],
        )
    )

    cumulative_line = (
        alt.Chart(df)
        .mark_line(color="#333333", strokeWidth=2, point=alt.OverlayMarkDef(color="#333333", size=40))
        .encode(
            x=alt.X("Label:N", sort=list(df["Label"])),
            y=alt.Y(
                "Cumulative %:Q",
                axis=alt.Axis(title="Cumulative %", titleColor="#333333"),
                scale=alt.Scale(domain=[0, 105]),
            ),
            tooltip=[
                alt.Tooltip("Label:N", title="Failure Mode"),
                alt.Tooltip("Cumulative %:Q", format=".1f", title="Cumulative %"),
            ],
        )
    )

    # 80% reference line
    rule_80 = (
        alt.Chart(pd.DataFrame({"y": [80]}))
        .mark_rule(color="#EF233C", strokeDash=[5, 3], strokeWidth=1.5)
        .encode(y=alt.Y("y:Q"))
    )

    chart = (
        alt.layer(bars, cumulative_line + rule_80)
        .resolve_scale(y="independent")
        .properties(
            width=600,
            height=320,
            title="FMEA Pareto — Failure Modes by RPN (descending)",
        )
        .configure_view(stroke=None)
        .configure_axis(grid=True, gridColor="#EEEEEE")
    )

    return chart
