"""
hypothesis_tests.py
===================
Guided hypothesis testing module for the Lean Six Sigma Black Belt analytics system.

Provides one-sample t, two-sample t (Welch), paired t, one-proportion z,
two-proportion z, chi-square independence, and one-way ANOVA tests.
Each function returns a fully-populated HypothesisResult dataclass with
plain-English interpretation, assumption notes, and an optional Altair chart.
"""

from __future__ import annotations

import math
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
class HypothesisResult:
    """
    Container for a hypothesis test result and its interpretation.

    Attributes
    ----------
    test_name : str
        Human-readable name of the statistical test performed.
    statistic : float
        Calculated test statistic (t, z, F, chi2, etc.).
    p_value : float
        Two-tailed p-value (or appropriate tail for the test).
    degrees_of_freedom : float | None
        Degrees of freedom, if applicable to the test.
    effect_size : float | None
        Standardised effect size measure (Cohen's d, Cramer's V, eta²).
    confidence_interval : tuple[float, float] | None
        (lower, upper) confidence interval at the chosen alpha level.
    reject_h0 : bool
        True if p_value < alpha (null hypothesis is rejected).
    alpha : float
        Significance level used for the test (default 0.05).
    interpretation : str
        Plain-English explanation of the result (2–4 sentences).
    assumptions : list[str]
        List of statistical assumptions that apply to this test.
    recommended_action : str
        Specific next step for the analyst or process owner.
    chart : alt.Chart | None
        Optional Altair visualisation of the test data.
    """

    test_name: str
    statistic: float
    p_value: float
    degrees_of_freedom: Optional[float]
    effect_size: Optional[float]
    confidence_interval: Optional[tuple[float, float]]
    reject_h0: bool
    alpha: float
    interpretation: str
    assumptions: list[str]
    recommended_action: str
    chart: Optional[alt.Chart]


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def interpret_p(
    p: float,
    alpha: float,
    test_name: str,
    h0_description: str,
    h1_description: str,
    effect_size: Optional[float] = None,
    effect_label: str = "effect size",
    effect_threshold_small: float = 0.2,
) -> str:
    """
    Generate a 2–4 sentence plain-English interpretation of a hypothesis test result.

    Parameters
    ----------
    p : float
        Observed p-value.
    alpha : float
        Significance level (e.g. 0.05).
    test_name : str
        Name of the test (used in the narrative).
    h0_description : str
        Statement of the null hypothesis.
    h1_description : str
        Statement of the alternative hypothesis.
    effect_size : float, optional
        Absolute value of the standardised effect size.
    effect_label : str
        Label for the effect size in output text.
    effect_threshold_small : float
        Threshold below which effect is considered practically small.

    Returns
    -------
    str
        Multi-sentence plain-English interpretation.
    """
    sentences: list[str] = []

    if p < alpha:
        sentences.append(
            f"The {test_name} provides sufficient evidence to reject H\u2080 "
            f"(p = {p:.4f} < \u03b1 = {alpha}). "
            f"{h1_description} is statistically supported."
        )
    else:
        sentences.append(
            f"The {test_name} does not provide sufficient evidence to reject H\u2080 "
            f"(p = {p:.4f} \u2265 \u03b1 = {alpha}). "
            f"We cannot conclude that {h1_description}."
        )

    if effect_size is not None:
        abs_es = abs(effect_size)
        if p < alpha and abs_es < effect_threshold_small:
            sentences.append(
                f"However, the {effect_label} ({abs_es:.3f}) is small, suggesting the "
                "difference may have limited practical significance despite being statistically "
                "significant — consider whether the magnitude of the effect is meaningful in "
                "context."
            )
        elif p >= alpha and abs_es >= 0.5:
            sentences.append(
                f"Note: the {effect_label} ({abs_es:.3f}) is moderate-to-large. "
                "The test may be underpowered (insufficient sample size) to detect this "
                "difference as statistically significant — consider collecting more data."
            )

    return " ".join(sentences)


def _effect_magnitude_label(d: float) -> str:
    """Return a Cohen's d magnitude label (small / medium / large)."""
    d = abs(d)
    if d < 0.2:
        return "negligible"
    if d < 0.5:
        return "small"
    if d < 0.8:
        return "medium"
    return "large"


# ---------------------------------------------------------------------------
# One-sample t-test
# ---------------------------------------------------------------------------

