"""
Measurement System Analysis (MSA) — Gauge R&R (ANOVA Method)
=============================================================
Implements the AIAG MSA Reference Manual methodology for Gauge Repeatability
and Reproducibility using the Analysis of Variance (ANOVA) approach, which
is the standard for Lean Six Sigma Black Belt analyses.

Usage
-----
    from analytics.msa import run_gauge_rr, gauge_rr_chart
    result = run_gauge_rr(df, part_col="Part", operator_col="Operator",
                          measurement_col="Value", lsl=0.0, usl=10.0)
    chart  = gauge_rr_chart(result, df, "Part", "Operator", "Value")
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import altair as alt
import pandas as pd


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class MSAResult:
    """Holds all Gauge R&R ANOVA results."""

    n_parts: int
    n_operators: int
    n_reps: int

    # Variance components (expressed as standard deviations — "sigma")
    repeatability_var: float       # EV  = equipment / within-appraiser variation
    reproducibility_var: float     # AV  = appraiser / between-appraiser variation
    gauge_var: float               # GRR = sqrt(EV^2 + AV^2)
    part_var: float                # PV  = part-to-part variation
    total_var: float               # TV  = sqrt(GRR^2 + PV^2)

    # Study-variation percentages  (5.15 * sigma basis — 99% coverage)
    pct_grr_study: float           # GRR / TV * 100
    pct_grr_tolerance: float       # GRR / tolerance * 100  (0 if no tolerance given)

    # Number of distinct categories
    ndc: int                       # 1.41 * PV / GRR  (floor)

    # Component percentages of total variation
    ev_pct: float                  # EV / TV * 100
    av_pct: float                  # AV / TV * 100
    pv_pct: float                  # PV / TV * 100

    # Acceptability flags
    is_acceptable: bool            # pct_grr_study < 10
    is_marginal: bool              # 10 <= pct_grr_study < 30

    interpretation: str
    recommended_action: str


# ---------------------------------------------------------------------------
# Core analysis function
# ---------------------------------------------------------------------------

def run_gauge_rr(
    data: pd.DataFrame,
    part_col: str,
    operator_col: str,
    measurement_col: str,
    lsl: Optional[float] = None,
    usl: Optional[float] = None,
) -> MSAResult:
    """
    Run a full Gauge R&R analysis using the ANOVA method.

    Parameters
    ----------
    data : pd.DataFrame
        Long-form data with one row per measurement.
    part_col : str
        Column identifying the part (sample).
    operator_col : str
        Column identifying the operator (appraiser).
    measurement_col : str
        Column containing the measured value.
    lsl : float, optional
        Lower specification limit.  Used only for tolerance-based GRR%.
    usl : float, optional
        Upper specification limit.  Used only for tolerance-based GRR%.

    Returns
    -------
    MSAResult
    """
    df = data[[part_col, operator_col, measurement_col]].copy()
    df.columns = ["part", "operator", "y"]
    df["y"] = pd.to_numeric(df["y"], errors="raise")

    parts     = sorted(df["part"].unique())
    operators = sorted(df["operator"].unique())
    p = len(parts)       # number of parts
    o = len(operators)   # number of operators

    # Verify balanced design (same number of reps in every cell)
    cell_counts = df.groupby(["part", "operator"])["y"].count()
    rep_counts  = cell_counts.unique()
    if len(rep_counts) != 1:
        raise ValueError(
            f"Unbalanced design detected. Each Part × Operator cell must have "
            f"the same number of replications. Found counts: {sorted(rep_counts)}"
        )
    r = int(rep_counts[0])  # number of replications per cell

    # ------------------------------------------------------------------
    # ANOVA sum-of-squares decomposition
    # ------------------------------------------------------------------
    grand_mean = df["y"].mean()

    # Part means, operator means, cell means
    part_means     = df.groupby("part")["y"].mean()
    operator_means = df.groupby("operator")["y"].mean()
    cell_means     = df.groupby(["part", "operator"])["y"].mean()

    # SS_Parts  (between parts)
    ss_parts = o * r * sum((part_means[pt] - grand_mean) ** 2 for pt in parts)

    # SS_Operators (between operators)
    ss_operators = p * r * sum(
        (operator_means[op] - grand_mean) ** 2 for op in operators
    )

    # SS_Interaction (Part × Operator)
    ss_interaction = r * sum(
        (cell_means.loc[(pt, op)] - part_means[pt] - operator_means[op] + grand_mean) ** 2
        for pt in parts
        for op in operators
    )

    # SS_Error (within cells — pure repeatability)
    ss_error = sum(
        (row["y"] - cell_means.loc[(row["part"], row["operator"])]) ** 2
        for _, row in df.iterrows()
    )

    # ------------------------------------------------------------------
    # Degrees of freedom
    # ------------------------------------------------------------------
    df_parts       = p - 1
    df_operators   = o - 1
    df_interaction = (p - 1) * (o - 1)
    df_error       = p * o * (r - 1)
    # df_total    = N - 1  (not used directly but kept for sanity)

    # Guard against zero df (e.g., r = 1 means df_error = 0)
    if df_error == 0:
        raise ValueError(
            "Each Part × Operator cell must have at least 2 replications "
            "to estimate pure repeatability (EV). Got r=1."
        )

    # ------------------------------------------------------------------
    # Mean squares
    # ------------------------------------------------------------------
    ms_parts       = ss_parts       / df_parts
    ms_operators   = ss_operators   / df_operators
    ms_interaction = ss_interaction / df_interaction  if df_interaction > 0 else 0.0
    ms_error       = ss_error       / df_error

    # ------------------------------------------------------------------
    # Variance components
    # ------------------------------------------------------------------
    # Repeatability (Equipment Variation)
    var_repeatability = ms_error                               # sigma_e^2

    # Interaction variance component
    var_interaction = max(0.0, (ms_interaction - ms_error) / r)

    # Reproducibility (Appraiser Variation) — includes interaction
    var_operator = max(0.0, (ms_operators - ms_interaction) / (p * r))
    var_reproducibility = var_operator + var_interaction       # AV^2

    # Gauge R&R
    var_gauge = var_repeatability + var_reproducibility        # GRR^2

    # Part-to-part variation
    var_part = max(0.0, (ms_parts - ms_interaction) / (o * r))

    # Total variation
    var_total = var_gauge + var_part

    # Convert to standard deviations (sigma)
    sigma_ev    = math.sqrt(var_repeatability)
    sigma_av    = math.sqrt(var_reproducibility)
    sigma_gauge = math.sqrt(var_gauge)
    sigma_pv    = math.sqrt(var_part)
    sigma_tv    = math.sqrt(var_total)

    # ------------------------------------------------------------------
    # Study variation: 5.15 * sigma  (Minitab default, 99% coverage)
    # ------------------------------------------------------------------
    K = 5.15

    sv_ev    = K * sigma_ev
    sv_av    = K * sigma_av
    sv_gauge = K * sigma_gauge
    sv_pv    = K * sigma_pv
    sv_tv    = K * sigma_tv

    if sv_tv > 0:
        pct_grr_study = (sv_gauge / sv_tv) * 100.0
        ev_pct        = (sv_ev    / sv_tv) * 100.0
        av_pct        = (sv_av    / sv_tv) * 100.0
        pv_pct        = (sv_pv    / sv_tv) * 100.0
    else:
        pct_grr_study = 0.0
        ev_pct = av_pct = pv_pct = 0.0

    # Tolerance-based GRR%
    pct_grr_tolerance = 0.0
    if lsl is not None and usl is not None:
        tolerance = usl - lsl
        if tolerance > 0:
            pct_grr_tolerance = (sv_gauge / tolerance) * 100.0

    # Number of distinct categories
    if sigma_gauge > 0:
        ndc = max(1, int(math.floor(1.41 * sigma_pv / sigma_gauge)))
    else:
        ndc = 9999  # perfect gauge

    # ------------------------------------------------------------------
    # Acceptability flags
    # ------------------------------------------------------------------
    is_acceptable = pct_grr_study < 10.0
    is_marginal   = 10.0 <= pct_grr_study < 30.0

    # ------------------------------------------------------------------
    # Interpretation text
    # ------------------------------------------------------------------
    interp_lines: list[str] = []

    if is_acceptable:
        interp_lines.append(
            "Measurement system is acceptable. GRR is below 10% of total variation."
        )
    elif is_marginal:
        dominant = "equipment (EV)" if ev_pct >= av_pct else "appraiser (AV)"
        interp_lines.append(
            "Measurement system is marginal. May be acceptable depending on "
            "application criticality and cost of improvement. "
            f"Investigate dominant source: {dominant} contributes more variation."
        )
    else:
        interp_lines.append(
            "Measurement system is NOT acceptable. More than 30% of observed "
            "variation is from the gauge, not the process. The measurement system "
            "must be improved before relying on this data."
        )

    if ndc < 2:
        interp_lines.append(
            f"NDC = {ndc}: Measurement system cannot distinguish between parts — "
            "effectively useless for process analysis."
        )
    elif ndc < 5:
        interp_lines.append(
            f"NDC = {ndc}: Measurement system can make only coarse distinctions."
        )
    else:
        interp_lines.append(
            f"NDC = {ndc}: Measurement system can make adequate distinctions "
            "for process control (NDC ≥ 5)."
        )

    interp_lines.append(
        f"GRR% (study) = {pct_grr_study:.1f}% | "
        f"EV% = {ev_pct:.1f}% | AV% = {av_pct:.1f}% | PV% = {pv_pct:.1f}%."
    )

    if pct_grr_tolerance > 0:
        interp_lines.append(
            f"GRR% (tolerance) = {pct_grr_tolerance:.1f}% "
            f"(based on tolerance = {usl - lsl:.4g})."
        )

    interpretation = "  ".join(interp_lines)

    # ------------------------------------------------------------------
    # Recommended action
    # ------------------------------------------------------------------
    if is_acceptable:
        recommended_action = (
            "No immediate action required on the measurement system. "
            "Continue monitoring for drift over time."
        )
    elif is_marginal:
        if ev_pct >= av_pct:
            recommended_action = (
                "Primary driver is equipment variation (EV). "
                "Investigate: gauge calibration, fixture stability, environmental "
                "conditions, and measurement procedure consistency. "
                "Consider re-training operators or improving the fixture."
            )
        else:
            recommended_action = (
                "Primary driver is appraiser variation (AV). "
                "Conduct operator training and standardize the measurement procedure. "
                "Develop clear measurement work instructions with visual aids."
            )
    else:
        recommended_action = (
            "URGENT: Measurement system must be improved before using this data "
            "for process decisions. Actions: (1) Perform full calibration, "
            "(2) retrain all operators to a standardized procedure, "
            "(3) assess gauge resolution — it may be inadequate for this tolerance. "
            "(4) Consider replacing the measurement device."
        )

    return MSAResult(
        n_parts=p,
        n_operators=o,
        n_reps=r,
        repeatability_var=sigma_ev,
        reproducibility_var=sigma_av,
        gauge_var=sigma_gauge,
        part_var=sigma_pv,
        total_var=sigma_tv,
        pct_grr_study=round(pct_grr_study, 2),
        pct_grr_tolerance=round(pct_grr_tolerance, 2),
        ndc=ndc,
        ev_pct=round(ev_pct, 2),
        av_pct=round(av_pct, 2),
        pv_pct=round(pv_pct, 2),
        is_acceptable=is_acceptable,
        is_marginal=is_marginal,
        interpretation=interpretation,
        recommended_action=recommended_action,
    )


# ---------------------------------------------------------------------------
# Charting
# ---------------------------------------------------------------------------

def gauge_rr_chart(
    result: MSAResult,
    data: pd.DataFrame,
    part_col: str,
    operator_col: str,
    measurement_col: str,
) -> alt.Chart:
    """
    Build a 3-panel Altair composite chart for Gauge R&R results.

    Panel 1 — Measurements by Part (colored by operator)
    Panel 2 — Measurements by Operator
    Panel 3 — Variation component breakdown (EV%, AV%, PV%)

    Returns
    -------
    alt.VConcatChart
    """
    df = data[[part_col, operator_col, measurement_col]].copy()
    df.columns = ["Part", "Operator", "Measurement"]
    df["Measurement"] = pd.to_numeric(df["Measurement"])
    df["Part"] = df["Part"].astype(str)
    df["Operator"] = df["Operator"].astype(str)

    # ------------------------------------------------------------------
    # Panel 1: Measurements by Part
    # ------------------------------------------------------------------
    part_chart = (
        alt.Chart(df, title="Measurements by Part")
        .mark_circle(size=60, opacity=0.75)
        .encode(
            x=alt.X(
                "Part:N",
                sort=sorted(df["Part"].unique()),
                axis=alt.Axis(labelAngle=-30, title="Part"),
            ),
            y=alt.Y(
                "Measurement:Q",
                scale=alt.Scale(zero=False),
                axis=alt.Axis(title="Measurement"),
            ),
            color=alt.Color(
                "Operator:N",
                legend=alt.Legend(title="Operator"),
            ),
            tooltip=["Part", "Operator", "Measurement"],
        )
        .properties(width=500, height=200)
    )

    # Add mean line per part
    part_means_df = df.groupby("Part", as_index=False)["Measurement"].mean()
    part_mean_line = (
        alt.Chart(part_means_df)
        .mark_line(color="black", strokeDash=[4, 2], strokeWidth=1.5)
        .encode(
            x=alt.X("Part:N", sort=sorted(df["Part"].unique())),
            y=alt.Y("Measurement:Q"),
        )
    )
    panel1 = part_chart + part_mean_line

    # ------------------------------------------------------------------
    # Panel 2: Measurements by Operator
    # ------------------------------------------------------------------
    panel2 = (
        alt.Chart(df, title="Measurements by Operator")
        .mark_boxplot(extent="min-max", size=30)
        .encode(
            x=alt.X(
                "Operator:N",
                sort=sorted(df["Operator"].unique()),
                axis=alt.Axis(title="Operator"),
            ),
            y=alt.Y(
                "Measurement:Q",
                scale=alt.Scale(zero=False),
                axis=alt.Axis(title="Measurement"),
            ),
            color=alt.Color("Operator:N", legend=None),
            tooltip=["Operator", "Measurement"],
        )
        .properties(width=500, height=200)
    )

    # ------------------------------------------------------------------
    # Panel 3: Variation Breakdown Bar Chart
    # ------------------------------------------------------------------
    breakdown_data = pd.DataFrame(
        {
            "Component": ["Equipment Variation (EV)", "Appraiser Variation (AV)", "Part Variation (PV)"],
            "Pct_of_TV": [result.ev_pct, result.av_pct, result.pv_pct],
            "Color":     ["#4361EE", "#FFB703", "#06D6A0"],
        }
    )
    # Sort descending
    breakdown_data = breakdown_data.sort_values("Pct_of_TV", ascending=False)

    # Threshold rules line for GRR
    threshold_30 = pd.DataFrame({"y": [30.0]})
    threshold_10 = pd.DataFrame({"y": [10.0]})

    bar_chart = (
        alt.Chart(breakdown_data, title="Variation Component Breakdown (% of Total Variation)")
        .mark_bar()
        .encode(
            x=alt.X(
                "Component:N",
                sort=list(breakdown_data["Component"]),
                axis=alt.Axis(labelAngle=-15, title="Variation Component"),
            ),
            y=alt.Y(
                "Pct_of_TV:Q",
                axis=alt.Axis(title="% of Total Variation"),
                scale=alt.Scale(domain=[0, 110]),
            ),
            color=alt.Color(
                "Component:N",
                scale=alt.Scale(
                    domain=list(breakdown_data["Component"]),
                    range=list(breakdown_data["Color"]),
                ),
                legend=alt.Legend(title="Component"),
            ),
            tooltip=[
                alt.Tooltip("Component:N"),
                alt.Tooltip("Pct_of_TV:Q", format=".2f", title="% of TV"),
            ],
        )
        .properties(width=500, height=200)
    )

    label_layer = (
        alt.Chart(breakdown_data)
        .mark_text(dy=-6, color="black", fontSize=11)
        .encode(
            x=alt.X("Component:N", sort=list(breakdown_data["Component"])),
            y=alt.Y("Pct_of_TV:Q"),
            text=alt.Text("Pct_of_TV:Q", format=".1f"),
        )
    )

    rule_30 = (
        alt.Chart(threshold_30)
        .mark_rule(color="#EF233C", strokeDash=[6, 3], strokeWidth=1.5)
        .encode(y=alt.Y("y:Q"))
    )
    rule_10 = (
        alt.Chart(threshold_10)
        .mark_rule(color="#FFB703", strokeDash=[6, 3], strokeWidth=1.5)
        .encode(y=alt.Y("y:Q"))
    )

    panel3 = bar_chart + label_layer + rule_30 + rule_10

    # ------------------------------------------------------------------
    # Combine into vertical stack with title
    # ------------------------------------------------------------------
    combined = alt.vconcat(
        panel1,
        panel2,
        panel3,
        title=alt.TitleParams(
            text=f"Gauge R&R Analysis — GRR% = {result.pct_grr_study:.1f}%  |  NDC = {result.ndc}",
            fontSize=14,
            anchor="middle",
        ),
    ).configure_view(stroke=None).configure_axis(grid=True, gridColor="#E0E0E0")

    return combined


# ---------------------------------------------------------------------------
# Utility: summary table for display
# ---------------------------------------------------------------------------

def msa_summary_table(result: MSAResult) -> pd.DataFrame:
    """
    Return a tidy DataFrame summarising the MSA result suitable
    for display in a Streamlit app or report.
    """
    K = 5.15
    rows = [
        {"Source": "Gauge R&R",           "StdDev": result.gauge_var,        "StudyVar (5.15σ)": K * result.gauge_var,        "%StudyVar": result.pct_grr_study},
        {"Source": "  Repeatability (EV)", "StdDev": result.repeatability_var, "StudyVar (5.15σ)": K * result.repeatability_var, "%StudyVar": result.ev_pct},
        {"Source": "  Reproducibility (AV)","StdDev": result.reproducibility_var,"StudyVar (5.15σ)": K * result.reproducibility_var,"%StudyVar": result.av_pct},
        {"Source": "Part-to-Part (PV)",   "StdDev": result.part_var,          "StudyVar (5.15σ)": K * result.part_var,          "%StudyVar": result.pv_pct},
        {"Source": "Total Variation (TV)", "StdDev": result.total_var,         "StudyVar (5.15σ)": K * result.total_var,         "%StudyVar": 100.0},
    ]
    df = pd.DataFrame(rows)
    df["StdDev"]          = df["StdDev"].round(6)
    df["StudyVar (5.15σ)"] = df["StudyVar (5.15σ)"].round(6)
    df["%StudyVar"]       = df["%StudyVar"].round(2)
    return df
