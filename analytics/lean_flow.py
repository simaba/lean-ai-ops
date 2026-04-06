"""
Lean Flow / Value Stream Analysis Module
=========================================
Provides takt time analysis, value stream mapping metrics, bottleneck
identification, Process Cycle Efficiency (PCE), and Little's Law WIP
estimation for Lean Six Sigma projects.

The module follows standard Lean / Toyota Production System (TPS) definitions:
    Value-Added (VA)     — activities the customer is willing to pay for
    Non-Value-Added (NVA) — activities that consume resources but add no value
    Takt Time            — available production time divided by customer demand
    Process Cycle Efficiency — VA time / total lead time × 100
    Little's Law         — Lead Time = WIP / Throughput Rate

Usage
-----
    from analytics.lean_flow import (
        ProcessStep, run_lean_flow_analysis,
        value_stream_chart, utilisation_chart,
        pce_gauge_html, waste_waterfall_chart,
    )

    steps = [
        ProcessStep("Order Entry",   cycle_time_min=5.0,  wait_time_min=120.0,
                    defect_rate_pct=2.0,  is_value_added=False, operator_count=1.0),
        ProcessStep("Machining",     cycle_time_min=18.0, wait_time_min=240.0,
                    defect_rate_pct=4.5,  is_value_added=True,  operator_count=2.0,
                    uptime_pct=88.0, rework_pct=60.0),
        ProcessStep("Assembly",      cycle_time_min=12.0, wait_time_min=60.0,
                    defect_rate_pct=1.5,  is_value_added=True,  operator_count=2.0),
        ProcessStep("Quality Check", cycle_time_min=6.0,  wait_time_min=30.0,
                    defect_rate_pct=0.5,  is_value_added=False, operator_count=1.0),
        ProcessStep("Shipping Prep", cycle_time_min=4.0,  wait_time_min=15.0,
                    defect_rate_pct=0.2,  is_value_added=True,  operator_count=1.0),
    ]

    result = run_lean_flow_analysis(
        steps=steps,
        takt_time_min=20.0,
        available_time_min=450.0,   # 7.5-hour shift
        demand_per_day=22,
    )

    chart = value_stream_chart(result)
    util  = utilisation_chart(result)
    gauge = pce_gauge_html(result.process_cycle_efficiency_pct)
    wfall = waste_waterfall_chart(result)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import altair as alt
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ProcessStep:
    """A single step in the value stream."""

    name: str
    cycle_time_min: float        # manual / machine work time per unit (minutes)
    wait_time_min: float         # queue / wait time before this step (minutes)
    defect_rate_pct: float       # % of units requiring rework or scrap at this step
    is_value_added: bool         # True = VA, False = NVA
    operator_count: float        # headcount assigned to this step
    batch_size: int = 1          # units processed per batch
    uptime_pct: float = 100.0    # machine/resource uptime (%)
    rework_pct: float = 0.0      # % of defective units that are reworked (vs scrapped)

    def __post_init__(self) -> None:
        if self.cycle_time_min < 0:
            raise ValueError(f"cycle_time_min must be non-negative, got {self.cycle_time_min}.")
        if self.wait_time_min < 0:
            raise ValueError(f"wait_time_min must be non-negative, got {self.wait_time_min}.")
        if not (0.0 <= self.defect_rate_pct <= 100.0):
            raise ValueError(f"defect_rate_pct must be 0–100, got {self.defect_rate_pct}.")
        if self.operator_count < 0:
            raise ValueError(f"operator_count must be non-negative, got {self.operator_count}.")
        if self.batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {self.batch_size}.")
        if not (0.0 < self.uptime_pct <= 100.0):
            raise ValueError(f"uptime_pct must be > 0 and <= 100, got {self.uptime_pct}.")
        if not (0.0 <= self.rework_pct <= 100.0):
            raise ValueError(f"rework_pct must be 0–100, got {self.rework_pct}.")


@dataclass
class LeanFlowResult:
    """Aggregated Lean / value stream analysis results."""

    # ------------------------------------------------------------------
    # Takt & demand
    # ------------------------------------------------------------------
    takt_time_min: float               # customer demand rate (min per unit)
    total_demand_per_day: float
    available_time_min: float

    # ------------------------------------------------------------------
    # Value stream totals
    # ------------------------------------------------------------------
    total_cycle_time_min: float        # sum of all step cycle times
    total_wait_time_min: float         # sum of all step wait times
    total_lead_time_min: float         # total CT + total wait (end-to-end)
    process_cycle_efficiency_pct: float  # VA time / lead time × 100

    # ------------------------------------------------------------------
    # WIP & throughput (Little's Law)
    # ------------------------------------------------------------------
    throughput_units_per_hour: float
    avg_wip_units: float
    littles_law_lead_time_min: float   # WIP / throughput rate (should ≈ lead time)

    # ------------------------------------------------------------------
    # Bottleneck
    # ------------------------------------------------------------------
    bottleneck_step: str
    bottleneck_ct_min: float           # effective CT of bottleneck (adjusted for uptime)
    bottleneck_utilisation_pct: float  # effective CT / takt time × 100

    # ------------------------------------------------------------------
    # Waste summary
    # ------------------------------------------------------------------
    total_defect_rework_time_min: float
    nva_time_min: float
    va_time_min: float
    waste_pct_of_lead_time: float

    # ------------------------------------------------------------------
    # Per-step analysis
    # ------------------------------------------------------------------
    step_analysis: List[dict]

    # ------------------------------------------------------------------
    # Narrative
    # ------------------------------------------------------------------
    observations: List[str]
    recommendations: List[str]


# ---------------------------------------------------------------------------
# Core analysis function
# ---------------------------------------------------------------------------

def run_lean_flow_analysis(
    steps: List[ProcessStep],
    takt_time_min: float,
    available_time_min: float,
    demand_per_day: float,
) -> LeanFlowResult:
    """
    Compute a full Lean / value stream analysis for a list of process steps.

    Parameters
    ----------
    steps : list[ProcessStep]
        Ordered list of process steps from first to last in the value stream.
    takt_time_min : float
        Customer takt time in minutes per unit
        (= available_time_min / demand_per_day).
    available_time_min : float
        Net available production time per day/shift (minutes).
    demand_per_day : float
        Customer demand units per day/shift.

    Returns
    -------
    LeanFlowResult
    """
    if not steps:
        raise ValueError("steps must contain at least one ProcessStep.")
    if takt_time_min <= 0:
        raise ValueError(f"takt_time_min must be > 0, got {takt_time_min}.")
    if available_time_min <= 0:
        raise ValueError(f"available_time_min must be > 0, got {available_time_min}.")
    if demand_per_day <= 0:
        raise ValueError(f"demand_per_day must be > 0, got {demand_per_day}.")

    # ------------------------------------------------------------------
    # 1.  Value stream totals
    # ------------------------------------------------------------------
    total_cycle_time_min = sum(s.cycle_time_min for s in steps)
    total_wait_time_min  = sum(s.wait_time_min  for s in steps)
    total_lead_time_min  = total_cycle_time_min + total_wait_time_min

    va_time_min  = sum(s.cycle_time_min for s in steps if s.is_value_added)
    nva_cycle    = sum(s.cycle_time_min for s in steps if not s.is_value_added)
    nva_time_min = nva_cycle + total_wait_time_min   # NVA CT + all waiting

    process_cycle_efficiency_pct = (
        (va_time_min / total_lead_time_min * 100.0) if total_lead_time_min > 0 else 0.0
    )

    # ------------------------------------------------------------------
    # 2.  Bottleneck — step with highest effective cycle time
    #     Effective CT = cycle_time_min / (uptime_pct / 100)
    # ------------------------------------------------------------------
    effective_cts = [s.cycle_time_min / (s.uptime_pct / 100.0) for s in steps]
    bottleneck_idx = int(np.argmax(effective_cts))
    bottleneck_step = steps[bottleneck_idx].name
    bottleneck_ct_min = effective_cts[bottleneck_idx]
    bottleneck_utilisation_pct = (
        (bottleneck_ct_min / takt_time_min * 100.0) if takt_time_min > 0 else 0.0
    )

    # ------------------------------------------------------------------
    # 3.  Throughput & WIP (Little's Law)
    #     Throughput is constrained by the bottleneck effective CT.
    #     throughput_rate (units/min) = 1 / bottleneck_effective_CT
    #     But also capped by takt: cannot ship faster than demand.
    # ------------------------------------------------------------------
    throughput_rate_per_min = min(
        1.0 / bottleneck_ct_min if bottleneck_ct_min > 0 else float("inf"),
        1.0 / takt_time_min,
    )
    throughput_units_per_hour = throughput_rate_per_min * 60.0

    # WIP via Little's Law: WIP = throughput_rate × lead_time
    avg_wip_units = throughput_rate_per_min * total_lead_time_min

    # Implied lead time from Little's Law (cross-check)
    littles_law_lead_time_min = (
        avg_wip_units / throughput_rate_per_min if throughput_rate_per_min > 0 else 0.0
    )

    # ------------------------------------------------------------------
    # 4.  Defect rework time
    #     Per step: CT × defect_rate/100 × rework_pct/100
    # ------------------------------------------------------------------
    total_defect_rework_time_min = sum(
        s.cycle_time_min * (s.defect_rate_pct / 100.0) * (s.rework_pct / 100.0)
        for s in steps
    )

    waste_pct_of_lead_time = (
        ((nva_time_min + total_defect_rework_time_min) / total_lead_time_min * 100.0)
        if total_lead_time_min > 0 else 0.0
    )

    # ------------------------------------------------------------------
    # 5.  Per-step analysis
    # ------------------------------------------------------------------
    step_analysis: List[dict] = []
    for i, s in enumerate(steps):
        eff_ct = effective_cts[i]
        util   = (eff_ct / takt_time_min * 100.0) if takt_time_min > 0 else 0.0
        step_analysis.append(
            {
                "step":              s.name,
                "cycle_time_min":    s.cycle_time_min,
                "wait_time_min":     s.wait_time_min,
                "is_value_added":    s.is_value_added,
                "utilisation_pct":   round(util, 2),
                "effective_ct_min":  round(eff_ct, 4),
                "is_bottleneck":     i == bottleneck_idx,
                "defect_rate_pct":   s.defect_rate_pct,
                "operator_count":    s.operator_count,
                "uptime_pct":        s.uptime_pct,
            }
        )

    # ------------------------------------------------------------------
    # 6.  Observations (plain English)
    # ------------------------------------------------------------------
    observations: List[str] = []

    # PCE health
    if process_cycle_efficiency_pct < 1.0:
        observations.append(
            f"Process Cycle Efficiency is critically low at {process_cycle_efficiency_pct:.1f}%. "
            "Fewer than 1% of elapsed time adds customer value — the value stream is "
            "dominated by waiting and non-value-added activity."
        )
    elif process_cycle_efficiency_pct < 5.0:
        observations.append(
            f"Process Cycle Efficiency is {process_cycle_efficiency_pct:.1f}%, which is poor "
            "(typical manufacturing PCE is 5–25%). There is significant opportunity to compress "
            "lead time by attacking queue and wait times."
        )
    elif process_cycle_efficiency_pct <= 25.0:
        observations.append(
            f"Process Cycle Efficiency is {process_cycle_efficiency_pct:.1f}%, within the "
            "typical manufacturing range of 5–25%. Focused kaizen on the largest wait "
            "segments can push this higher."
        )
    else:
        observations.append(
            f"Process Cycle Efficiency is {process_cycle_efficiency_pct:.1f}%, which is good "
            "(above 25%). The value stream is relatively lean, though further improvement "
            "remains possible."
        )

    # Bottleneck
    if bottleneck_utilisation_pct > 100.0:
        observations.append(
            f"The bottleneck is '{bottleneck_step}' with an effective cycle time of "
            f"{bottleneck_ct_min:.1f} min — {bottleneck_utilisation_pct - 100:.1f}% over takt. "
            "This step is starving downstream operations and will cause a backlog under "
            "current demand."
        )
    elif bottleneck_utilisation_pct > 90.0:
        observations.append(
            f"'{bottleneck_step}' is the bottleneck at {bottleneck_utilisation_pct:.1f}% "
            "utilisation — dangerously close to capacity with no buffer for variation or "
            "unplanned downtime."
        )
    else:
        observations.append(
            f"'{bottleneck_step}' is the constraining step at {bottleneck_utilisation_pct:.1f}% "
            "utilisation. The line has some capacity headroom, but this step should be "
            "protected from disruption."
        )

    # Wait time proportion
    wait_proportion = (total_wait_time_min / total_lead_time_min * 100.0) if total_lead_time_min > 0 else 0.0
    observations.append(
        f"Wait / queue time accounts for {wait_proportion:.1f}% of total lead time "
        f"({total_wait_time_min:.0f} min of {total_lead_time_min:.0f} min). "
        "Reducing batch sizes and implementing pull/kanban signals are the primary levers "
        "to address this."
    )

    # WIP observation
    observations.append(
        f"Little's Law estimates {avg_wip_units:.1f} units of average WIP in the system, "
        f"yielding an implied lead time of {littles_law_lead_time_min:.0f} min. "
        "High WIP inflates lead time, ties up working capital, and obscures quality problems."
    )

    # Defect / rework observation
    if total_defect_rework_time_min > 0:
        observations.append(
            f"Defect rework adds an estimated {total_defect_rework_time_min:.1f} min of "
            "hidden work per unit cycle. Eliminating root causes reduces effective load on "
            "operators and lowers the risk of the bottleneck being pushed over takt."
        )

    # Waste proportion
    observations.append(
        f"Combined waste (NVA cycle time + wait + rework) represents "
        f"{waste_pct_of_lead_time:.1f}% of total lead time. "
        "Lean transformation efforts should prioritise the largest waste categories first."
    )

    # ------------------------------------------------------------------
    # 7.  Recommendations
    # ------------------------------------------------------------------
    recommendations: List[str] = []

    # Bottleneck-specific
    if bottleneck_utilisation_pct >= 100.0:
        recommendations.append(
            f"Immediately relieve the bottleneck at '{bottleneck_step}': evaluate overtime, "
            "cross-training additional operators, splitting the step, or investing in faster "
            "equipment. Every minute of bottleneck uptime gained translates directly to "
            "throughput."
        )
    elif bottleneck_utilisation_pct >= 85.0:
        recommendations.append(
            f"Protect '{bottleneck_step}' from unplanned stoppages with a small buffer stock "
            "upstream and a Total Productive Maintenance (TPM) programme. Aim to bring "
            "effective utilisation below 85% to absorb demand spikes."
        )

    # PCE / wait time
    if wait_proportion > 50.0:
        recommendations.append(
            "Implement pull-based scheduling (kanban or CONWIP) to reduce inter-step queues. "
            "Target the longest individual wait time first for a rapid-cycle kaizen event. "
            "Reducing batch sizes will also directly cut queue-driven wait times."
        )
    else:
        recommendations.append(
            "Conduct a waste-walk workshop to categorise and quantify each wait segment. "
            "Even modest queue reductions will meaningfully improve PCE and customer "
            "responsiveness."
        )

    # NVA steps
    nva_steps = [s.name for s in steps if not s.is_value_added]
    if nva_steps:
        recommendations.append(
            f"Challenge the necessity of non-value-added steps: {', '.join(nva_steps)}. "
            "Apply the '5 Why' technique to determine whether each can be eliminated, "
            "combined, or replaced by error-proofing (poka-yoke) upstream."
        )

    # Defect / rework
    high_defect_steps = [s.name for s in steps if s.defect_rate_pct > 3.0]
    if high_defect_steps:
        recommendations.append(
            f"Prioritise defect reduction at {', '.join(high_defect_steps)} (defect rate > 3%). "
            "Use DMAIC or a focused kaizen to identify root causes. Reducing defects lowers "
            "rework load and protects the bottleneck from hidden capacity loss."
        )

    return LeanFlowResult(
        takt_time_min=round(takt_time_min, 4),
        total_demand_per_day=round(demand_per_day, 2),
        available_time_min=round(available_time_min, 2),
        total_cycle_time_min=round(total_cycle_time_min, 4),
        total_wait_time_min=round(total_wait_time_min, 4),
        total_lead_time_min=round(total_lead_time_min, 4),
        process_cycle_efficiency_pct=round(process_cycle_efficiency_pct, 4),
        throughput_units_per_hour=round(throughput_units_per_hour, 4),
        avg_wip_units=round(avg_wip_units, 4),
        littles_law_lead_time_min=round(littles_law_lead_time_min, 4),
        bottleneck_step=bottleneck_step,
        bottleneck_ct_min=round(bottleneck_ct_min, 4),
        bottleneck_utilisation_pct=round(bottleneck_utilisation_pct, 2),
        total_defect_rework_time_min=round(total_defect_rework_time_min, 4),
        nva_time_min=round(nva_time_min, 4),
        va_time_min=round(va_time_min, 4),
        waste_pct_of_lead_time=round(waste_pct_of_lead_time, 2),
        step_analysis=step_analysis,
        observations=observations,
        recommendations=recommendations,
    )


# ---------------------------------------------------------------------------
# Chart: Value Stream Map (stacked horizontal bar)
# ---------------------------------------------------------------------------

def value_stream_chart(result: LeanFlowResult) -> alt.Chart:
    """
    Stacked horizontal bar chart visualising the value stream composition.

    Each step shows three segments:
        Value-added cycle time  — green  (#22C55E)
        NVA cycle time          — amber  (#F59E0B)
        Wait / queue time       — red    (#EF4444)

    A vertical rule marks takt time in dark navy (#1E1B4B).

    Parameters
    ----------
    result : LeanFlowResult
        Output from ``run_lean_flow_analysis``.

    Returns
    -------
    alt.Chart
    """
    if not result.step_analysis:
        return alt.Chart(pd.DataFrame()).mark_text().encode(
            text=alt.value("No step data available.")
        )

    # Build long-format DataFrame for stacking
    records = []
    for row in result.step_analysis:
        step = row["step"]
        ct   = row["cycle_time_min"]
        wait = row["wait_time_min"]
        is_va = row["is_value_added"]

        records.append(
            {"Step": step, "Segment": "VA Cycle Time" if is_va else "NVA Cycle Time",
             "Minutes": ct, "Sort": result.step_analysis.index(row)}
        )
        records.append(
            {"Step": step, "Segment": "Wait / Queue Time",
             "Minutes": wait, "Sort": result.step_analysis.index(row)}
        )

    df = pd.DataFrame(records)

    # Determine step order (top → bottom = first → last in process)
    step_order = [row["step"] for row in result.step_analysis]

    color_scale = alt.Scale(
        domain=["VA Cycle Time", "NVA Cycle Time", "Wait / Queue Time"],
        range=["#22C55E",       "#F59E0B",         "#EF4444"],
    )

    bars = (
        alt.Chart(df, title="Value Stream — Time Composition per Step")
        .mark_bar(height={"band": 0.6})
        .encode(
            y=alt.Y(
                "Step:N",
                sort=step_order,
                axis=alt.Axis(title=None, labelFontSize=12),
            ),
            x=alt.X(
                "Minutes:Q",
                stack="zero",
                axis=alt.Axis(title="Time (minutes)", labelFontSize=11),
            ),
            color=alt.Color(
                "Segment:N",
                scale=color_scale,
                legend=alt.Legend(title="Time Category", orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("Step:N"),
                alt.Tooltip("Segment:N"),
                alt.Tooltip("Minutes:Q", format=".1f", title="Minutes"),
            ],
            order=alt.Order("Segment:N", sort="descending"),
        )
        .properties(width=560, height=max(200, len(step_order) * 45))
    )

    # Takt time vertical rule
    takt_df = pd.DataFrame({"x": [result.takt_time_min], "label": ["Takt time"]})
    takt_rule = (
        alt.Chart(takt_df)
        .mark_rule(color="#1E1B4B", strokeWidth=2.5, strokeDash=[6, 3])
        .encode(x=alt.X("x:Q"))
    )
    takt_text = (
        alt.Chart(takt_df)
        .mark_text(
            align="left", dx=5, dy=-8, color="#1E1B4B",
            fontSize=11, fontWeight="bold",
        )
        .encode(
            x=alt.X("x:Q"),
            y=alt.value(8),
            text=alt.Text("label:N"),
        )
    )

    return (
        alt.layer(bars, takt_rule, takt_text)
        .configure_view(stroke=None)
        .configure_axis(grid=True, gridColor="#EEEEEE")
    )


# ---------------------------------------------------------------------------
# Chart: Step Utilisation
# ---------------------------------------------------------------------------

def utilisation_chart(result: LeanFlowResult) -> alt.Chart:
    """
    Horizontal bar chart showing each step's utilisation relative to takt time.

    Colour coding:
        Red   (#EF4444) — utilisation > 90%  (at or over capacity)
        Amber (#F59E0B) — utilisation 70–90% (caution zone)
        Green (#22C55E) — utilisation < 70%  (healthy headroom)

    Reference lines:
        85%  — Target utilisation (dashed dark-blue)
        100% — Overload threshold (solid red)

    Parameters
    ----------
    result : LeanFlowResult

    Returns
    -------
    alt.Chart
    """
    if not result.step_analysis:
        return alt.Chart(pd.DataFrame()).mark_text().encode(
            text=alt.value("No step data available.")
        )

    records = []
    for row in result.step_analysis:
        util = row["utilisation_pct"]
        if util > 90.0:
            colour_band = "Over capacity (>90%)"
        elif util >= 70.0:
            colour_band = "Caution (70–90%)"
        else:
            colour_band = "Healthy (<70%)"
        records.append(
            {
                "Step":          row["step"],
                "Utilisation %": util,
                "Band":          colour_band,
                "Is Bottleneck": row["is_bottleneck"],
            }
        )

    df = pd.DataFrame(records)
    step_order = [row["step"] for row in result.step_analysis]

    color_scale = alt.Scale(
        domain=["Over capacity (>90%)", "Caution (70–90%)", "Healthy (<70%)"],
        range=["#EF4444",               "#F59E0B",           "#22C55E"],
    )

    bars = (
        alt.Chart(df, title="Step Utilisation vs Takt Time")
        .mark_bar(height={"band": 0.6})
        .encode(
            y=alt.Y(
                "Step:N",
                sort=step_order,
                axis=alt.Axis(title=None, labelFontSize=12),
            ),
            x=alt.X(
                "Utilisation %:Q",
                axis=alt.Axis(title="Utilisation (%)", labelFontSize=11),
                scale=alt.Scale(domain=[0, max(110.0, df["Utilisation %"].max() + 10)]),
            ),
            color=alt.Color(
                "Band:N",
                scale=color_scale,
                legend=alt.Legend(title="Capacity Band", orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("Step:N"),
                alt.Tooltip("Utilisation %:Q", format=".1f"),
                alt.Tooltip("Band:N"),
                alt.Tooltip("Is Bottleneck:N"),
            ],
        )
        .properties(width=500, height=max(200, len(step_order) * 45))
    )

    # Target line at 85%
    target_df = pd.DataFrame({"x": [85.0], "label": ["Target (85%)"]})
    target_rule = (
        alt.Chart(target_df)
        .mark_rule(color="#1E1B4B", strokeWidth=1.8, strokeDash=[6, 3])
        .encode(x=alt.X("x:Q"))
    )
    target_text = (
        alt.Chart(target_df)
        .mark_text(align="left", dx=4, dy=-8, color="#1E1B4B", fontSize=10)
        .encode(
            x=alt.X("x:Q"),
            y=alt.value(8),
            text=alt.Text("label:N"),
        )
    )

    # Overload line at 100%
    overload_df = pd.DataFrame({"x": [100.0], "label": ["Overload (100%)"]})
    overload_rule = (
        alt.Chart(overload_df)
        .mark_rule(color="#EF4444", strokeWidth=2.0)
        .encode(x=alt.X("x:Q"))
    )
    overload_text = (
        alt.Chart(overload_df)
        .mark_text(align="left", dx=4, dy=-8, color="#EF4444", fontSize=10)
        .encode(
            x=alt.X("x:Q"),
            y=alt.value(8),
            text=alt.Text("label:N"),
        )
    )

    return (
        alt.layer(bars, target_rule, target_text, overload_rule, overload_text)
        .configure_view(stroke=None)
        .configure_axis(grid=True, gridColor="#EEEEEE")
    )


# ---------------------------------------------------------------------------
# Scorecard: PCE Gauge HTML
# ---------------------------------------------------------------------------

def pce_gauge_html(pce_pct: float) -> str:
    """
    Return an HTML string containing a colour-coded PCE scorecard / gauge.

    Thresholds:
        Poor     — PCE < 5%   (red background)
        Typical  — PCE 5–25%  (amber background)
        Good     — PCE > 25%  (green background)

    Parameters
    ----------
    pce_pct : float
        Process Cycle Efficiency as a percentage (0–100).

    Returns
    -------
    str
        Self-contained HTML div suitable for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    if pce_pct < 5.0:
        label     = "Poor"
        bg_color  = "#FEE2E2"   # red-100
        text_color = "#991B1B"  # red-800
        bar_color = "#EF4444"
        explanation = (
            "PCE below 5% indicates severe waste. The vast majority of elapsed time adds "
            "no customer value. Urgent lean intervention is required — focus on eliminating "
            "the largest queue and wait segments."
        )
    elif pce_pct <= 25.0:
        label     = "Typical"
        bg_color  = "#FEF9C3"   # yellow-100
        text_color = "#92400E"  # amber-800
        bar_color = "#F59E0B"
        explanation = (
            "PCE in the 5–25% range is typical for manufacturing and transactional "
            "processes. There is clear opportunity to improve, and a systematic kaizen "
            "programme can deliver meaningful gains."
        )
    else:
        label     = "Good"
        bg_color  = "#DCFCE7"   # green-100
        text_color = "#166534"  # green-800
        bar_color = "#22C55E"
        explanation = (
            "PCE above 25% is considered good. The value stream is relatively lean. "
            "Focus on sustaining current performance, preventing backsliding, and "
            "seeking incremental improvements through continuous improvement."
        )

    bar_width = min(pce_pct, 100.0)

    html = f"""
<div style="
    background-color: {bg_color};
    border-left: 6px solid {bar_color};
    border-radius: 8px;
    padding: 20px 24px;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    max-width: 520px;
">
    <div style="display: flex; align-items: baseline; gap: 12px; margin-bottom: 6px;">
        <span style="font-size: 2.8rem; font-weight: 700; color: {text_color}; line-height: 1;">
            {pce_pct:.1f}%
        </span>
        <span style="
            font-size: 0.9rem; font-weight: 600; letter-spacing: 0.05em;
            color: {text_color}; text-transform: uppercase;
        ">
            {label}
        </span>
    </div>
    <div style="font-size: 0.85rem; font-weight: 600; color: {text_color}; margin-bottom: 8px;">
        Process Cycle Efficiency (PCE)
    </div>
    <!-- Progress bar -->
    <div style="
        background-color: rgba(0,0,0,0.08);
        border-radius: 999px;
        height: 10px;
        margin-bottom: 14px;
        overflow: hidden;
    ">
        <div style="
            width: {bar_width:.1f}%;
            height: 100%;
            background-color: {bar_color};
            border-radius: 999px;
        "></div>
    </div>
    <!-- Scale labels -->
    <div style="
        display: flex; justify-content: space-between;
        font-size: 0.72rem; color: {text_color}; opacity: 0.75;
        margin-bottom: 12px;
    ">
        <span>0% — Poor</span><span>5%</span><span>25%</span><span>100% — World-class</span>
    </div>
    <p style="font-size: 0.82rem; color: {text_color}; margin: 0; line-height: 1.5;">
        {explanation}
    </p>
</div>
"""
    return html


# ---------------------------------------------------------------------------
# Chart: Waste Waterfall (lead time composition)
# ---------------------------------------------------------------------------

def waste_waterfall_chart(result: LeanFlowResult) -> alt.Chart:
    """
    Horizontal waterfall-style bar chart showing the composition of total lead time.

    Segments (in order):
        VA Cycle Time    — green  (#22C55E)
        NVA Cycle Time   — amber  (#F59E0B)
        Wait / Queue     — red    (#EF4444)
        Defect Rework    — pink   (#EC4899)

    Parameters
    ----------
    result : LeanFlowResult

    Returns
    -------
    alt.Chart
    """
    nva_cycle_time = result.nva_time_min - result.total_wait_time_min

    segments = [
        {"Segment": "VA Cycle Time",   "Minutes": result.va_time_min,                  "Color": "#22C55E"},
        {"Segment": "NVA Cycle Time",  "Minutes": max(nva_cycle_time, 0.0),            "Color": "#F59E0B"},
        {"Segment": "Wait / Queue",    "Minutes": result.total_wait_time_min,           "Color": "#EF4444"},
        {"Segment": "Defect Rework",   "Minutes": result.total_defect_rework_time_min,  "Color": "#EC4899"},
    ]

    # Filter out zero-value segments to keep the chart clean
    segments = [s for s in segments if s["Minutes"] > 0]

    df = pd.DataFrame(segments)
    total = result.total_lead_time_min if result.total_lead_time_min > 0 else 1.0
    df["Pct of Lead Time"] = df["Minutes"] / total * 100.0

    # Segment display order
    seg_order = [s["Segment"] for s in segments]

    color_scale = alt.Scale(
        domain=[s["Segment"] for s in segments],
        range=[s["Color"]    for s in segments],
    )

    bars = (
        alt.Chart(df, title="Lead Time Composition — Waste Waterfall")
        .mark_bar(height={"band": 0.65}, cornerRadiusBottomRight=4, cornerRadiusTopRight=4)
        .encode(
            y=alt.Y(
                "Segment:N",
                sort=seg_order,
                axis=alt.Axis(title=None, labelFontSize=12),
            ),
            x=alt.X(
                "Minutes:Q",
                axis=alt.Axis(title="Time (minutes)", labelFontSize=11),
            ),
            color=alt.Color(
                "Segment:N",
                scale=color_scale,
                legend=alt.Legend(title="Segment", orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("Segment:N"),
                alt.Tooltip("Minutes:Q",           format=".1f", title="Minutes"),
                alt.Tooltip("Pct of Lead Time:Q",  format=".1f", title="% of Lead Time"),
            ],
        )
        .properties(width=500, height=max(180, len(segments) * 55))
    )

    # Value labels
    text_layer = (
        alt.Chart(df)
        .mark_text(align="left", dx=6, fontSize=11, color="#374151")
        .encode(
            y=alt.Y("Segment:N", sort=seg_order),
            x=alt.X("Minutes:Q"),
            text=alt.Text("Minutes:Q", format=".1f"),
        )
    )

    # Total lead time reference line
    total_df = pd.DataFrame(
        {"x": [result.total_lead_time_min], "label": [f"Total LT: {result.total_lead_time_min:.0f} min"]}
    )
    total_rule = (
        alt.Chart(total_df)
        .mark_rule(color="#6B7280", strokeWidth=1.5, strokeDash=[4, 3])
        .encode(x=alt.X("x:Q"))
    )
    total_text = (
        alt.Chart(total_df)
        .mark_text(align="left", dx=5, dy=-8, color="#6B7280", fontSize=10)
        .encode(
            x=alt.X("x:Q"),
            y=alt.value(8),
            text=alt.Text("label:N"),
        )
    )

    return (
        alt.layer(bars, text_layer, total_rule, total_text)
        .configure_view(stroke=None)
        .configure_axis(grid=True, gridColor="#EEEEEE")
    )