def one_sample_t(
    data: list[float],
    target: float,
    alpha: float = 0.05,
) -> HypothesisResult:
    """
    One-sample t-test: test whether the population mean equals a target value.

    Parameters
    ----------
    data : list[float]
        Sample measurements.
    target : float
        Hypothesised population mean (H0: μ = target).
    alpha : float
        Significance level (default 0.05).

    Returns
    -------
    HypothesisResult
    """
    arr = np.asarray(data, dtype=float)
    n = len(arr)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))

    t_stat, p_value = stats.ttest_1samp(arr, popmean=target)
    t_stat = float(t_stat)
    p_value = float(p_value)
    df = float(n - 1)

    # Cohen's d for one-sample: (mean - target) / s
    effect_size = (mean - target) / std if std > 0 else None

    # Confidence interval on the mean at (1-alpha) level
    ci = stats.t.interval(1.0 - alpha, df=df, loc=mean, scale=std / math.sqrt(n))
    confidence_interval = (float(ci[0]), float(ci[1]))

    interpretation = interpret_p(
        p=p_value,
        alpha=alpha,
        test_name="one-sample t-test",
        h0_description=f"the population mean equals {target}",
        h1_description=f"the true mean differs from {target}",
        effect_size=effect_size,
        effect_label="Cohen's d",
        effect_threshold_small=0.2,
    )

    # Practical note
    if effect_size is not None:
        mag = _effect_magnitude_label(effect_size)
        interpretation += (
            f" The Cohen's d of {effect_size:.3f} indicates a {mag} practical effect."
        )

    assumptions = [
        "Observations are independent.",
        "Data are approximately normally distributed (use Shapiro–Wilk to verify).",
        "Measurement scale is continuous (interval or ratio).",
    ]
    if n < 30:
        assumptions.append(
            f"Sample size is small (n = {n}). Normality assumption is more critical; "
            "consider a non-parametric alternative (Wilcoxon signed-rank test) if normality "
            "cannot be confirmed."
        )

    if p_value < alpha:
        recommended_action = (
            f"The mean ({mean:.4g}) is statistically different from the target ({target:.4g}). "
            "Identify root causes of the shift using a fishbone diagram or regression analysis "
            "and implement a process adjustment to re-center the output."
        )
    else:
        recommended_action = (
            f"No statistically significant difference from the target ({target:.4g}) was detected. "
            "Continue monitoring with an I-MR control chart and re-evaluate if the sample size "
            "increases or process conditions change."
        )

    chart = _dot_strip_chart(
        values=arr.tolist(),
        reference=target,
        label="Data",
        ref_label=f"Target = {target:.4g}",
        title=f"One-Sample t-Test  (t = {t_stat:.3f}, p = {p_value:.4f})",
    )

    return HypothesisResult(
        test_name="One-Sample t-Test",
        statistic=t_stat,
        p_value=p_value,
        degrees_of_freedom=df,
        effect_size=effect_size,
        confidence_interval=confidence_interval,
        reject_h0=p_value < alpha,
        alpha=alpha,
        interpretation=interpretation,
        assumptions=assumptions,
        recommended_action=recommended_action,
        chart=chart,
    )


# ---------------------------------------------------------------------------
# Two-sample t-test (Welch by default)
# ---------------------------------------------------------------------------

