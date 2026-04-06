"""
spc.py
======
Statistical Process Control (SPC) module for the Lean Six Sigma Black Belt analytics system.

Implements I-MR charts (Individuals and Moving Range), Xbar-R charts, and p-charts with
variable control limits.  Each function returns a populated SPCResult dataclass and a
layered Altair chart ready for display in Streamlit or Jupyter.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import altair as alt
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# SPC constants table  (subgroup size → {A2, D3, D4, d2})
# ---------------------------------------------------------------------------

_CONTROL_CONSTANTS: dict[int, dict[str, float]] = {
    2: {"A2": 1.880, "D3": 0.000, "D4": 3.267, "d2": 1.128},
    3: {"A2": 1.023, "D3": 0.000, "D4": 2.574, "d2": 1.693},
    4: {"A2": 0.729, "D3": 0.000, "D4": 2.282, "d2": 2.059},
    5: {"A2": 0.577, "D3": 0.000, "D4": 2.114, "d2": 2.326},
    6: {"A2": 0.483, "D3": 0.000, "D4": 2.004, "d2": 2.534},
    7: {"A2": 0.419, "D3": 0.076, "D4": 1.924, "d2": 2.704},
    8: {"A2": 0.373, "D3": 0.136, "D4": 1.864, "d2": 2.847},
}

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

_COL_LINE = "#4361EE"          # data line / bars
_COL_OOC = "#EF233C"           # out-of-control points
_COL_UCL = "#EF233C"           # UCL / LCL (red dashed)
_COL_CL = "#888888"            # centreline (grey)
_COL_BAND = "#FFE5E8"          # p-chart variable-limit band fill


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class SPCResult:
    """
    Container for SPC chart calculations and control-status signals.

    Attributes
    ----------
    chart_type : str
        Name of the chart: "I-MR", "Xbar-R", or "p-chart".
    centerline : float
        Primary chart centreline (process mean or p_bar).
    ucl : float
        Primary chart upper control limit.
    lcl : float
        Primary chart lower control limit.
    secondary_centerline : float | None
        Centreline for the secondary chart panel (MR_bar or R_bar), or None.
    secondary_ucl : float | None
        UCL for the secondary chart panel, or None.
    secondary_lcl : float | None
        LCL for the secondary chart panel, or None.
    ooc_points : list[int]
        Zero-based indices of points that violated at least one control rule.
    signals : list[str]
        Plain-English description of each OOC signal detected.
    is_in_control : bool
        True when no OOC signals were found.
    interpretation : str
        Plain-English summary of process stability.
    recommended_action : str
        Specific next step for the process owner.
    """

    chart_type: str
    centerline: float
    ucl: float
    lcl: float
    secondary_centerline: Optional[float]
    secondary_ucl: Optional[float]
    secondary_lcl: Optional[float]
    ooc_points: list[int]
    signals: list[str]
    is_in_control: bool
    interpretation: str
    recommended_action: str


# ---------------------------------------------------------------------------
# Run-rule detection helpers
# ---------------------------------------------------------------------------

def _rule1_ooc(values: list[float], ucl: float, lcl: float) -> list[int]:
    """Rule 1: 1 point beyond 3-sigma limits."""
    return [i for i, v in enumerate(values) if v > ucl or v < lcl]


def _rule2_run(values: list[float], centerline: float, run_length: int = 8) -> list[int]:
    """
    Rule 2: `run_length` or more consecutive points on the same side of the centreline.
    Returns the index of the LAST point in each qualifying run (flagging the event).
    """
    signals: list[int] = []
    n = len(values)
    i = 0
    while i < n:
        side = values[i] > centerline  # True = above, False = below
        j = i
        while j < n and (values[j] > centerline) == side:
            j += 1
        run = j - i
        if run >= run_length:
            # flag the last index of the run
            signals.append(j - 1)
        i = j
    return signals


def _rule3_trend(values: list[float], consecutive: int = 6) -> list[int]:
    """
    Rule 3: `consecutive` or more points in a strict monotonic sequence (up or down).
    Returns the index of the LAST point in each qualifying trend.
    """
    signals: list[int] = []
    n = len(values)
    if n < 2:
        return signals
    diffs = [values[k + 1] - values[k] for k in range(n - 1)]
    i = 0
    while i < len(diffs):
        direction = diffs[i] > 0  # True = up
        j = i
        while j < len(diffs) and diffs[j] != 0 and (diffs[j] > 0) == direction:
            j += 1
        run_points = j - i + 1  # number of original points in the monotonic run
        if run_points >= consecutive:
            signals.append(i + run_points - 1)
        i = j if j > i else i + 1
    return signals


def _collect_ooc(
    values: list[float],
    ucl: float,
    lcl: float,
    centerline: float,
) -> tuple[list[int], list[str]]:
    """
    Apply rules 1–3 to a list of values and return (ooc_indices, signal_descriptions).
    Indices are deduplicated while preserving order.
    """
    signals: list[str] = []
    ooc_set: dict[int, None] = {}  # ordered set

    r1 = _rule1_ooc(values, ucl, lcl)
    for idx in r1:
        if idx not in ooc_set:
            ooc_set[idx] = None
        signals.append(
            f"Rule 1 — Point {idx + 1} ({values[idx]:.4g}) is beyond the 3\u03c3 control limit "
            f"(UCL={ucl:.4g}, LCL={lcl:.4g})."
        )

    r2 = _rule2_run(values, centerline)
    for idx in r2:
        if idx not in ooc_set:
            ooc_set[idx] = None
        signals.append(
            f"Rule 2 — Run of \u22658 consecutive points on the same side of the centreline "
            f"ending at point {idx + 1} ({values[idx]:.4g})."
        )

    r3 = _rule3_trend(values)
    for idx in r3:
        if idx not in ooc_set:
            ooc_set[idx] = None
        signals.append(
            f"Rule 3 — Trend of \u22656 consecutive points in one direction "
            f"ending at point {idx + 1} ({values[idx]:.4g})."
        )

    return list(ooc_set.keys()), signals


def _build_spc_interpretation(
    chart_type: str,
    is_in_control: bool,
    n_ooc: int,
    n_total: int,
) -> str:
    """Build a plain-English stability interpretation."""
    if is_in_control:
        return (
            f"The {chart_type} chart shows the process is in statistical control. "
            f"All {n_total} points fall within the control limits and no run rules were violated. "
            "The process is exhibiting only common-cause variation."
        )
    pct = 100 * n_ooc / n_total
    return (
        f"The {chart_type} chart indicates the process is OUT OF CONTROL. "
        f"{n_ooc} of {n_total} points ({pct:.1f}%) triggered one or more control signals. "
        "Special-cause variation is present and should be investigated immediately."
    )


def _build_spc_action(is_in_control: bool, chart_type: str) -> str:
    """Return a specific recommended action."""
    if is_in_control:
        return (
            "Continue routine monitoring. Consider conducting a process capability study "
            "(Cp/Cpk) now that statistical control has been confirmed. Review the control "
            "chart at least once per shift to detect future special causes early."
        )
    return (
        "Immediately investigate the out-of-control signals using the '5 Whys' or Fishbone "
        "technique. For each special-cause event, document the likely assignable cause on the "
        f"control chart and remove those subgroups before recalculating the {chart_type} "
        "control limits for ongoing monitoring."
    )


# ---------------------------------------------------------------------------
# I-MR chart
# ---------------------------------------------------------------------------

def imr_chart(data: list[float]) -> tuple[SPCResult, alt.Chart]:
    """
    Compute an Individuals and Moving Range (I-MR) chart.

    Parameters
    ----------
    data : list[float]
        Individual measurement values in time order.  Minimum 4 points.

    Returns
    -------
    tuple[SPCResult, alt.Chart]
        Populated SPCResult and a layered dual-panel Altair chart.

    Raises
    ------
    ValueError
        If fewer than 4 data points are supplied.
    """
    if len(data) < 4:
        raise ValueError("I-MR chart requires at least 4 data points.")

    arr = np.asarray(data, dtype=float)
    n = len(arr)

    # ---- Control limit calculations -------------------------------------
    x_bar = float(np.mean(arr))
    moving_ranges = np.abs(np.diff(arr))
    mr_bar = float(np.mean(moving_ranges))

    # I chart limits  (d2=1.128, E2=2.66 = 3/d2)
    e2 = 3.0 / 1.128  # ≈ 2.659574
    ucl_i = x_bar + e2 * mr_bar
    lcl_i = x_bar - e2 * mr_bar

    # MR chart limits  (D4=3.267 for n=2, D3=0)
    ucl_mr = 3.267 * mr_bar
    lcl_mr = 0.0

    # ---- Out-of-control detection ---------------------------------------
    individuals = arr.tolist()
    ooc_idx, signals = _collect_ooc(individuals, ucl_i, lcl_i, x_bar)

    # Also check MR chart for rule 1 only
    mr_list = moving_ranges.tolist()
    mr_ooc_r1 = _rule1_ooc(mr_list, ucl_mr, lcl_mr)
    for idx in mr_ooc_r1:
        mr_pt_idx = idx + 1  # MR(i) corresponds to original point i+1
        if mr_pt_idx not in ooc_idx:
            ooc_idx.append(mr_pt_idx)
        signals.append(
            f"MR Rule 1 — Moving range at position {idx + 1} ({mr_list[idx]:.4g}) "
            f"exceeds UCL_MR ({ucl_mr:.4g})."
        )

    ooc_idx = sorted(set(ooc_idx))
    is_in_control = len(ooc_idx) == 0

    interpretation = _build_spc_interpretation("I-MR", is_in_control, len(ooc_idx), n)
    recommended_action = _build_spc_action(is_in_control, "I-MR")

    result = SPCResult(
        chart_type="I-MR",
        centerline=x_bar,
        ucl=ucl_i,
        lcl=lcl_i,
        secondary_centerline=mr_bar,
        secondary_ucl=ucl_mr,
        secondary_lcl=lcl_mr,
        ooc_points=ooc_idx,
        signals=signals,
        is_in_control=is_in_control,
        interpretation=interpretation,
        recommended_action=recommended_action,
    )

    # ---- Build Altair chart ---------------------------------------------
    chart = _build_imr_chart(
        individuals=individuals,
        mr_list=mr_list,
        x_bar=x_bar,
        ucl_i=ucl_i,
        lcl_i=lcl_i,
        mr_bar=mr_bar,
        ucl_mr=ucl_mr,
        lcl_mr=lcl_mr,
        ooc_idx=ooc_idx,
    )

    return result, chart


def _build_imr_chart(
    individuals: list[float],
    mr_list: list[float],
    x_bar: float,
    ucl_i: float,
    lcl_i: float,
    mr_bar: float,
    ucl_mr: float,
    lcl_mr: float,
    ooc_idx: list[int],
) -> alt.Chart:
    """Construct the layered dual-panel I-MR Altair chart."""

    n = len(individuals)

    # --- Individuals panel -----------------------------------------------
    df_i = pd.DataFrame({
        "Index": list(range(1, n + 1)),
        "Value": individuals,
        "UCL": [ucl_i] * n,
        "LCL": [lcl_i] * n,
        "CL": [x_bar] * n,
        "OOC": ["OOC" if i in ooc_idx else "In Control" for i in range(n)],
        "Status": [
            "ABOVE UCL" if v > ucl_i else ("BELOW LCL" if v < lcl_i else "OK")
            for v in individuals
        ],
    })

    i_line = (
        alt.Chart(df_i)
        .mark_line(color=_COL_LINE, strokeWidth=1.5)
        .encode(
            x=alt.X("Index:Q", title="Subgroup / Observation"),
            y=alt.Y("Value:Q", title="Individual Value"),
            tooltip=[
                alt.Tooltip("Index:Q", title="Point"),
                alt.Tooltip("Value:Q", format=".4f", title="Value"),
                alt.Tooltip("UCL:Q", format=".4f"),
                alt.Tooltip("LCL:Q", format=".4f"),
                alt.Tooltip("Status:N"),
            ],
        )
    )

    i_dots_all = (
        alt.Chart(df_i)
        .mark_circle(size=45, opacity=0.7)
        .encode(
            x=alt.X("Index:Q"),
            y=alt.Y("Value:Q"),
            color=alt.Color(
                "OOC:N",
                scale=alt.Scale(domain=["In Control", "OOC"], range=[_COL_LINE, _COL_OOC]),
                legend=alt.Legend(title="Status"),
            ),
            tooltip=[
                alt.Tooltip("Index:Q", title="Point"),
                alt.Tooltip("Value:Q", format=".4f"),
                alt.Tooltip("OOC:N", title="Control Status"),
            ],
        )
    )

    i_ucl = _hline(ucl_i, _COL_UCL, [6, 4], f"UCL = {ucl_i:.4g}")
    i_lcl = _hline(lcl_i, _COL_UCL, [6, 4], f"LCL = {lcl_i:.4g}")
    i_cl = _hline(x_bar, _COL_CL, [], f"CL = {x_bar:.4g}")

    panel_i = (
        alt.layer(i_line, i_dots_all, i_ucl, i_lcl, i_cl)
        .properties(
            title=alt.TitleParams(
                text="Individuals Chart (I)",
                subtitle=f"CL = {x_bar:.4g}  |  UCL = {ucl_i:.4g}  |  LCL = {lcl_i:.4g}",
                fontSize=13, subtitleFontSize=10, subtitleColor="#555",
            ),
            height=260,
            width="container",
        )
    )

    # --- Moving Range panel ----------------------------------------------
    n_mr = len(mr_list)
    mr_ooc_set = {idx + 1 for idx in range(n_mr) if mr_list[idx] > ucl_mr}  # original indices

    df_mr = pd.DataFrame({
        "Index": list(range(2, n_mr + 2)),  # MR(i) plotted at position i+1
        "MR": mr_list,
        "UCL_MR": [ucl_mr] * n_mr,
        "LCL_MR": [lcl_mr] * n_mr,
        "MR_bar": [mr_bar] * n_mr,
        "OOC": ["OOC" if (i + 1) in mr_ooc_set else "In Control" for i in range(n_mr)],
        "Status": ["ABOVE UCL" if v > ucl_mr else "OK" for v in mr_list],
    })

    mr_line = (
        alt.Chart(df_mr)
        .mark_line(color=_COL_LINE, strokeWidth=1.5)
        .encode(
            x=alt.X("Index:Q", title="Observation"),
            y=alt.Y("MR:Q", title="Moving Range"),
            tooltip=[
                alt.Tooltip("Index:Q", title="Point"),
                alt.Tooltip("MR:Q", format=".4f", title="MR"),
                alt.Tooltip("UCL_MR:Q", format=".4f", title="UCL"),
                alt.Tooltip("Status:N"),
            ],
        )
    )

    mr_dots = (
        alt.Chart(df_mr)
        .mark_circle(size=45, opacity=0.7)
        .encode(
            x=alt.X("Index:Q"),
            y=alt.Y("MR:Q"),
            color=alt.Color(
                "OOC:N",
                scale=alt.Scale(domain=["In Control", "OOC"], range=[_COL_LINE, _COL_OOC]),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Index:Q", title="Point"),
                alt.Tooltip("MR:Q", format=".4f"),
                alt.Tooltip("OOC:N"),
            ],
        )
    )

    mr_ucl_rule = _hline(ucl_mr, _COL_UCL, [6, 4], f"UCL_MR = {ucl_mr:.4g}")
    mr_cl_rule = _hline(mr_bar, _COL_CL, [], f"MR_bar = {mr_bar:.4g}")

    panel_mr = (
        alt.layer(mr_line, mr_dots, mr_ucl_rule, mr_cl_rule)
        .properties(
            title=alt.TitleParams(
                text="Moving Range Chart (MR)",
                subtitle=f"MR\u0305 = {mr_bar:.4g}  |  UCL = {ucl_mr:.4g}  |  LCL = 0",
                fontSize=13, subtitleFontSize=10, subtitleColor="#555",
            ),
            height=260,
            width="container",
        )
    )

    combined = (
        alt.vconcat(panel_i, panel_mr)
        .properties(title=alt.TitleParams(text="I-MR Control Chart", fontSize=16))
        .configure_axis(grid=False, labelFontSize=11, titleFontSize=12)
        .configure_view(strokeWidth=0)
    )

    return combined


# ---------------------------------------------------------------------------
# Xbar-R chart
# ---------------------------------------------------------------------------

def xbar_r_chart(data: list[list[float]]) -> tuple[SPCResult, alt.Chart]:
    """
    Compute an Xbar-R (Mean and Range) control chart for subgrouped data.

    Parameters
    ----------
    data : list[list[float]]
        List of subgroups; each subgroup is a list of individual measurements.
        All subgroups must have the same size (2–8 measurements).

    Returns
    -------
    tuple[SPCResult, alt.Chart]
        Populated SPCResult and a layered dual-panel Altair chart.

    Raises
    ------
    ValueError
        If fewer than 4 subgroups are provided, subgroup sizes are inconsistent,
        or the subgroup size is not in the supported range (2–8).
    """
    if len(data) < 4:
        raise ValueError("Xbar-R chart requires at least 4 subgroups.")

    subgroup_sizes = [len(sg) for sg in data]
    if len(set(subgroup_sizes)) != 1:
        raise ValueError(
            "All subgroups must have the same number of measurements for an Xbar-R chart. "
            "For variable subgroup sizes consider an Xbar-S chart."
        )

    n_sub = subgroup_sizes[0]
    if n_sub not in _CONTROL_CONSTANTS:
        raise ValueError(
            f"Subgroup size {n_sub} is not supported. Supported sizes: "
            f"{sorted(_CONTROL_CONSTANTS.keys())}."
        )

    constants = _CONTROL_CONSTANTS[n_sub]
    A2 = constants["A2"]
    D3 = constants["D3"]
    D4 = constants["D4"]

    # ---- Compute subgroup statistics ------------------------------------
    subgroup_means: list[float] = []
    subgroup_ranges: list[float] = []
    for sg in data:
        arr_sg = np.asarray(sg, dtype=float)
        subgroup_means.append(float(np.mean(arr_sg)))
        subgroup_ranges.append(float(np.max(arr_sg) - np.min(arr_sg)))

    x_dbar = float(np.mean(subgroup_means))
    r_bar = float(np.mean(subgroup_ranges))

    # ---- Control limits -------------------------------------------------
    ucl_x = x_dbar + A2 * r_bar
    lcl_x = x_dbar - A2 * r_bar

    ucl_r = D4 * r_bar
    lcl_r = D3 * r_bar

    # ---- OOC detection --------------------------------------------------
    ooc_x_idx, signals_x = _collect_ooc(subgroup_means, ucl_x, lcl_x, x_dbar)
    ooc_r_r1 = _rule1_ooc(subgroup_ranges, ucl_r, lcl_r)
    signals_r: list[str] = []
    for idx in ooc_r_r1:
        signals_r.append(
            f"R-chart Rule 1 — Subgroup {idx + 1} range ({subgroup_ranges[idx]:.4g}) "
            f"is beyond control limit (UCL_R={ucl_r:.4g}, LCL_R={lcl_r:.4g})."
        )

    all_signals = signals_x + signals_r
    all_ooc = sorted(set(ooc_x_idx + ooc_r_r1))
    is_in_control = len(all_ooc) == 0
    k = len(data)

    interpretation = _build_spc_interpretation("Xbar-R", is_in_control, len(all_ooc), k)
    recommended_action = _build_spc_action(is_in_control, "Xbar-R")

    result = SPCResult(
        chart_type="Xbar-R",
        centerline=x_dbar,
        ucl=ucl_x,
        lcl=lcl_x,
        secondary_centerline=r_bar,
        secondary_ucl=ucl_r,
        secondary_lcl=lcl_r,
        ooc_points=all_ooc,
        signals=all_signals,
        is_in_control=is_in_control,
        interpretation=interpretation,
        recommended_action=recommended_action,
    )

    chart = _build_xbar_r_chart(
        subgroup_means=subgroup_means,
        subgroup_ranges=subgroup_ranges,
        x_dbar=x_dbar,
        ucl_x=ucl_x,
        lcl_x=lcl_x,
        r_bar=r_bar,
        ucl_r=ucl_r,
        lcl_r=lcl_r,
        ooc_x_idx=ooc_x_idx,
        ooc_r_idx=ooc_r_r1,
    )

    return result, chart


def _build_xbar_r_chart(
    subgroup_means: list[float],
    subgroup_ranges: list[float],
    x_dbar: float,
    ucl_x: float,
    lcl_x: float,
    r_bar: float,
    ucl_r: float,
    lcl_r: float,
    ooc_x_idx: list[int],
    ooc_r_idx: list[int],
) -> alt.Chart:
    """Build the layered dual-panel Xbar-R Altair chart."""

    k = len(subgroup_means)
    ooc_x_set = set(ooc_x_idx)
    ooc_r_set = set(ooc_r_idx)

    # ---- Xbar panel -----------------------------------------------------
    df_x = pd.DataFrame({
        "Subgroup": list(range(1, k + 1)),
        "Mean": subgroup_means,
        "UCL": [ucl_x] * k,
        "LCL": [lcl_x] * k,
        "CL": [x_dbar] * k,
        "OOC": ["OOC" if i in ooc_x_set else "In Control" for i in range(k)],
        "Status": [
            "ABOVE UCL" if v > ucl_x else ("BELOW LCL" if v < lcl_x else "OK")
            for v in subgroup_means
        ],
    })

    x_line = (
        alt.Chart(df_x)
        .mark_line(color=_COL_LINE, strokeWidth=1.5)
        .encode(
            x=alt.X("Subgroup:Q", title="Subgroup"),
            y=alt.Y("Mean:Q", title="Subgroup Mean"),
            tooltip=[
                alt.Tooltip("Subgroup:Q"),
                alt.Tooltip("Mean:Q", format=".4f"),
                alt.Tooltip("UCL:Q", format=".4f"),
                alt.Tooltip("LCL:Q", format=".4f"),
                alt.Tooltip("Status:N"),
            ],
        )
    )

    x_dots = (
        alt.Chart(df_x)
        .mark_circle(size=50, opacity=0.75)
        .encode(
            x=alt.X("Subgroup:Q"),
            y=alt.Y("Mean:Q"),
            color=alt.Color(
                "OOC:N",
                scale=alt.Scale(domain=["In Control", "OOC"], range=[_COL_LINE, _COL_OOC]),
                legend=alt.Legend(title="Status"),
            ),
            tooltip=[
                alt.Tooltip("Subgroup:Q"),
                alt.Tooltip("Mean:Q", format=".4f"),
                alt.Tooltip("OOC:N", title="Control Status"),
            ],
        )
    )

    x_ucl = _hline(ucl_x, _COL_UCL, [6, 4], f"UCL = {ucl_x:.4g}")
    x_lcl = _hline(lcl_x, _COL_UCL, [6, 4], f"LCL = {lcl_x:.4g}")
    x_cl = _hline(x_dbar, _COL_CL, [], f"X\u0305\u0305 = {x_dbar:.4g}")

    panel_x = (
        alt.layer(x_line, x_dots, x_ucl, x_lcl, x_cl)
        .properties(
            title=alt.TitleParams(
                text="X\u0305bar Chart",
                subtitle=f"X\u0305\u0305 = {x_dbar:.4g}  |  UCL = {ucl_x:.4g}  |  LCL = {lcl_x:.4g}",
                fontSize=13, subtitleFontSize=10, subtitleColor="#555",
            ),
            height=260,
            width="container",
        )
    )

    # ---- Range panel ----------------------------------------------------
    df_r = pd.DataFrame({
        "Subgroup": list(range(1, k + 1)),
        "Range": subgroup_ranges,
        "UCL_R": [ucl_r] * k,
        "LCL_R": [lcl_r] * k,
        "R_bar": [r_bar] * k,
        "OOC": ["OOC" if i in ooc_r_set else "In Control" for i in range(k)],
        "Status": [
            "ABOVE UCL" if v > ucl_r else ("BELOW LCL" if v < lcl_r else "OK")
            for v in subgroup_ranges
        ],
    })

    r_line = (
        alt.Chart(df_r)
        .mark_line(color=_COL_LINE, strokeWidth=1.5)
        .encode(
            x=alt.X("Subgroup:Q", title="Subgroup"),
            y=alt.Y("Range:Q", title="Subgroup Range"),
            tooltip=[
                alt.Tooltip("Subgroup:Q"),
                alt.Tooltip("Range:Q", format=".4f"),
                alt.Tooltip("UCL_R:Q", format=".4f", title="UCL"),
                alt.Tooltip("Status:N"),
            ],
        )
    )

    r_dots = (
        alt.Chart(df_r)
        .mark_circle(size=50, opacity=0.75)
        .encode(
            x=alt.X("Subgroup:Q"),
            y=alt.Y("Range:Q"),
            color=alt.Color(
                "OOC:N",
                scale=alt.Scale(domain=["In Control", "OOC"], range=[_COL_LINE, _COL_OOC]),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Subgroup:Q"),
                alt.Tooltip("Range:Q", format=".4f"),
                alt.Tooltip("OOC:N"),
            ],
        )
    )

    r_ucl = _hline(ucl_r, _COL_UCL, [6, 4], f"UCL_R = {ucl_r:.4g}")
    r_cl = _hline(r_bar, _COL_CL, [], f"R\u0305 = {r_bar:.4g}")

    panel_r = (
        alt.layer(r_line, r_dots, r_ucl, r_cl)
        .properties(
            title=alt.TitleParams(
                text="R Chart",
                subtitle=f"R\u0305 = {r_bar:.4g}  |  UCL = {ucl_r:.4g}  |  LCL = {lcl_r:.4g}",
                fontSize=13, subtitleFontSize=10, subtitleColor="#555",
            ),
            height=260,
            width="container",
        )
    )

    combined = (
        alt.vconcat(panel_x, panel_r)
        .properties(title=alt.TitleParams(text="Xbar-R Control Chart", fontSize=16))
        .configure_axis(grid=False, labelFontSize=11, titleFontSize=12)
        .configure_view(strokeWidth=0)
    )

    return combined


# ---------------------------------------------------------------------------
# p-chart (attribute chart with variable control limits)
# ---------------------------------------------------------------------------

def p_chart(
    defectives: list[int],
    sample_sizes: list[int],
) -> tuple[SPCResult, alt.Chart]:
    """
    Compute a p-chart for attribute (pass/fail) data with variable sample sizes.

    Parameters
    ----------
    defectives : list[int]
        Number of defective (non-conforming) units in each sample period.
    sample_sizes : list[int]
        Number of units inspected in each corresponding sample period.

    Returns
    -------
    tuple[SPCResult, alt.Chart]
        Populated SPCResult and an Altair chart with variable control limit bands.

    Raises
    ------
    ValueError
        If the lists have different lengths or fewer than 4 points are provided.
    """
    if len(defectives) != len(sample_sizes):
        raise ValueError("defectives and sample_sizes must have the same length.")
    if len(defectives) < 4:
        raise ValueError("p-chart requires at least 4 data points.")

    total_def = sum(defectives)
    total_n = sum(sample_sizes)
    p_bar = total_def / total_n

    n = len(defectives)
    proportions: list[float] = [d / ni for d, ni in zip(defectives, sample_sizes)]

    # Variable limits per point
    ucl_list: list[float] = []
    lcl_list: list[float] = []

    for ni in sample_sizes:
        sigma_i = math.sqrt(p_bar * (1.0 - p_bar) / ni)
        ucl_list.append(p_bar + 3.0 * sigma_i)
        lcl_list.append(max(0.0, p_bar - 3.0 * sigma_i))

    # ---- OOC detection --------------------------------------------------
    ooc_idx: list[int] = []
    signals: list[str] = []

    for i, (pi, ucl_i, lcl_i) in enumerate(zip(proportions, ucl_list, lcl_list)):
        if pi > ucl_i:
            ooc_idx.append(i)
            signals.append(
                f"Rule 1 — Point {i + 1}: proportion {pi:.4f} exceeds UCL {ucl_i:.4f} "
                f"(sample size = {sample_sizes[i]}, defectives = {defectives[i]})."
            )
        elif pi < lcl_i:
            ooc_idx.append(i)
            signals.append(
                f"Rule 1 — Point {i + 1}: proportion {pi:.4f} is below LCL {lcl_i:.4f} "
                f"(sample size = {sample_sizes[i]}, defectives = {defectives[i]})."
            )

    # Run-rule checks on proportions
    r2_idx = _rule2_run(proportions, p_bar)
    for idx in r2_idx:
        if idx not in ooc_idx:
            ooc_idx.append(idx)
        signals.append(
            f"Rule 2 — Run of \u22658 consecutive points on the same side of p\u0305 "
            f"ending at point {idx + 1} (p = {proportions[idx]:.4f})."
        )

    r3_idx = _rule3_trend(proportions)
    for idx in r3_idx:
        if idx not in ooc_idx:
            ooc_idx.append(idx)
        signals.append(
            f"Rule 3 — Trend of \u22656 consecutive points in one direction "
            f"ending at point {idx + 1} (p = {proportions[idx]:.4f})."
        )

    ooc_idx = sorted(set(ooc_idx))
    is_in_control = len(ooc_idx) == 0

    # Representative single UCL/LCL for SPCResult (use mean of variable limits)
    ucl_rep = float(np.mean(ucl_list))
    lcl_rep = float(np.mean(lcl_list))

    interpretation = _build_spc_interpretation("p-chart", is_in_control, len(ooc_idx), n)
    interpretation += (
        f" Overall p\u0305 = {p_bar:.4f} ({total_def} defectives in {total_n} inspected)."
    )
    recommended_action = _build_spc_action(is_in_control, "p-chart")

    result = SPCResult(
        chart_type="p-chart",
        centerline=p_bar,
        ucl=ucl_rep,
        lcl=lcl_rep,
        secondary_centerline=None,
        secondary_ucl=None,
        secondary_lcl=None,
        ooc_points=ooc_idx,
        signals=signals,
        is_in_control=is_in_control,
        interpretation=interpretation,
        recommended_action=recommended_action,
    )

    chart = _build_p_chart(
        proportions=proportions,
        ucl_list=ucl_list,
        lcl_list=lcl_list,
        p_bar=p_bar,
        ooc_idx=ooc_idx,
        defectives=defectives,
        sample_sizes=sample_sizes,
    )

    return result, chart


def _build_p_chart(
    proportions: list[float],
    ucl_list: list[float],
    lcl_list: list[float],
    p_bar: float,
    ooc_idx: list[int],
    defectives: list[int],
    sample_sizes: list[int],
) -> alt.Chart:
    """Build the p-chart Altair chart with variable limit bands."""

    n = len(proportions)
    ooc_set = set(ooc_idx)

    df = pd.DataFrame({
        "Sample": list(range(1, n + 1)),
        "Proportion": proportions,
        "UCL": ucl_list,
        "LCL": lcl_list,
        "p_bar": [p_bar] * n,
        "Defectives": defectives,
        "n": sample_sizes,
        "OOC": ["OOC" if i in ooc_set else "In Control" for i in range(n)],
        "Status": [
            "ABOVE UCL" if pi > ui else ("BELOW LCL" if pi < li else "OK")
            for pi, ui, li in zip(proportions, ucl_list, lcl_list)
        ],
    })

    # Variable limit band (area between LCL and UCL)
    band = (
        alt.Chart(df)
        .mark_area(color=_COL_BAND, opacity=0.4, line=False)
        .encode(
            x=alt.X("Sample:Q", title="Sample Period"),
            y=alt.Y("LCL:Q"),
            y2=alt.Y2("UCL:Q"),
        )
    )

    # UCL line (variable)
    ucl_line = (
        alt.Chart(df)
        .mark_line(color=_COL_UCL, strokeDash=[6, 4], strokeWidth=1.5, opacity=0.9)
        .encode(
            x=alt.X("Sample:Q"),
            y=alt.Y("UCL:Q", title="Proportion Non-Conforming"),
            tooltip=[alt.Tooltip("UCL:Q", format=".4f", title="UCL")],
        )
    )

    # LCL line (variable)
    lcl_line = (
        alt.Chart(df)
        .mark_line(color=_COL_UCL, strokeDash=[6, 4], strokeWidth=1.5, opacity=0.9)
        .encode(
            x=alt.X("Sample:Q"),
            y=alt.Y("LCL:Q"),
            tooltip=[alt.Tooltip("LCL:Q", format=".4f", title="LCL")],
        )
    )

    # Centreline (p_bar)
    p_bar_line = (
        alt.Chart(df)
        .mark_line(color=_COL_CL, strokeWidth=1.5)
        .encode(
            x=alt.X("Sample:Q"),
            y=alt.Y("p_bar:Q"),
            tooltip=[alt.Tooltip("p_bar:Q", format=".4f", title="p\u0305")],
        )
    )

    # Data line
    data_line = (
        alt.Chart(df)
        .mark_line(color=_COL_LINE, strokeWidth=1.5)
        .encode(
            x=alt.X("Sample:Q"),
            y=alt.Y("Proportion:Q"),
            tooltip=[
                alt.Tooltip("Sample:Q", title="Sample"),
                alt.Tooltip("Proportion:Q", format=".4f", title="p"),
                alt.Tooltip("Defectives:Q"),
                alt.Tooltip("n:Q", title="Sample Size"),
                alt.Tooltip("UCL:Q", format=".4f"),
                alt.Tooltip("LCL:Q", format=".4f"),
                alt.Tooltip("Status:N"),
            ],
        )
    )

    # Data points, coloured by OOC status
    data_dots = (
        alt.Chart(df)
        .mark_circle(size=55, opacity=0.8)
        .encode(
            x=alt.X("Sample:Q"),
            y=alt.Y("Proportion:Q"),
            color=alt.Color(
                "OOC:N",
                scale=alt.Scale(domain=["In Control", "OOC"], range=[_COL_LINE, _COL_OOC]),
                legend=alt.Legend(title="Status"),
            ),
            tooltip=[
                alt.Tooltip("Sample:Q"),
                alt.Tooltip("Proportion:Q", format=".4f", title="p"),
                alt.Tooltip("Defectives:Q"),
                alt.Tooltip("n:Q", title="n"),
                alt.Tooltip("OOC:N", title="Control Status"),
            ],
        )
    )

    chart = (
        alt.layer(band, ucl_line, lcl_line, p_bar_line, data_line, data_dots)
        .properties(
            title=alt.TitleParams(
                text="p-Chart — Proportion Non-Conforming",
                subtitle=(
                    f"p\u0305 = {p_bar:.4f}  |  Variable UCL/LCL (3\u03c3, sample-size adjusted)"
                ),
                fontSize=15,
                subtitleFontSize=11,
                subtitleColor="#555",
            ),
            height=260,
            width="container",
        )
        .configure_axis(grid=False, labelFontSize=11, titleFontSize=12)
        .configure_view(strokeWidth=0)
    )

    return chart


# ---------------------------------------------------------------------------
# Internal chart utility
# ---------------------------------------------------------------------------

def _hline(
    y_val: float,
    color: str,
    dash: list[int],
    tooltip_text: str,
) -> alt.Chart:
    """
    Return a horizontal rule Altair layer at y = y_val.

    Parameters
    ----------
    y_val : float
        Y-axis position for the rule.
    color : str
        Line colour (hex or named colour).
    dash : list[int]
        Stroke-dash pattern; empty list for solid line.
    tooltip_text : str
        Text to display in the tooltip.

    Returns
    -------
    alt.Chart
        A single-row Chart with mark_rule encoding.
    """
    df = pd.DataFrame({"y": [y_val], "label": [tooltip_text]})
    kwargs: dict = {"color": color, "strokeWidth": 1.8}
    if dash:
        kwargs["strokeDash"] = dash
    return (
        alt.Chart(df)
        .mark_rule(**kwargs)
        .encode(
            y=alt.Y("y:Q"),
            tooltip=[alt.Tooltip("label:N", title="Limit")],
        )
    )
