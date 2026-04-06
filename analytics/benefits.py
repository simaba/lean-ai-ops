"""
Benefits and ROI Calculation Module
=====================================
Provides Cost of Quality (COQ) analysis, ROI, payback period, and
3-year Net Present Value (NPV) calculations for Lean Six Sigma projects.

The Cost of Quality model follows the COPQ (Cost of Poor Quality) framework:
    Prevention    — costs to prevent defects (training, process design, etc.)
    Appraisal     — costs to detect defects (inspection, testing, audits)
    Internal Failure — costs of defects found before delivery (scrap, rework)
    External Failure — costs of defects found after delivery (warranty, returns)

Hard savings = actual cost reduction (verifiable in P&L).
Soft savings = cost avoidance, productivity improvement (real but harder to audit).

Usage
-----
    from analytics.benefits import (
        CostOfQualityEntry, run_benefits_analysis,
        copq_waterfall_chart, savings_timeline_chart,
    )

    entries = [
        CostOfQualityEntry("Internal Failure", "Scrap — Line 3", 120_000, True),
        CostOfQualityEntry("Internal Failure", "Rework Labour",   80_000, True),
        CostOfQualityEntry("External Failure", "Warranty Claims", 250_000, True),
        CostOfQualityEntry("Appraisal",        "Final Inspection Labour", 60_000, False),
        CostOfQualityEntry("Prevention",       "Training Programme",      15_000, False),
    ]
    result = run_benefits_analysis(
        copq_entries=entries,
        projected_improvement_pct=40.0,
        implementation_cost=75_000,
        discount_rate=0.10,
        confidence="High",
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import altair as alt
import pandas as pd


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CostOfQualityEntry:
    """A single line item in the Cost of Quality register."""

    category: str           # "Prevention" | "Appraisal" | "Internal Failure" | "External Failure"
    description: str
    annual_cost: float
    is_hard_saving: bool    # True = hard (P&L verifiable); False = soft (avoidance / productivity)

    VALID_CATEGORIES = frozenset(
        {"Prevention", "Appraisal", "Internal Failure", "External Failure"}
    )

    def __post_init__(self) -> None:
        if self.category not in self.VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{self.category}'. "
                f"Must be one of: {sorted(self.VALID_CATEGORIES)}"
            )
        if self.annual_cost < 0:
            raise ValueError(f"annual_cost must be non-negative, got {self.annual_cost}.")


@dataclass
class BenefitsResult:
    """Aggregated financial results for a Lean Six Sigma project."""

    total_copq: float

    # Cost breakdown by category
    internal_failure_cost: float
    external_failure_cost: float
    appraisal_cost: float
    prevention_cost: float

    # Savings
    projected_savings_hard: float
    projected_savings_soft: float
    total_projected_savings: float

    # Financial metrics
    implementation_cost: float
    net_benefit_year1: float      # total_projected_savings - implementation_cost
    roi_pct: float                # net_benefit_year1 / implementation_cost * 100
    payback_months: float         # implementation_cost / monthly_savings
    npv_3yr: float                # NPV at discount_rate over 3 years

    confidence_level: str         # "High" | "Medium" | "Low"
    interpretation: str
    recommended_action: str


# ---------------------------------------------------------------------------
# Core analysis function
# ---------------------------------------------------------------------------

def run_benefits_analysis(
    copq_entries: List[CostOfQualityEntry],
    projected_improvement_pct: float,
    implementation_cost: float,
    discount_rate: float = 0.10,
    confidence: str = "Medium",
) -> BenefitsResult:
    """
    Calculate project benefits and ROI.

    Parameters
    ----------
    copq_entries : list[CostOfQualityEntry]
        All cost-of-quality line items for the current state.
    projected_improvement_pct : float
        Expected % reduction in COPQ from the project (0–100).
    implementation_cost : float
        Total cost to implement the project (training, equipment, consulting, etc.).
    discount_rate : float
        Annual discount rate for NPV calculation (default 10%).
    confidence : str
        Analyst-assessed confidence in the estimates: "High", "Medium", "Low".

    Returns
    -------
    BenefitsResult
    """
    if not (0 < projected_improvement_pct <= 100):
        raise ValueError(
            f"projected_improvement_pct must be between 0 and 100, got {projected_improvement_pct}."
        )
    if implementation_cost < 0:
        raise ValueError("implementation_cost must be non-negative.")
    if not (0 < discount_rate < 1):
        raise ValueError(f"discount_rate must be between 0 and 1, got {discount_rate}.")
    if confidence not in ("High", "Medium", "Low"):
        raise ValueError(f"confidence must be 'High', 'Medium', or 'Low', got '{confidence}'.")

    # ------------------------------------------------------------------
    # 1.  Aggregate costs by category
    # ------------------------------------------------------------------
    total_copq          = sum(e.annual_cost for e in copq_entries)
    internal_failure    = sum(e.annual_cost for e in copq_entries if e.category == "Internal Failure")
    external_failure    = sum(e.annual_cost for e in copq_entries if e.category == "External Failure")
    appraisal           = sum(e.annual_cost for e in copq_entries if e.category == "Appraisal")
    prevention          = sum(e.annual_cost for e in copq_entries if e.category == "Prevention")

    # ------------------------------------------------------------------
    # 2.  Projected savings
    # ------------------------------------------------------------------
    improvement_fraction = projected_improvement_pct / 100.0

    # Hard vs soft savings: scale proportionally by entry type
    hard_copq = sum(e.annual_cost for e in copq_entries if e.is_hard_saving)
    soft_copq = sum(e.annual_cost for e in copq_entries if not e.is_hard_saving)

    projected_savings_hard = hard_copq * improvement_fraction
    projected_savings_soft = soft_copq * improvement_fraction
    total_projected_savings = projected_savings_hard + projected_savings_soft

    # ------------------------------------------------------------------
    # 3.  Financial metrics
    # ------------------------------------------------------------------
    net_benefit_year1 = total_projected_savings - implementation_cost

    roi_pct = (
        (net_benefit_year1 / implementation_cost) * 100.0
        if implementation_cost > 0
        else float("inf")
    )

    monthly_savings = total_projected_savings / 12.0
    payback_months  = (
        implementation_cost / monthly_savings
        if monthly_savings > 0
        else float("inf")
    )

    # ------------------------------------------------------------------
    # 4.  3-Year NPV
    #     Cash flows: Year 0 = -implementation_cost
    #                 Year 1 = total_projected_savings (constant annual savings)
    #                 Year 2 = total_projected_savings
    #                 Year 3 = total_projected_savings
    # ------------------------------------------------------------------
    npv_3yr = -implementation_cost + sum(
        total_projected_savings / (1.0 + discount_rate) ** t
        for t in range(1, 4)
    )

    # ------------------------------------------------------------------
    # 5.  Interpretation
    # ------------------------------------------------------------------
    interp_parts: list[str] = []

    if roi_pct == float("inf"):
        interp_parts.append(
            "Implementation cost is zero — ROI is effectively infinite. "
            "Verify cost assumptions."
        )
    elif roi_pct > 200:
        interp_parts.append(
            f"Exceptional ROI of {roi_pct:.0f}%. "
            "This project has strong financial justification."
        )
    elif roi_pct > 100:
        interp_parts.append(
            f"Strong ROI of {roi_pct:.0f}%. "
            "The project pays for itself and delivers meaningful returns."
        )
    elif roi_pct > 0:
        interp_parts.append(
            f"Positive ROI of {roi_pct:.0f}%, but modest. "
            "Validate assumptions carefully before proceeding."
        )
    else:
        interp_parts.append(
            f"ROI of {roi_pct:.0f}% — investment does not recover in Year 1. "
            "Consider phasing implementation or reducing scope."
        )

    if payback_months < 6:
        interp_parts.append(
            f"Payback period is {payback_months:.1f} months — "
            "excellent speed to value (under 6 months)."
        )
    elif payback_months <= 18:
        interp_parts.append(
            f"Payback period is {payback_months:.1f} months — acceptable."
        )
    else:
        interp_parts.append(
            f"Long payback period of {payback_months:.1f} months — "
            "ensure benefit assumptions are robust and get sign-off from Finance."
        )

    interp_parts.append(
        f"3-Year NPV at {discount_rate*100:.0f}% discount rate: "
        f"${npv_3yr:,.0f}.  "
        f"Total COPQ identified: ${total_copq:,.0f}.  "
        f"Projected annual savings: ${total_projected_savings:,.0f} "
        f"({projected_improvement_pct:.0f}% improvement).  "
        f"Hard savings: ${projected_savings_hard:,.0f} / "
        f"Soft savings: ${projected_savings_soft:,.0f}.  "
        f"Confidence: {confidence}."
    )

    interpretation = "  ".join(interp_parts)

    # ------------------------------------------------------------------
    # 6.  Recommended action
    # ------------------------------------------------------------------
    if roi_pct > 100 and payback_months <= 18:
        recommended_action = (
            "Proceed with implementation. Establish a baseline metric dashboard "
            "to track savings realisation monthly. Schedule a 90-day benefits review."
        )
    elif roi_pct > 0:
        recommended_action = (
            "Proceed cautiously. Confirm hard savings with Finance before launch. "
            "Consider a pilot to validate the projected improvement % before full rollout."
        )
    else:
        recommended_action = (
            "Re-evaluate project scope. Identify additional COPQ sources or "
            "reduce implementation cost. A phased approach may improve the ROI profile."
        )

    return BenefitsResult(
        total_copq=round(total_copq, 2),
        internal_failure_cost=round(internal_failure, 2),
        external_failure_cost=round(external_failure, 2),
        appraisal_cost=round(appraisal, 2),
        prevention_cost=round(prevention, 2),
        projected_savings_hard=round(projected_savings_hard, 2),
        projected_savings_soft=round(projected_savings_soft, 2),
        total_projected_savings=round(total_projected_savings, 2),
        implementation_cost=round(implementation_cost, 2),
        net_benefit_year1=round(net_benefit_year1, 2),
        roi_pct=round(roi_pct, 2),
        payback_months=round(payback_months, 2),
        npv_3yr=round(npv_3yr, 2),
        confidence_level=confidence,
        interpretation=interpretation,
        recommended_action=recommended_action,
    )


# ---------------------------------------------------------------------------
# Chart: COPQ Waterfall / Grouped Bar
# ---------------------------------------------------------------------------

def copq_waterfall_chart(entries: List[CostOfQualityEntry]) -> alt.Chart:
    """
    Horizontal bar chart showing annual cost by category with colour coding.

    Color scheme:
        Prevention      = #06D6A0  (green — good investment)
        Appraisal       = #4361EE  (blue — necessary cost)
        Internal Failure = #FFB703 (amber — waste to eliminate)
        External Failure = #EF233C  (red — highest risk/cost)

    Returns
    -------
    alt.Chart
    """
    if not entries:
        return alt.Chart(pd.DataFrame()).mark_text().encode(
            text=alt.value("No Cost of Quality entries to display.")
        )

    records = [
        {
            "Category":    e.category,
            "Description": e.description,
            "Annual Cost": e.annual_cost,
            "Type":        "Hard Saving" if e.is_hard_saving else "Soft / Avoidance",
        }
        for e in entries
    ]
    df = pd.DataFrame(records)

    # Aggregate by category for summary bars
    agg = df.groupby("Category", as_index=False)["Annual Cost"].sum()
    agg["Category Order"] = agg["Category"].map(
        {"Prevention": 0, "Appraisal": 1, "Internal Failure": 2, "External Failure": 3}
    )
    agg.sort_values("Category Order", inplace=True)
    agg["Label"] = agg.apply(
        lambda row: f"${row['Annual Cost']:,.0f}", axis=1
    )

    color_scale = alt.Scale(
        domain=["Prevention", "Appraisal", "Internal Failure", "External Failure"],
        range=["#06D6A0",    "#4361EE",    "#FFB703",          "#EF233C"],
    )

    bars = (
        alt.Chart(agg, title="Cost of Quality Breakdown")
        .mark_bar(cornerRadiusBottomRight=4, cornerRadiusTopRight=4)
        .encode(
            y=alt.Y(
                "Category:N",
                sort=["External Failure", "Internal Failure", "Appraisal", "Prevention"],
                axis=alt.Axis(title=None),
            ),
            x=alt.X(
                "Annual Cost:Q",
                axis=alt.Axis(title="Annual Cost ($)", format="$,.0f"),
            ),
            color=alt.Color(
                "Category:N",
                scale=color_scale,
                legend=alt.Legend(title="COQ Category"),
            ),
            tooltip=[
                alt.Tooltip("Category:N"),
                alt.Tooltip("Annual Cost:Q", format="$,.0f", title="Annual Cost"),
            ],
        )
        .properties(width=500, height=250)
    )

    text_layer = (
        alt.Chart(agg)
        .mark_text(align="left", dx=5, color="#333333", fontSize=11)
        .encode(
            y=alt.Y(
                "Category:N",
                sort=["External Failure", "Internal Failure", "Appraisal", "Prevention"],
            ),
            x=alt.X("Annual Cost:Q"),
            text=alt.Text("Label:N"),
        )
    )

    # Detail breakdown — smaller bars below
    detail_bars = (
        alt.Chart(df, title="Cost of Quality — Line Item Detail")
        .mark_bar(opacity=0.85, cornerRadiusBottomRight=3, cornerRadiusTopRight=3)
        .encode(
            y=alt.Y(
                "Description:N",
                sort=alt.EncodingSortField(field="Annual Cost", order="descending"),
                axis=alt.Axis(title=None),
            ),
            x=alt.X("Annual Cost:Q", axis=alt.Axis(title="Annual Cost ($)", format="$,.0f")),
            color=alt.Color("Category:N", scale=color_scale, legend=None),
            tooltip=[
                alt.Tooltip("Description:N"),
                alt.Tooltip("Category:N"),
                alt.Tooltip("Annual Cost:Q", format="$,.0f"),
                alt.Tooltip("Type:N", title="Saving Type"),
            ],
        )
        .properties(width=500, height=max(150, len(df) * 25))
    )

    return (
        alt.vconcat(bars + text_layer, detail_bars)
        .configure_view(stroke=None)
        .configure_axis(grid=True, gridColor="#EEEEEE")
    )


# ---------------------------------------------------------------------------
# Chart: Savings Timeline (Cumulative Benefit)
# ---------------------------------------------------------------------------

def savings_timeline_chart(result: BenefitsResult) -> alt.Chart:
    """
    Line chart showing cumulative net benefit over 36 months.

    Month 0  : -implementation_cost  (investment outlay)
    Month 1+ : cumulative += monthly_savings

    Marks the payback crossover point in green (#06D6A0).
    The horizontal zero reference line separates loss from gain.

    Returns
    -------
    alt.LayerChart
    """
    monthly_savings = result.total_projected_savings / 12.0

    months      = list(range(0, 37))
    cumulative  = []
    for m in months:
        if m == 0:
            cumulative.append(-result.implementation_cost)
        else:
            cumulative.append(-result.implementation_cost + monthly_savings * m)

    df = pd.DataFrame({"Month": months, "Cumulative Benefit": cumulative})
    df["Phase"] = df["Cumulative Benefit"].apply(
        lambda v: "Recovery" if v < 0 else "Profit"
    )

    # Find exact payback month (linear interpolation)
    payback_month = result.payback_months if result.payback_months <= 36 else None

    # Main line
    line = (
        alt.Chart(df, title="Cumulative Net Benefit Over 36 Months")
        .mark_line(strokeWidth=2.5, color="#4361EE")
        .encode(
            x=alt.X("Month:Q", axis=alt.Axis(title="Month", tickCount=12)),
            y=alt.Y(
                "Cumulative Benefit:Q",
                axis=alt.Axis(title="Cumulative Benefit ($)", format="$,.0f"),
                scale=alt.Scale(zero=True),
            ),
            tooltip=[
                alt.Tooltip("Month:Q"),
                alt.Tooltip("Cumulative Benefit:Q", format="$,.0f", title="Cumulative Benefit"),
            ],
        )
        .properties(width=560, height=300)
    )

    # Area shading: negative = red-tinted, positive = green-tinted
    area_neg = (
        alt.Chart(df[df["Cumulative Benefit"] <= 0])
        .mark_area(color="#EF233C", opacity=0.08)
        .encode(
            x=alt.X("Month:Q"),
            y=alt.Y("Cumulative Benefit:Q"),
        )
    )
    area_pos = (
        alt.Chart(df[df["Cumulative Benefit"] >= 0])
        .mark_area(color="#06D6A0", opacity=0.12)
        .encode(
            x=alt.X("Month:Q"),
            y=alt.Y("Cumulative Benefit:Q"),
        )
    )

    # Zero reference line
    zero_line = (
        alt.Chart(pd.DataFrame({"y": [0]}))
        .mark_rule(color="#888888", strokeWidth=1.2)
        .encode(y=alt.Y("y:Q"))
    )

    layers: list[alt.Chart] = [area_neg, area_pos, line, zero_line]

    # Payback marker
    if payback_month is not None and payback_month <= 36:
        payback_df = pd.DataFrame(
            {
                "Month": [payback_month],
                "Cumulative Benefit": [0.0],
                "Label": [f"Payback\n~{payback_month:.1f} mo"],
            }
        )
        payback_point = (
            alt.Chart(payback_df)
            .mark_point(color="#06D6A0", size=120, filled=True)
            .encode(
                x=alt.X("Month:Q"),
                y=alt.Y("Cumulative Benefit:Q"),
                tooltip=[
                    alt.Tooltip("Month:Q", format=".1f", title="Payback Month"),
                ],
            )
        )
        payback_text = (
            alt.Chart(payback_df)
            .mark_text(dy=-14, color="#06D6A0", fontSize=11, fontWeight="bold")
            .encode(
                x=alt.X("Month:Q"),
                y=alt.Y("Cumulative Benefit:Q"),
                text=alt.Text("Label:N"),
            )
        )
        layers += [payback_point, payback_text]

    # Year markers (vertical lines at 12, 24, 36)
    year_df = pd.DataFrame({"x": [12, 24, 36], "Label": ["Year 1", "Year 2", "Year 3"]})
    year_lines = (
        alt.Chart(year_df)
        .mark_rule(color="#BBBBBB", strokeDash=[3, 3], strokeWidth=1)
        .encode(x=alt.X("x:Q"))
    )
    year_text = (
        alt.Chart(year_df)
        .mark_text(dy=-8, color="#888888", fontSize=9)
        .encode(
            x=alt.X("x:Q"),
            y=alt.value(10),
            text=alt.Text("Label:N"),
        )
    )
    layers += [year_lines, year_text]

    return (
        alt.layer(*layers)
        .configure_view(stroke=None)
        .configure_axis(grid=True, gridColor="#EEEEEE")
    )


# ---------------------------------------------------------------------------
# Utility: summary DataFrame for reporting
# ---------------------------------------------------------------------------

def benefits_summary_table(result: BenefitsResult) -> pd.DataFrame:
    """Return a tidy summary DataFrame suitable for display."""
    rows = [
        {"Metric": "Total COPQ (Current State)",      "Value": f"${result.total_copq:,.0f}"},
        {"Metric": "  Internal Failure",              "Value": f"${result.internal_failure_cost:,.0f}"},
        {"Metric": "  External Failure",              "Value": f"${result.external_failure_cost:,.0f}"},
        {"Metric": "  Appraisal",                     "Value": f"${result.appraisal_cost:,.0f}"},
        {"Metric": "  Prevention",                    "Value": f"${result.prevention_cost:,.0f}"},
        {"Metric": "Projected Savings (Hard)",        "Value": f"${result.projected_savings_hard:,.0f}"},
        {"Metric": "Projected Savings (Soft)",        "Value": f"${result.projected_savings_soft:,.0f}"},
        {"Metric": "Total Projected Savings (Annual)","Value": f"${result.total_projected_savings:,.0f}"},
        {"Metric": "Implementation Cost",             "Value": f"${result.implementation_cost:,.0f}"},
        {"Metric": "Net Benefit Year 1",              "Value": f"${result.net_benefit_year1:,.0f}"},
        {"Metric": "ROI %",                           "Value": f"{result.roi_pct:.1f}%"},
        {"Metric": "Payback Period",                  "Value": f"{result.payback_months:.1f} months"},
        {"Metric": "3-Year NPV",                      "Value": f"${result.npv_3yr:,.0f}"},
        {"Metric": "Confidence Level",                "Value": result.confidence_level},
    ]
    return pd.DataFrame(rows)