def two_sample_t(
    group_a: list[float],
    group_b: list[float],
    alpha: float = 0.05,
    equal_var: bool = False,
) -> HypothesisResult:
    """
    Two-sample (Welch) t-test: test whether two independent group means differ.

    Parameters
    ----------
    group_a : list[float]
        Measurements for group A.
    group_b : list[float]
        Measurements for group B.
    alpha : float
        Significance level (default 0.05).
    equal_var : bool
        If True, assume equal variances (Student's t). Default False (Welch).

    Returns
    -------
    HypothesisResult
    """
    a = np.asarray(group_a, dtype=float)
    b = np.asarray(group_b, dtype=float)
    na, nb = len(a), len(b)
    mean_a, mean_b = float(np.mean(a)), float(np.mean(b))
    std_a, std_b = float(np.std(a, ddof=1)), float(np.std(b, ddof=1))

    t_stat, p_value = stats.ttest_ind(a, b, equal_var=equal_var)
    t_stat = float(t_stat)
    p_value = float(p_value)

    # Degrees of freedom (Welch–Satterthwaite)
    if equal_var:
        df = float(na + nb - 2)
    else:
        num = (std_a**2 / na + std_b**2 / nb) ** 2
        den = (std_a**2 / na) ** 2 / (na - 1) + (std_b**2 / nb) ** 2 / (nb - 1)
        df = float(num / den) if den > 0 else float(na + nb - 2)

    # Cohen's d with pooled SD
    pooled_std = math.sqrt(((na - 1) * std_a**2 + (nb - 1) * std_b**2) / (na + nb - 2))
    effect_size = (mean_a - mean_b) / pooled_std if pooled_std > 0 else None

    # CI on the difference of means
    diff = mean_a - mean_b
    se_diff = math.sqrt(std_a**2 / na + std_b**2 / nb)
    t_crit = float(stats.t.ppf(1 - alpha / 2, df=df))
    confidence_interval = (diff - t_crit * se_diff, diff + t_crit * se_diff)

    test_variant = "Student's two-sample t-test" if equal_var else "Welch two-sample t-test"
    interpretation = interpret_p(
        p=p_value,
        alpha=alpha,
        test_name=test_variant,
        h0_description="the two group means are equal",
        h1_description="the two group means are different",
        effect_size=effect_size,
        effect_label="Cohen's d",
        effect_threshold_small=0.2,
    )
    if effect_size is not None:
        mag = _effect_magnitude_label(effect_size)
        interpretation += f" The Cohen's d of {effect_size:.3f} indicates a {mag} practical effect."

    assumptions = [
        "Observations within each group are independent.",
        "Each group is approximately normally distributed.",
        "Measurement scale is continuous (interval or ratio).",
    ]
    if not equal_var:
        assumptions.append(
            "Welch's correction is applied — no assumption of equal variances. "
            "If variances are known to be equal, set equal_var=True for slightly more power."
        )
    else:
        assumptions.append(
            "Equal-variance assumed. Verify with Levene's test (scipy.stats.levene)."
        )

    if p_value < alpha:
        recommended_action = (
            f"Group A mean ({mean_a:.4g}) differs from Group B mean ({mean_b:.4g}). "
            "Investigate what distinguishes the two groups (different operators, machines, "
            "materials?) and use the higher-performing group as a benchmark for improvement."
        )
    else:
        recommended_action = (
            "No significant difference between groups was detected. "
            "If a meaningful difference was expected, consider increasing the sample size. "
            "Use a power analysis (e.g., statsmodels.stats.power) to determine the required n."
        )

    chart = _two_group_boxplot(
        group_a=a.tolist(),
        group_b=b.tolist(),
        label_a="Group A",
        label_b="Group B",
        title=f"Two-Sample t-Test  (t = {t_stat:.3f}, p = {p_value:.4f})",
    )

    return HypothesisResult(
        test_name="Two-Sample t-Test (Welch)" if not equal_var else "Two-Sample t-Test (Student)",
        statistic=t_stat,
        p_value=p_value,
        degrees_of_freedom=df,
        effect_size=effect_size,
        confidence_interval=confidence_interval,
        reject_h0=p_value < alpha,
        alpha=alpha,
        interpretation=interpretation,
        assumptions=assumptions,
        recommended_action=recommended_action,
        chart=chart,
    )


# ---------------------------------------------------------------------------
# Paired t-test
# ---------------------------------------------------------------------------

