"""
capability.py
=============
Process Capability Analysis module for the Lean Six Sigma Black Belt analytics system.

Computes Cp, Cpk, Pp, Ppk, sigma level, DPMO, and normality tests.
Produces an Altair histogram with specification limit overlays.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import altair as alt
import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class CapabilityResult:
    """
    Container for all process capability metrics and supporting metadata.

    Attributes
    ----------
    n : int
        Number of data points analysed.
    mean : float
        Arithmetic mean of the data.
    within_stdev : float
        Short-term (within-subgroup) standard deviation estimated from the
        average moving range: MR_bar / 1.128  (d2 constant for subgroup n=2).
    overall_stdev : float
        Long-term standard deviation: sample std with ddof=1.
    lsl : float | None
        Lower specification limit, or None if not provided.
    usl : float | None
        Upper specification limit, or None if not provided.
    target : float | None
        Nominal / target value, or None if not provided.
    cp : float | None
        Potential capability index.  Requires both LSL and USL.
    cpk : float | None
        Actual (centred) capability index using within_stdev.
    pp : float | None
        Potential performance index.  Requires both LSL and USL.
    ppk : float | None
        Actual performance index using overall_stdev.
    sigma_level : float | None
        Process sigma level estimated as cpk * 3.
    pct_out_of_spec : float
        Observed percentage of values outside the specification limits (0–100).
    dpm : int
        Estimated defects per million opportunities derived from the normal CDF
        using overall_stdev.
    normality_p : float
        p-value from the normality test (Shapiro–Wilk if n≤50, else D'Agostino–
        Pearson omnibus test).
    is_normal : bool
        True when normality_p > 0.05.
    interpretation : str
        Plain-English summary of capability performance (2–3 sentences).
    recommended_action : str
        Specific, actionable next step for the process owner.
    """

    n: int
    mean: float
    within_stdev: float
    overall_stdev: float
    lsl: Optional[float]
    usl: Optional[float]
    target: Optional[float]
    cp: Optional[float]
    cpk: Optional[float]
    pp: Optional[float]
    ppk: Optional[float]
    sigma_level: Optional[float]
    pct_out_of_spec: float
    dpm: int
    normality_p: float
    is_normal: bool
    interpretation: str
    recommended_action: str


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

def run_capability(
    data: list[float],
    lsl: Optional[float] = None,
    usl: Optional[float] = None,
    target: Optional[float] = None,
) -> CapabilityResult:
    """
    Perform a full process capability study on a list of continuous measurements.

    Parameters
    ----------
    data : list[float]
        Individual measurements (at least 2 values required).
    lsl : float, optional
        Lower specification limit.
    usl : float, optional
        Upper specification limit.
    target : float, optional
        Process target / nominal value.

    Returns
    -------
    CapabilityResult
        Fully populated capability result dataclass.

    Raises
    ------
    ValueError
        If fewer than 2 data points are supplied.
    """
    if len(data) < 2:
        raise ValueError("At least 2 data points are required for capability analysis.")

    arr = np.asarray(data, dtype=float)
    n = len(arr)

    # ---- Basic statistics ------------------------------------------------
    mean = float(np.mean(arr))

    # Within (short-term) standard deviation via average moving range
    moving_ranges = np.abs(np.diff(arr))
    mr_bar = float(np.mean(moving_ranges))
    within_stdev = mr_bar / 1.128  # d2 constant for subgroup size 2

    # Overall (long-term) standard deviation
    overall_stdev = float(np.std(arr, ddof=1))

    # ---- Capability indices ----------------------------------------------
    cp: Optional[float] = None
    cpk: Optional[float] = None
    pp: Optional[float] = None
    ppk: Optional[float] = None
    sigma_level: Optional[float] = None

    has_both_limits = (lsl is not None) and (usl is not None)

    if has_both_limits and within_stdev > 0:
        cp = (usl - lsl) / (6.0 * within_stdev)

    cpu: Optional[float] = None
    cpl: Optional[float] = None

    if usl is not None and within_stdev > 0:
        cpu = (usl - mean) / (3.0 * within_stdev)
    if lsl is not None and within_stdev > 0:
        cpl = (mean - lsl) / (3.0 * within_stdev)

    if cpu is not None and cpl is not None:
        cpk = min(cpu, cpl)
    elif cpu is not None:
        cpk = cpu
    elif cpl is not None:
        cpk = cpl

    if cpk is not None:
        sigma_level = cpk * 3.0

    # Performance indices (use overall_stdev)
    if has_both_limits and overall_stdev > 0:
        pp = (usl - lsl) / (6.0 * overall_stdev)

    ppu: Optional[float] = None
    ppl: Optional[float] = None

    if usl is not None and overall_stdev > 0:
        ppu = (usl - mean) / (3.0 * overall_stdev)
    if lsl is not None and overall_stdev > 0:
        ppl = (mean - lsl) / (3.0 * overall_stdev)

    if ppu is not None and ppl is not None:
        ppk = min(ppu, ppl)
    elif ppu is not None:
        ppk = ppu
    elif ppl is not None:
        ppk = ppl

    # ---- Observed % out of spec -----------------------------------------
    out_mask = np.zeros(n, dtype=bool)
    if usl is not None:
        out_mask |= arr > usl
    if lsl is not None:
        out_mask |= arr < lsl
    pct_out_of_spec = float(np.sum(out_mask)) / n * 100.0

    # ---- Estimated DPMO via normal CDF (uses overall_stdev) -------------
    dpm_float = 0.0
    if overall_stdev > 0:
        if usl is not None:
            # probability above USL
            dpm_float += stats.norm.sf(usl, loc=mean, scale=overall_stdev)
        if lsl is not None:
            # probability below LSL
            dpm_float += stats.norm.cdf(lsl, loc=mean, scale=overall_stdev)
    dpm = int(round(dpm_float * 1_000_000))

    # ---- Normality test -------------------------------------------------
    if n <= 50:
        stat_norm, normality_p = stats.shapiro(arr)
    else:
        stat_norm, normality_p = stats.normaltest(arr)
    normality_p = float(normality_p)
    is_normal = normality_p > 0.05

    # ---- Plain-English interpretation -----------------------------------
    interpretation = _build_interpretation(cpk, is_normal, n)
    recommended_action = _build_recommendation(cpk, ppk, pct_out_of_spec, is_normal, n)

    return CapabilityResult(
        n=n,
        mean=mean,
        within_stdev=within_stdev,
        overall_stdev=overall_stdev,
        lsl=lsl,
        usl=usl,
        target=target,
        cp=cp,
        cpk=cpk,
        pp=pp,
        ppk=ppk,
        sigma_level=sigma_level,
        pct_out_of_spec=pct_out_of_spec,
        dpm=dpm,
        normality_p=normality_p,
        is_normal=is_normal,
        interpretation=interpretation,
        recommended_action=recommended_action,
    )


# ---------------------------------------------------------------------------
# Interpretation helpers
# ---------------------------------------------------------------------------

def _build_interpretation(
    cpk: Optional[float],
    is_normal: bool,
    n: int,
) -> str:
    """Build a 2–3 sentence plain-English interpretation of capability."""
    parts: list[str] = []

    if cpk is None:
        parts.append(
            "No specification limits were provided, so capability indices cannot be "
            "calculated. Review the process against customer requirements to establish limits."
        )
    elif cpk >= 1.67:
        parts.append(
            f"Process is highly capable (Cpk = {cpk:.3f}). "
            "Sigma level suggests excellent performance with very few defects expected."
        )
    elif cpk >= 1.33:
        parts.append(
            f"Process is capable (Cpk = {cpk:.3f}). "
            "Meets the typical industry minimum standard of 1.33."
        )
    elif cpk >= 1.0:
        parts.append(
            f"Process is marginally capable (Cpk = {cpk:.3f}). "
            "Some improvement is recommended to achieve a more robust safety margin."
        )
    else:
        parts.append(
            f"Process is NOT capable (Cpk = {cpk:.3f}). "
            "Significant output falls outside the specification limits and immediate action is required."
        )

    if not is_normal:
        parts.append(
            "Note: data may not be normally distributed — results should be interpreted "
            "cautiously and a non-normal capability analysis (e.g., Johnson transformation "
            "or percentile method) may be more appropriate."
        )

    if n < 30:
        parts.append(
            "Sample size is small — results are estimates. "
            "Collect more data for a reliable baseline (minimum 30, ideally 100+ observations)."
        )

    return " ".join(parts)


def _build_recommendation(
    cpk: Optional[float],
    ppk: Optional[float],
    pct_out_of_spec: float,
    is_normal: bool,
    n: int,
) -> str:
    """Return a specific, actionable next step for the process owner."""
    if cpk is None:
        return (
            "Establish clear lower and upper specification limits in collaboration with the "
            "customer or engineering team, then re-run the capability analysis."
        )

    if n < 30:
        return (
            f"Collect at least {30 - n} additional observations (target ≥ 30, ideally ≥ 100) "
            "to establish a statistically reliable baseline before drawing capability conclusions."
        )

    if not is_normal:
        return (
            "Investigate the source of non-normality (outliers, multi-modality, or a skewed "
            "underlying distribution). Apply a Box–Cox or Johnson transformation, or use a "
            "percentile-based capability metric before reporting results."
        )

    if cpk < 1.0:
        if pct_out_of_spec > 5.0:
            return (
                f"{pct_out_of_spec:.1f}% of output is out of spec. Immediately initiate a "
                "DMAIC project: map the process, identify the dominant sources of variation "
                "with a fishbone / C&E matrix, and implement containment while root-cause "
                "analysis is underway."
            )
        return (
            "Cpk is below 1.0. Run a Gauge R&R study to rule out measurement error, then "
            "use a Multi-Vari chart or ANOVA to identify the primary factor driving defects "
            "and implement targeted process improvement."
        )

    if cpk < 1.33:
        return (
            "Cpk is between 1.0 and 1.33 — process is marginal. Investigate centering: "
            "if the process mean can be shifted toward the target the Cpk will improve "
            "without reducing variation. Consider SPC monitoring to detect drift early."
        )

    if cpk < 1.67:
        if ppk is not None and ppk < cpk * 0.9:
            return (
                "Cpk is acceptable but Ppk is notably lower, indicating long-term drift or "
                "process shifts. Implement an I-MR or Xbar-R control chart to monitor stability "
                "and initiate a measurement systems study to quantify Gauge R&R."
            )
        return (
            "Process is capable. Maintain current controls and conduct periodic SPC monitoring "
            "(monthly capability study) to confirm sustained performance."
        )

    # cpk >= 1.67
    return (
        "Process is highly capable. Consider extending the control chart interval, "
        "documenting the current process settings as a best-practice standard, and "
        "reallocating improvement resources to the next highest-priority process."
    )


# ---------------------------------------------------------------------------
# Altair visualisation
# ---------------------------------------------------------------------------

def capability_histogram(
    data: list[float],
    result: CapabilityResult,
) -> alt.Chart:
    """
    Build an Altair layered histogram with specification limit overlays.

    Parameters
    ----------
    data : list[float]
        The raw measurement data (same list passed to run_capability).
    result : CapabilityResult
        The populated CapabilityResult from run_capability.

    Returns
    -------
    alt.Chart
        Altair layered chart object ready for display in Streamlit or Jupyter.
    """
    df = pd.DataFrame({"value": data})

    # ---- Histogram layer ------------------------------------------------
    hist = (
        alt.Chart(df)
        .mark_bar(color="#4361EE", opacity=0.65, cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
        .encode(
            alt.X(
                "value:Q",
                bin=alt.Bin(maxbins=40),
                title="Measurement Value",
            ),
            alt.Y("count():Q", title="Count"),
            tooltip=[
                alt.Tooltip("value:Q", bin=alt.Bin(maxbins=40), title="Bin start"),
                alt.Tooltip("count():Q", title="Count"),
            ],
        )
    )

    # ---- Vertical rule layers -------------------------------------------
    rule_layers: list[alt.Chart] = [hist]

    def _vline(value: float, color: str, dash: list[int], label: str) -> alt.Chart:
        """Return a vertical rule mark at a given x value."""
        rule_df = pd.DataFrame({"value": [value], "label": [label]})
        return (
            alt.Chart(rule_df)
            .mark_rule(color=color, strokeDash=dash, strokeWidth=2)
            .encode(
                x=alt.X("value:Q"),
                tooltip=[alt.Tooltip("label:N", title="Limit"), alt.Tooltip("value:Q", title="Value")],
            )
        )

    # Mean — blue solid
    rule_layers.append(_vline(result.mean, "#1D3461", [], "Mean"))

    # LSL — red dashed
    if result.lsl is not None:
        rule_layers.append(_vline(result.lsl, "#EF233C", [6, 4], f"LSL = {result.lsl:.4g}"))

    # USL — red dashed
    if result.usl is not None:
        rule_layers.append(_vline(result.usl, "#EF233C", [6, 4], f"USL = {result.usl:.4g}"))

    # Target — green dashed
    if result.target is not None:
        rule_layers.append(_vline(result.target, "#2DC653", [4, 4], f"Target = {result.target:.4g}"))

    # ---- Assemble subtitle for key metrics ------------------------------
    metrics_parts: list[str] = []
    if result.cpk is not None:
        metrics_parts.append(f"Cpk = {result.cpk:.3f}")
    if result.ppk is not None:
        metrics_parts.append(f"Ppk = {result.ppk:.3f}")
    if result.sigma_level is not None:
        metrics_parts.append(f"σ = {result.sigma_level:.2f}")
    metrics_parts.append(f"n = {result.n}")
    metrics_parts.append(f"DPM = {result.dpm:,}")
    subtitle = "  |  ".join(metrics_parts)

    chart = (
        alt.layer(*rule_layers)
        .properties(
            title=alt.TitleParams(
                text="Process Capability — Data Distribution",
                subtitle=subtitle,
                fontSize=15,
                subtitleFontSize=11,
                subtitleColor="#555555",
            ),
            height=280,
            width="container",
        )
        .configure_axis(grid=False, labelFontSize=11, titleFontSize=12)
        .configure_view(strokeWidth=0)
    )

    return chart