def paired_t(
    before: list[float],
    after: list[float],
    alpha: float = 0.05,
) -> HypothesisResult:
    """
    Paired t-test: test whether a systematic difference exists between paired measurements.

    Parameters
    ----------
    before : list[float]
        Pre-treatment (or first condition) measurements.
    after : list[float]
        Post-treatment (or second condition) measurements.
    alpha : float
        Significance level (default 0.05).

    Returns
    -------
    HypothesisResult

    Raises
    ------
    ValueError
        If before and after have different lengths.
    """
    if len(before) != len(after):
        raise ValueError("before and after must have the same number of observations.")

    b = np.asarray(before, dtype=float)
    a = np.asarray(after, dtype=float)
    diffs = b - a
    n = len(diffs)
    mean_diff = float(np.mean(diffs))
    std_diff = float(np.std(diffs, ddof=1))

    t_stat, p_value = stats.ttest_rel(b, a)
    t_stat = float(t_stat)
    p_value = float(p_value)
    df = float(n - 1)

    # Cohen's d on the differences
    effect_size = mean_diff / std_diff if std_diff > 0 else None

    # CI on mean difference
    se = std_diff / math.sqrt(n)
    ci = stats.t.interval(1.0 - alpha, df=df, loc=mean_diff, scale=se)
    confidence_interval = (float(ci[0]), float(ci[1]))

    interpretation = interpret_p(
        p=p_value,
        alpha=alpha,
        test_name="paired t-test",
        h0_description="the mean difference between paired observations is zero",
        h1_description="a systematic difference exists between the paired conditions",
        effect_size=effect_size,
        effect_label="Cohen's d (on differences)",
        effect_threshold_small=0.2,
    )
    if effect_size is not None:
        mag = _effect_magnitude_label(effect_size)
        interpretation += (
            f" The Cohen's d on the differences is {effect_size:.3f} ({mag} effect)."
        )

    assumptions = [
        "The differences between paired observations are independent.",
        "The differences are approximately normally distributed.",
        "Pairs are matched or related (same unit measured twice, or matched subjects).",
    ]
    if n < 30:
        assumptions.append(
            f"Small sample (n = {n} pairs). Verify normality of differences with Shapiro–Wilk; "
            "consider Wilcoxon signed-rank test as a non-parametric alternative."
        )

    if p_value < alpha:
        recommended_action = (
            f"A statistically significant mean difference of {mean_diff:.4g} was detected "
            f"(95 % CI: [{confidence_interval[0]:.4g}, {confidence_interval[1]:.4g}]). "
            "Quantify the practical impact using the effect size and cost-benefit analysis, "
            "then standardise the improvement if the direction is favourable."
        )
    else:
        recommended_action = (
            "No significant paired difference detected. Verify that the intervention was "
            "implemented consistently, confirm measurement system adequacy with a Gauge R&R "
            "study, and consider a larger paired sample if a small but important effect is suspected."
        )

    chart = _paired_diff_chart(
        diffs=diffs.tolist(),
        title=f"Paired t-Test — Distribution of Differences  (t = {t_stat:.3f}, p = {p_value:.4f})",
    )

    return HypothesisResult(
        test_name="Paired t-Test",
        statistic=t_stat,
        p_value=p_value,
        degrees_of_freedom=df,
        effect_size=effect_size,
        confidence_interval=confidence_interval,
        reject_h0=p_value < alpha,
        alpha=alpha,
        interpretation=interpretation,
        assumptions=assumptions,
        recommended_action=recommended_action,
        chart=chart,
    )


# ---------------------------------------------------------------------------
# One-proportion z-test
# ---------------------------------------------------------------------------

def one_proportion(
    successes: int,
    n: int,
    p0: float,
    alpha: float = 0.05,
) -> HypothesisResult:
    """
    One-proportion z-test: test whether an observed proportion equals a hypothesised value.

    Parameters
    ----------
    successes : int
        Number of successes (defectives, events, etc.) observed.
    n : int
        Total sample size.
    p0 : float
        Hypothesised proportion under H0 (0 < p0 < 1).
    alpha : float
        Significance level (default 0.05).

    Returns
    -------
    HypothesisResult
    """
    if not (0 < p0 < 1):
        raise ValueError("p0 must be strictly between 0 and 1.")
    if successes < 0 or successes > n:
        raise ValueError("successes must be between 0 and n.")

    p_hat = successes / n

    # Use scipy binom_test for exact (or normal approximation for large n)
    # For the z-statistic use the standard normal approximation
    se0 = math.sqrt(p0 * (1 - p0) / n)
    z_stat = (p_hat - p0) / se0 if se0 > 0 else 0.0

    # Two-tailed p-value from the standard normal
    p_value = float(2 * stats.norm.sf(abs(z_stat)))

    # Effect size: (p_hat - p0) / sqrt(p0*(1-p0)/n)  — standardised
    effect_size = z_stat  # equivalent to the above by definition

    # CI on p_hat using normal approximation (Wald interval)
    se_hat = math.sqrt(p_hat * (1 - p_hat) / n) if p_hat not in (0.0, 1.0) else se0
    z_crit = float(stats.norm.ppf(1 - alpha / 2))
    ci_lo = max(0.0, p_hat - z_crit * se_hat)
    ci_hi = min(1.0, p_hat + z_crit * se_hat)
    confidence_interval = (ci_lo, ci_hi)

    interpretation = interpret_p(
        p=p_value,
        alpha=alpha,
        test_name="one-proportion z-test",
        h0_description=f"the true proportion equals {p0:.4g}",
        h1_description=f"the true proportion differs from {p0:.4g}",
        effect_size=effect_size,
        effect_label="standardised z",
        effect_threshold_small=1.0,
    )
    interpretation += (
        f" Observed proportion: {p_hat:.4f} ({successes}/{n}), "
        f"hypothesised: {p0:.4f}."
    )

    assumptions = [
        "Observations are independent Bernoulli trials.",
        f"Normal approximation validity: n·p0 = {n*p0:.1f} and n·(1-p0) = {n*(1-p0):.1f} "
        f"(both should be ≥ 5; if not, use scipy.stats.binom_test for an exact test).",
    ]
    if n * p0 < 5 or n * (1 - p0) < 5:
        assumptions.append(
            "WARNING: Normal approximation may be unreliable with this sample size and p0. "
            "An exact binomial test is recommended."
        )

    if p_value < alpha:
        recommended_action = (
            f"The proportion {p_hat:.4f} is significantly different from the target {p0:.4f}. "
            "Use a Pareto chart to identify the dominant defect types and apply DMAIC "
            "to reduce the defect rate to or below the target."
        )
    else:
        recommended_action = (
            f"No significant departure from the target proportion {p0:.4f} was detected. "
            "Continue attribute monitoring with a p-chart and re-test when n is larger "
            "or if the process changes."
        )

    df_bar = pd.DataFrame({
        "Category": ["Successes", "Non-successes"],
        "Count": [successes, n - successes],
        "Proportion": [p_hat, 1 - p_hat],
    })
    chart = (
        alt.Chart(df_bar)
        .mark_bar(color="#4361EE", opacity=0.75)
        .encode(
            x=alt.X("Category:N", title=None),
            y=alt.Y("Proportion:Q", title="Proportion", scale=alt.Scale(domain=[0, 1])),
            tooltip=["Category:N", "Count:Q", alt.Tooltip("Proportion:Q", format=".4f")],
        )
        .properties(
            title=f"One-Proportion z-Test  (z = {z_stat:.3f}, p = {p_value:.4f})",
            height=260,
            width="container",
        )
    )
    # Add reference line for p0
    ref_df = pd.DataFrame({"p0": [p0]})
    ref_rule = (
        alt.Chart(ref_df)
        .mark_rule(color="#EF233C", strokeDash=[6, 4], strokeWidth=2)
        .encode(y=alt.Y("p0:Q"), tooltip=[alt.Tooltip("p0:Q", title=f"H0: p = {p0}")])
    )
    chart = alt.layer(chart, ref_rule).configure_view(strokeWidth=0)

    return HypothesisResult(
        test_name="One-Proportion z-Test",
        statistic=z_stat,
        p_value=p_value,
        degrees_of_freedom=None,
        effect_size=effect_size,
        confidence_interval=confidence_interval,
        reject_h0=p_value < alpha,
        alpha=alpha,
        interpretation=interpretation,
        assumptions=assumptions,
        recommended_action=recommended_action,
        chart=chart,
    )


# ---------------------------------------------------------------------------
# Two-proportion z-test
# ---------------------------------------------------------------------------

def two_proportion(
    s1: int,
    n1: int,
    s2: int,
    n2: int,
    alpha: float = 0.05,
) -> HypothesisResult:
    """
    Two-proportion z-test: test whether two independent proportions are equal.

    Parameters
    ----------
    s1 : int
        Successes in group 1.
    n1 : int
        Sample size of group 1.
    s2 : int
        Successes in group 2.
    n2 : int
        Sample size of group 2.
    alpha : float
        Significance level (default 0.05).

    Returns
    -------
    HypothesisResult
    """
    p1 = s1 / n1
    p2 = s2 / n2
    p_pool = (s1 + s2) / (n1 + n2)

    # Pooled standard error under H0
    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    z_stat = (p1 - p2) / se_pool if se_pool > 0 else 0.0
    p_value = float(2 * stats.norm.sf(abs(z_stat)))

    # Effect size: difference in proportions
    effect_size = p1 - p2

    # CI on the difference using unpooled SE
    se_diff = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    z_crit = float(stats.norm.ppf(1 - alpha / 2))
    diff = p1 - p2
    confidence_interval = (diff - z_crit * se_diff, diff + z_crit * se_diff)

    interpretation = interpret_p(
        p=p_value,
        alpha=alpha,
        test_name="two-proportion z-test",
        h0_description="the two proportions are equal",
        h1_description="the two proportions are different",
        effect_size=effect_size,
        effect_label="difference in proportions",
        effect_threshold_small=0.05,
    )
    interpretation += (
        f" Group 1 proportion: {p1:.4f} ({s1}/{n1}); "
        f"Group 2 proportion: {p2:.4f} ({s2}/{n2})."
    )

    assumptions = [
        "Observations within each group are independent.",
        "Samples are randomly drawn from their respective populations.",
        f"Normal approximation validity: each cell count (s1={s1}, n1-s1={n1-s1}, "
        f"s2={s2}, n2-s2={n2-s2}) should be ≥ 5.",
    ]
    cells = [s1, n1 - s1, s2, n2 - s2]
    if any(c < 5 for c in cells):
        assumptions.append(
            "WARNING: One or more cell counts are below 5. "
            "Use Fisher's exact test (scipy.stats.fisher_exact) for reliability."
        )

    if p_value < alpha:
        better = "Group 1" if p1 < p2 else "Group 2"
        recommended_action = (
            f"A statistically significant difference in proportions was found "
            f"(Δp = {diff:+.4f}). {better} has the lower defect/event rate. "
            "Identify what differentiates the better-performing group and replicate those "
            "conditions across both groups."
        )
    else:
        recommended_action = (
            "No significant difference between the two proportions was detected. "
            "Verify the test is adequately powered; use a sample-size calculation based on "
            "the minimum detectable difference that is practically important."
        )

    df_chart = pd.DataFrame({
        "Group": ["Group 1", "Group 2"],
        "Proportion": [p1, p2],
        "n": [n1, n2],
    })
    bars = (
        alt.Chart(df_chart)
        .mark_bar(color="#4361EE", opacity=0.75)
        .encode(
            x=alt.X("Group:N", title=None),
            y=alt.Y("Proportion:Q", scale=alt.Scale(domain=[0, 1])),
            tooltip=["Group:N", alt.Tooltip("Proportion:Q", format=".4f"), "n:Q"],
        )
    )
    chart = (
        bars
        .properties(
            title=f"Two-Proportion z-Test  (z = {z_stat:.3f}, p = {p_value:.4f})",
            height=260,
            width="container",
        )
        .configure_view(strokeWidth=0)
    )

    return HypothesisResult(
        test_name="Two-Proportion z-Test",
        statistic=z_stat,
        p_value=p_value,
        degrees_of_freedom=None,
        effect_size=effect_size,
        confidence_interval=confidence_interval,
        reject_h0=p_value < alpha,
        alpha=alpha,
        interpretation=interpretation,
        assumptions=assumptions,
        recommended_action=recommended_action,
        chart=chart,
    )


# ---------------------------------------------------------------------------
# Chi-square test of independence
# ---------------------------------------------------------------------------

def chi_square_independence(
    contingency_table: list[list[int]],
    alpha: float = 0.05,
) -> HypothesisResult:
    """
    Chi-square test of independence on a two-way contingency table.

    Parameters
    ----------
    contingency_table : list[list[int]]
        2-D array of observed frequencies, shape (r, c).
    alpha : float
        Significance level (default 0.05).

    Returns
    -------
    HypothesisResult
    """
    observed = np.asarray(contingency_table, dtype=float)
    r, c = observed.shape

    chi2, p_value, df, expected = stats.chi2_contingency(observed, correction=False)
    chi2 = float(chi2)
    p_value = float(p_value)
    df = float(df)

    # Cramer's V
    n_total = float(np.sum(observed))
    min_dim = min(r - 1, c - 1)
    cramers_v = math.sqrt(chi2 / (n_total * min_dim)) if min_dim > 0 and n_total > 0 else None
    effect_size = cramers_v

    interpretation = interpret_p(
        p=p_value,
        alpha=alpha,
        test_name="chi-square test of independence",
        h0_description="the row and column variables are independent",
        h1_description="an association exists between the row and column variables",
        effect_size=effect_size,
        effect_label="Cramer's V",
        effect_threshold_small=0.1,
    )
    if cramers_v is not None:
        if cramers_v < 0.1:
            v_label = "negligible"
        elif cramers_v < 0.3:
            v_label = "small"
        elif cramers_v < 0.5:
            v_label = "medium"
        else:
            v_label = "large"
        interpretation += (
            f" Cramer's V = {cramers_v:.3f} indicates a {v_label} association."
        )

    low_expected = np.sum(expected < 5)
    assumptions = [
        "Observations are independent.",
        "Data are counts (not percentages or ratios).",
        f"Expected cell frequency ≥ 5 for reliable results. "
        f"Currently {int(low_expected)} of {r*c} cells have expected count < 5.",
    ]
    if low_expected > 0:
        assumptions.append(
            "Consider collapsing categories or using Fisher's exact test "
            "(for 2×2 tables) to handle small expected counts."
        )

    if p_value < alpha:
        recommended_action = (
            "A significant association was found. Examine the standardised residuals "
            "((observed - expected) / sqrt(expected)) to identify which cells contribute "
            "most to the chi-square statistic, then target those combinations for "
            "process investigation."
        )
    else:
        recommended_action = (
            "No significant association was detected between the variables. "
            "Verify adequate cell sizes and consider whether the categories are the "
            "right level of granularity to detect a meaningful relationship."
        )

    # Heatmap of observed counts
    rows, cols = observed.shape
    records = []
    for i in range(rows):
        for j in range(cols):
            records.append({"Row": f"R{i+1}", "Col": f"C{j+1}", "Count": int(observed[i, j])})
    df_heat = pd.DataFrame(records)

    chart = (
        alt.Chart(df_heat)
        .mark_rect()
        .encode(
            x=alt.X("Col:N", title="Column Category"),
            y=alt.Y("Row:N", title="Row Category"),
            color=alt.Color("Count:Q", scale=alt.Scale(scheme="blues")),
            tooltip=["Row:N", "Col:N", "Count:Q"],
        )
        .properties(
            title=f"Chi-Square Test  (\u03c7\u00b2 = {chi2:.3f}, df = {int(df)}, p = {p_value:.4f})",
            height=260,
            width="container",
        )
        .configure_view(strokeWidth=0)
    )

    return HypothesisResult(
        test_name="Chi-Square Test of Independence",
        statistic=chi2,
        p_value=p_value,
        degrees_of_freedom=df,
        effect_size=cramers_v,
        confidence_interval=None,
        reject_h0=p_value < alpha,
        alpha=alpha,
        interpretation=interpretation,
        assumptions=assumptions,
        recommended_action=recommended_action,
        chart=chart,
    )


# ---------------------------------------------------------------------------
# One-way ANOVA
# ---------------------------------------------------------------------------

def one_way_anova(
    *groups: list[float],
    alpha: float = 0.05,
) -> HypothesisResult:
    """
    One-way ANOVA: test whether three or more independent group means are equal.

    Parameters
    ----------
    *groups : list[float]
        Two or more groups of measurements. Pass as positional arguments.
    alpha : float
        Significance level (default 0.05).

    Returns
    -------
    HypothesisResult

    Raises
    ------
    ValueError
        If fewer than 2 groups are provided.
    """
    if len(groups) < 2:
        raise ValueError("At least 2 groups are required for one-way ANOVA.")

    arrays = [np.asarray(g, dtype=float) for g in groups]
    k = len(arrays)
    n_total = sum(len(a) for a in arrays)

    f_stat, p_value = stats.f_oneway(*arrays)
    f_stat = float(f_stat)
    p_value = float(p_value)

    df_between = float(k - 1)
    df_within = float(n_total - k)

    # Eta-squared: SS_between / SS_total
    grand_mean = np.mean(np.concatenate(arrays))
    ss_between = sum(len(a) * (np.mean(a) - grand_mean) ** 2 for a in arrays)
    ss_total = sum(np.sum((a - grand_mean) ** 2) for a in arrays)
    eta_squared = float(ss_between / ss_total) if ss_total > 0 else None

    interpretation = interpret_p(
        p=p_value,
        alpha=alpha,
        test_name="one-way ANOVA",
        h0_description="all group means are equal",
        h1_description="at least one group mean differs from the others",
        effect_size=eta_squared,
        effect_label="eta-squared (\u03b7\u00b2)",
        effect_threshold_small=0.01,
    )
    if eta_squared is not None:
        if eta_squared < 0.01:
            eta_label = "negligible"
        elif eta_squared < 0.06:
            eta_label = "small"
        elif eta_squared < 0.14:
            eta_label = "medium"
        else:
            eta_label = "large"
        interpretation += (
            f" Eta-squared = {eta_squared:.3f} indicates a {eta_label} proportion of "
            "variance explained by the grouping factor."
        )

    assumptions = [
        "Observations are independent within and across groups.",
        "Each group is approximately normally distributed (verify with Shapiro–Wilk).",
        "Group variances are approximately equal (verify with Levene's test).",
        "Measurement scale is continuous (interval or ratio).",
    ]
    smallest_n = min(len(a) for a in arrays)
    if smallest_n < 10:
        assumptions.append(
            f"The smallest group has only {smallest_n} observations. "
            "The F-test may be sensitive to non-normality at this sample size; "
            "consider Kruskal–Wallis as a non-parametric alternative."
        )

    if p_value < alpha:
        recommended_action = (
            "Significant differences among group means were detected. "
            "Run a post-hoc test (Tukey HSD or Bonferroni correction) to identify which "
            "specific pairs of groups differ, then focus improvement efforts on the "
            "factor levels driving the worst performance."
        )
    else:
        recommended_action = (
            "No significant difference among group means was found. "
            "Verify that the factor levels tested represent the full range of practical "
            "operating conditions. If between-group variation is expected to be small, "
            "increase the number of replicates per group to improve statistical power."
        )

    # Box plot for each group
    records = []
    for idx, arr in enumerate(arrays):
        for val in arr.tolist():
            records.append({"Group": f"Group {idx+1}", "Value": val})
    df_box = pd.DataFrame(records)

    box = (
        alt.Chart(df_box)
        .mark_boxplot(color="#4361EE", outliers={"color": "#EF233C"})
        .encode(
            x=alt.X("Group:N", title=None),
            y=alt.Y("Value:Q", title="Measurement"),
            tooltip=["Group:N", alt.Tooltip("Value:Q", format=".4f")],
        )
    )
    chart = (
        box
        .properties(
            title=f"One-Way ANOVA  (F = {f_stat:.3f}, df = {int(df_between)}/{int(df_within)}, p = {p_value:.4f})",
            height=260,
            width="container",
        )
        .configure_view(strokeWidth=0)
    )

    return HypothesisResult(
        test_name="One-Way ANOVA",
        statistic=f_stat,
        p_value=p_value,
        degrees_of_freedom=df_between,
        effect_size=eta_squared,
        confidence_interval=None,
        reject_h0=p_value < alpha,
        alpha=alpha,
        interpretation=interpretation,
        assumptions=assumptions,
        recommended_action=recommended_action,
        chart=chart,
    )


# ---------------------------------------------------------------------------
# Internal chart helpers
# ---------------------------------------------------------------------------

def _dot_strip_chart(
    values: list[float],
    reference: float,
    label: str,
    ref_label: str,
    title: str,
) -> alt.Chart:
    """Dot strip chart with a reference line for one-sample visualisation."""
    df = pd.DataFrame({"value": values, "group": label})
    dots = (
        alt.Chart(df)
        .mark_circle(color="#4361EE", opacity=0.6, size=60)
        .encode(
            x=alt.X("value:Q", title="Measurement"),
            y=alt.Y("group:N", title=None),
            tooltip=[alt.Tooltip("value:Q", title="Value", format=".4f")],
        )
    )
    ref_df = pd.DataFrame({"ref": [reference], "label": [ref_label]})
    ref_line = (
        alt.Chart(ref_df)
        .mark_rule(color="#EF233C", strokeDash=[6, 4], strokeWidth=2)
        .encode(
            x=alt.X("ref:Q"),
            tooltip=[alt.Tooltip("label:N", title="Reference")],
        )
    )
    return (
        alt.layer(dots, ref_line)
        .properties(title=title, height=130, width="container")
        .configure_view(strokeWidth=0)
    )


def _two_group_boxplot(
    group_a: list[float],
    group_b: list[float],
    label_a: str,
    label_b: str,
    title: str,
) -> alt.Chart:
    """Side-by-side box plots for two independent groups."""
    records = (
        [{"Group": label_a, "Value": v} for v in group_a]
        + [{"Group": label_b, "Value": v} for v in group_b]
    )
    df = pd.DataFrame(records)
    chart = (
        alt.Chart(df)
        .mark_boxplot(color="#4361EE", outliers={"color": "#EF233C"})
        .encode(
            x=alt.X("Group:N", title=None),
            y=alt.Y("Value:Q", title="Measurement"),
            tooltip=["Group:N", alt.Tooltip("Value:Q", format=".4f")],
        )
        .properties(title=title, height=260, width="container")
        .configure_view(strokeWidth=0)
    )
    return chart


def _paired_diff_chart(diffs: list[float], title: str) -> alt.Chart:
    """Histogram of paired differences with a zero reference line."""
    df = pd.DataFrame({"diff": diffs})
    hist = (
        alt.Chart(df)
        .mark_bar(color="#4361EE", opacity=0.65)
        .encode(
            x=alt.X("diff:Q", bin=alt.Bin(maxbins=30), title="Difference (Before − After)"),
            y=alt.Y("count():Q", title="Count"),
            tooltip=[alt.Tooltip("diff:Q", bin=alt.Bin(maxbins=30), title="Diff bin"), "count():Q"],
        )
    )
    zero_df = pd.DataFrame({"zero": [0.0]})
    zero_line = (
        alt.Chart(zero_df)
        .mark_rule(color="#EF233C", strokeDash=[6, 4], strokeWidth=2)
        .encode(x=alt.X("zero:Q"))
    )
    return (
        alt.layer(hist, zero_line)
        .properties(title=title, height=260, width="container")
        .configure_view(strokeWidth=0)
    )
