"""
Regression Analysis Module
============================
Provides simple linear regression and multiple linear regression for
Lean Six Sigma projects, with full ANOVA table, coefficient inference,
assumption checks, and Altair visualisations.

Statsmodels is used when available (preferred — gives richer output).
A pure numpy/scipy fallback is provided for environments without statsmodels.

Usage
-----
    from analytics.regression import simple_regression, multiple_regression
    from analytics.regression import regression_scatter_chart, residual_plot

    result = simple_regression(x, y, x_name="Temperature", y_name="Yield")
    chart  = regression_scatter_chart(x, y, result, "Temperature", "Yield")
    resid  = residual_plot(x, y, result)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import altair as alt
import numpy as np
import pandas as pd
from scipy import stats

# Optional statsmodels — graceful fallback
try:
    import statsmodels.api as sm
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    _HAS_STATSMODELS = True
except ImportError:
    _HAS_STATSMODELS = False


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class RegressionResult:
    """Holds all regression output."""

    model_type: str                             # "Simple Linear" | "Multiple Linear"
    n: int

    r_squared: float
    adj_r_squared: float
    f_statistic: float
    f_p_value: float

    coefficients: Dict[str, float]              # {"intercept": ..., "VarA": ...}
    p_values: Dict[str, float]
    standard_errors: Dict[str, float]
    confidence_intervals: Dict[str, Tuple[float, float]]   # 95% CI per coefficient

    residual_std_error: float
    significant_predictors: List[str]           # p < alpha

    interpretation: str
    recommended_action: str
    assumptions_checks: Dict[str, str]          # {"normality": "Pass: ...", ...}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _shapiro_check(residuals: np.ndarray) -> str:
    """Run Shapiro-Wilk on residuals; return pass/fail string."""
    if len(residuals) < 3:
        return "Inconclusive: Too few observations for Shapiro-Wilk test."
    if len(residuals) > 5000:
        # For large samples use D'Agostino-Pearson
        stat, p = stats.normaltest(residuals)
        test_name = "D'Agostino-Pearson"
    else:
        stat, p = stats.shapiro(residuals)
        test_name = "Shapiro-Wilk"
    verdict = "Pass" if p >= 0.05 else "Fail"
    return (
        f"{verdict} ({test_name} W={stat:.4f}, p={p:.4f}). "
        + ("Residuals appear normally distributed." if p >= 0.05
           else "Residuals may not be normally distributed — check the residual plot.")
    )


def _breusch_pagan_text(fitted: np.ndarray, residuals: np.ndarray) -> str:
    """
    Simple Breusch-Pagan-style check via correlation between |residuals| and fitted.
    If |corr| > 0.3, flag as potential heteroscedasticity.
    """
    if len(fitted) < 4:
        return "Inconclusive: insufficient data."
    corr = np.corrcoef(fitted, np.abs(residuals))[0, 1]
    if abs(corr) > 0.3:
        return (
            f"Potential heteroscedasticity detected "
            f"(|corr(fitted, |residuals|)| = {abs(corr):.3f} > 0.3). "
            "Inspect the residual vs fitted plot."
        )
    return (
        f"No strong evidence of heteroscedasticity "
        f"(|corr(fitted, |residuals|)| = {abs(corr):.3f} ≤ 0.3)."
    )


def _durbin_watson(residuals: np.ndarray) -> str:
    """Compute Durbin-Watson statistic (test for autocorrelation in residuals)."""
    if len(residuals) < 3:
        return "Inconclusive: too few observations."
    diff = np.diff(residuals)
    dw = np.sum(diff ** 2) / np.sum(residuals ** 2)
    if dw < 1.5:
        verdict = "Possible positive autocorrelation"
    elif dw > 2.5:
        verdict = "Possible negative autocorrelation"
    else:
        verdict = "No significant autocorrelation detected"
    return f"DW = {dw:.3f} — {verdict} (ideal ≈ 2.0)."


def _vif_check(X_df: pd.DataFrame) -> str:
    """Compute Variance Inflation Factors for multicollinearity."""
    if not _HAS_STATSMODELS:
        return "VIF check unavailable — statsmodels not installed."
    if X_df.shape[1] < 2:
        return "Only one predictor — VIF not applicable."
    try:
        X_arr = X_df.values.astype(float)
        vif_values = {
            col: variance_inflation_factor(X_arr, i)
            for i, col in enumerate(X_df.columns)
        }
        high_vif = {k: v for k, v in vif_values.items() if v > 5}
        if high_vif:
            details = ", ".join(f"{k}={v:.2f}" for k, v in high_vif.items())
            return (
                f"High VIF detected ({details}). "
                "Multicollinearity may inflate standard errors."
            )
        details = ", ".join(f"{k}={v:.2f}" for k, v in vif_values.items())
        return f"VIF values acceptable ({details}). No serious multicollinearity."
    except Exception as exc:
        return f"VIF computation error: {exc}"


# ---------------------------------------------------------------------------
# Simple Linear Regression
# ---------------------------------------------------------------------------

def simple_regression(
    x: List[float],
    y: List[float],
    x_name: str = "X",
    y_name: str = "Y",
    alpha: float = 0.05,
) -> RegressionResult:
    """
    Fit a simple linear regression y = b0 + b1*x.

    Uses statsmodels OLS when available; falls back to scipy.stats.linregress.

    Parameters
    ----------
    x : array-like of float
    y : array-like of float
    x_name : str   Label for predictor variable.
    y_name : str   Label for response variable.
    alpha : float  Significance level (default 0.05).

    Returns
    -------
    RegressionResult
    """
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)

    if len(x_arr) != len(y_arr):
        raise ValueError("x and y must have the same length.")
    if len(x_arr) < 3:
        raise ValueError("Need at least 3 observations for regression.")

    n = len(x_arr)

    if _HAS_STATSMODELS:
        X_sm = sm.add_constant(x_arr)
        model = sm.OLS(y_arr, X_sm).fit()

        intercept = float(model.params[0])
        slope     = float(model.params[1])
        se_int    = float(model.bse[0])
        se_slope  = float(model.bse[1])
        p_int     = float(model.pvalues[0])
        p_slope   = float(model.pvalues[1])
        ci        = model.conf_int(alpha=alpha)
        ci_int    = (float(ci[0][0]), float(ci[1][0]))
        ci_slope  = (float(ci[0][1]), float(ci[1][1]))
        r2        = float(model.rsquared)
        adj_r2    = float(model.rsquared_adj)
        f_stat    = float(model.fvalue)
        f_pval    = float(model.f_pvalue)
        rse       = float(np.sqrt(model.mse_resid))
        residuals = np.array(model.resid)
        fitted    = np.array(model.fittedvalues)
    else:
        lr = stats.linregress(x_arr, y_arr)
        slope     = float(lr.slope)
        intercept = float(lr.intercept)
        r2        = float(lr.rvalue ** 2)
        fitted    = intercept + slope * x_arr
        residuals = y_arr - fitted
        rse       = float(np.sqrt(np.sum(residuals ** 2) / (n - 2)))
        se_slope  = float(lr.stderr)
        se_int    = float(lr.intercept_stderr) if hasattr(lr, "intercept_stderr") else rse * math.sqrt(np.mean(x_arr**2) / (np.var(x_arr, ddof=1) * n))
        # t-values and p-values
        t_slope   = slope / se_slope if se_slope > 0 else float("inf")
        t_int     = intercept / se_int if se_int > 0 else float("inf")
        p_slope   = float(2 * stats.t.sf(abs(t_slope), df=n - 2))
        p_int     = float(2 * stats.t.sf(abs(t_int),   df=n - 2))
        # 95% CIs
        t_crit    = stats.t.ppf(1 - alpha / 2, df=n - 2)
        ci_slope  = (slope - t_crit * se_slope, slope + t_crit * se_slope)
        ci_int    = (intercept - t_crit * se_int, intercept + t_crit * se_int)
        # Adjusted R²
        adj_r2    = 1 - (1 - r2) * (n - 1) / (n - 2)
        # F-statistic (1 predictor: F = t²)
        f_stat    = t_slope ** 2
        f_pval    = float(stats.f.sf(f_stat, 1, n - 2))

    # Assumptions checks
    norm_check = _shapiro_check(residuals)
    hetero_check = _breusch_pagan_text(fitted, residuals)
    dw_check = _durbin_watson(residuals)

    # Cook's distance approximation to flag influential points
    leverage = (x_arr - np.mean(x_arr)) ** 2 / (np.sum((x_arr - np.mean(x_arr)) ** 2)) + 1 / n
    std_resid = residuals / (rse * np.sqrt(1 - leverage + 1e-12))
    n_outliers = int(np.sum(np.abs(std_resid) > 3))
    outlier_check = (
        "No extreme outliers (|standardised residual| > 3)."
        if n_outliers == 0
        else f"{n_outliers} observation(s) with |standardised residual| > 3 detected. Investigate."
    )

    assumptions_checks = {
        "normality":          norm_check,
        "homoscedasticity":   hetero_check,
        "autocorrelation":    dw_check,
        "outliers":           outlier_check,
        "multicollinearity":  "Not applicable for simple linear regression.",
    }

    significant_predictors: List[str] = []
    if p_slope < alpha:
        significant_predictors.append(x_name)

    # Interpretation
    direction = "increases" if slope > 0 else "decreases"
    sig_text  = (
        f"The relationship is statistically significant (p = {p_slope:.4f})."
        if p_slope < alpha
        else f"The relationship is NOT statistically significant at α = {alpha} (p = {p_slope:.4f})."
    )
    interpretation = (
        f"Simple Linear Regression: {y_name} = {intercept:.4f} + {slope:.4f} × {x_name}.  "
        f"For each 1-unit increase in {x_name}, {y_name} {direction} by {abs(slope):.4f} units.  "
        f"R² = {r2:.4f} — the model explains {r2 * 100:.1f}% of the variation in {y_name}.  "
        f"Adjusted R² = {adj_r2:.4f}.  "
        f"{sig_text}  "
        f"Residual Standard Error = {rse:.4f}."
    )

    if p_slope < alpha and r2 >= 0.70:
        recommended_action = (
            f"{x_name} is a strong, statistically significant predictor of {y_name}. "
            "Use this relationship for process optimisation. Validate the model on new data."
        )
    elif p_slope < alpha:
        recommended_action = (
            f"{x_name} is statistically significant but explains only {r2 * 100:.1f}% of "
            f"variation in {y_name}. Consider adding additional predictors or transformations."
        )
    else:
        recommended_action = (
            f"No significant linear relationship found between {x_name} and {y_name}. "
            "Try a non-linear model, check for lurking variables, or gather more data."
        )

    return RegressionResult(
        model_type="Simple Linear",
        n=n,
        r_squared=round(r2, 6),
        adj_r_squared=round(adj_r2, 6),
        f_statistic=round(f_stat, 4),
        f_p_value=round(f_pval, 6),
        coefficients={"intercept": round(intercept, 6), x_name: round(slope, 6)},
        p_values={"intercept": round(p_int, 6), x_name: round(p_slope, 6)},
        standard_errors={"intercept": round(se_int, 6), x_name: round(se_slope, 6)},
        confidence_intervals={
            "intercept": (round(ci_int[0], 6),  round(ci_int[1], 6)),
            x_name:      (round(ci_slope[0], 6), round(ci_slope[1], 6)),
        },
        residual_std_error=round(rse, 6),
        significant_predictors=significant_predictors,
        interpretation=interpretation,
        recommended_action=recommended_action,
        assumptions_checks=assumptions_checks,
    )


# ---------------------------------------------------------------------------
# Multiple Linear Regression
# ---------------------------------------------------------------------------

def multiple_regression(
    X: pd.DataFrame,
    y: List[float],
    y_name: str = "Y",
    alpha: float = 0.05,
) -> RegressionResult:
    """
    Fit a multiple linear regression y = b0 + b1*x1 + b2*x2 + ...

    Parameters
    ----------
    X : pd.DataFrame
        Predictor matrix.  Each column is one predictor.
        Do NOT include a constant column — it is added automatically.
    y : array-like of float
        Response variable.
    y_name : str
        Label for response variable.
    alpha : float
        Significance level for hypothesis tests.

    Returns
    -------
    RegressionResult
    """
    X_df  = X.copy()
    y_arr = np.array(y, dtype=float)
    n     = len(y_arr)
    k     = X_df.shape[1]   # number of predictors

    if n != len(X_df):
        raise ValueError("X and y must have the same number of rows.")
    if n < k + 2:
        raise ValueError(
            f"Need at least {k + 2} observations for {k} predictors."
        )

    predictor_names = list(X_df.columns)

    if _HAS_STATSMODELS:
        X_sm  = sm.add_constant(X_df.values.astype(float))
        model = sm.OLS(y_arr, X_sm).fit()

        params   = model.params            # [intercept, b1, b2, ...]
        bse      = model.bse
        pvals    = model.pvalues
        ci_arr   = model.conf_int(alpha=alpha)
        r2       = float(model.rsquared)
        adj_r2   = float(model.rsquared_adj)
        f_stat   = float(model.fvalue)
        f_pval   = float(model.f_pvalue)
        rse      = float(np.sqrt(model.mse_resid))
        residuals = np.array(model.resid)
        fitted    = np.array(model.fittedvalues)

        all_names = ["intercept"] + predictor_names
        coefficients       = {nm: round(float(params[i]),  6) for i, nm in enumerate(all_names)}
        p_values           = {nm: round(float(pvals[i]),   6) for i, nm in enumerate(all_names)}
        standard_errors    = {nm: round(float(bse[i]),     6) for i, nm in enumerate(all_names)}
        confidence_intervals = {
            nm: (round(float(ci_arr[i][0]), 6), round(float(ci_arr[i][1]), 6))
            for i, nm in enumerate(all_names)
        }

    else:
        # Pure numpy lstsq fallback
        X_aug = np.column_stack([np.ones(n), X_df.values.astype(float)])
        params, _, _, _ = np.linalg.lstsq(X_aug, y_arr, rcond=None)
        fitted    = X_aug @ params
        residuals = y_arr - fitted

        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((y_arr - np.mean(y_arr)) ** 2))
        r2     = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k - 1)
        rse    = math.sqrt(ss_res / (n - k - 1)) if n > k + 1 else float("nan")

        # Coefficient standard errors via (X'X)^-1
        try:
            cov = rse ** 2 * np.linalg.inv(X_aug.T @ X_aug)
            ses = np.sqrt(np.diag(cov))
        except np.linalg.LinAlgError:
            ses = np.full(len(params), float("nan"))

        t_stats = params / (ses + 1e-300)
        p_vals  = np.array([float(2 * stats.t.sf(abs(t), df=n - k - 1)) for t in t_stats])

        t_crit = stats.t.ppf(1 - alpha / 2, df=n - k - 1)
        ci_lo  = params - t_crit * ses
        ci_hi  = params + t_crit * ses

        ms_model = (ss_tot - ss_res) / k
        ms_resid = ss_res / (n - k - 1) if n > k + 1 else float("nan")
        f_stat   = ms_model / ms_resid if ms_resid and ms_resid > 0 else float("nan")
        f_pval   = float(stats.f.sf(f_stat, k, n - k - 1)) if not math.isnan(f_stat) else float("nan")

        all_names = ["intercept"] + predictor_names
        coefficients       = {nm: round(float(params[i]),  6) for i, nm in enumerate(all_names)}
        p_values           = {nm: round(float(p_vals[i]),  6) for i, nm in enumerate(all_names)}
        standard_errors    = {nm: round(float(ses[i]),     6) for i, nm in enumerate(all_names)}
        confidence_intervals = {
            nm: (round(float(ci_lo[i]), 6), round(float(ci_hi[i]), 6))
            for i, nm in enumerate(all_names)
        }

    # Assumptions checks
    norm_check   = _shapiro_check(residuals)
    hetero_check = _breusch_pagan_text(fitted, residuals)
    dw_check     = _durbin_watson(residuals)
    vif_check    = _vif_check(X_df)

    n_outliers = int(np.sum(np.abs(residuals / (rse + 1e-300)) > 3))
    outlier_check = (
        "No extreme outliers (|standardised residual| > 3)."
        if n_outliers == 0
        else f"{n_outliers} observation(s) with |standardised residual| > 3. Investigate."
    )

    significant_predictors = [
        nm for nm in predictor_names if p_values.get(nm, 1.0) < alpha
    ]

    # Interpretation
    sig_list = ", ".join(significant_predictors) if significant_predictors else "none"
    interpretation = (
        f"Multiple Linear Regression with {k} predictors.  "
        f"R² = {r2:.4f} — the model explains {r2 * 100:.1f}% of variation in {y_name}.  "
        f"Adjusted R² = {adj_r2:.4f}.  "
        f"F({k}, {n - k - 1}) = {f_stat:.3f}, p = {f_pval:.4f} — "
        + ("model is statistically significant overall." if f_pval < alpha
           else "model is NOT statistically significant overall.")
        + f"  Significant predictors (α={alpha}): {sig_list}.  "
        f"Residual Standard Error = {rse:.4f}."
    )

    if len(significant_predictors) > 0 and r2 >= 0.70:
        recommended_action = (
            "The model explains a large portion of variation and has significant predictors. "
            "Use for prediction and optimisation. Validate on holdout data."
        )
    elif len(significant_predictors) > 0:
        recommended_action = (
            "Significant predictors found but R² is low. "
            "Consider adding higher-order terms, interactions, or additional variables."
        )
    else:
        recommended_action = (
            "No significant predictors. Re-examine variable selection, "
            "check for non-linear relationships, and ensure adequate sample size."
        )

    return RegressionResult(
        model_type="Multiple Linear",
        n=n,
        r_squared=round(r2, 6),
        adj_r_squared=round(adj_r2, 6),
        f_statistic=round(f_stat, 4) if not math.isnan(f_stat) else float("nan"),
        f_p_value=round(f_pval, 6) if not math.isnan(f_pval) else float("nan"),
        coefficients=coefficients,
        p_values=p_values,
        standard_errors=standard_errors,
        confidence_intervals=confidence_intervals,
        residual_std_error=round(rse, 6),
        significant_predictors=significant_predictors,
        interpretation=interpretation,
        recommended_action=recommended_action,
        assumptions_checks={
            "normality":         norm_check,
            "homoscedasticity":  hetero_check,
            "autocorrelation":   dw_check,
            "multicollinearity": vif_check,
            "outliers":          outlier_check,
        },
    )


# ---------------------------------------------------------------------------
# Chart: Scatter + Regression Line (with confidence band)
# ---------------------------------------------------------------------------

def regression_scatter_chart(
    x: List[float],
    y: List[float],
    result: RegressionResult,
    x_name: str = "X",
    y_name: str = "Y",
) -> alt.Chart:
    """
    Scatter plot of actual data with the fitted regression line and 95% confidence band.

    Only applicable to simple regression (one predictor).  For multiple regression,
    use partial regression plots instead.

    Returns
    -------
    alt.LayerChart
    """
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)
    n     = len(x_arr)

    intercept = result.coefficients["intercept"]
    # Find slope key (the one that isn't intercept)
    slope_key = [k for k in result.coefficients if k != "intercept"][0]
    slope     = result.coefficients[slope_key]

    y_pred = intercept + slope * x_arr
    residuals = y_arr - y_pred
    rse    = result.residual_std_error

    # 95% confidence band on fitted line
    x_line = np.linspace(x_arr.min(), x_arr.max(), 200)
    x_mean = np.mean(x_arr)
    ss_x   = np.sum((x_arr - x_mean) ** 2)
    t_crit = stats.t.ppf(0.975, df=n - 2) if n > 2 else 1.96

    se_band = rse * np.sqrt(1 / n + (x_line - x_mean) ** 2 / (ss_x + 1e-300))
    y_line  = intercept + slope * x_line
    ci_lo   = y_line - t_crit * se_band
    ci_hi   = y_line + t_crit * se_band

    # Data frames
    scatter_df = pd.DataFrame(
        {
            x_name: x_arr,
            y_name: y_arr,
            "Predicted": y_pred,
            "Residual": residuals,
        }
    )
    line_df = pd.DataFrame(
        {x_name: x_line, "Fitted": y_line, "CI_Lo": ci_lo, "CI_Hi": ci_hi}
    )

    scatter = (
        alt.Chart(scatter_df)
        .mark_circle(size=55, color="#4361EE", opacity=0.75)
        .encode(
            x=alt.X(f"{x_name}:Q", axis=alt.Axis(title=x_name)),
            y=alt.Y(f"{y_name}:Q", scale=alt.Scale(zero=False), axis=alt.Axis(title=y_name)),
            tooltip=[
                alt.Tooltip(f"{x_name}:Q", format=".4g"),
                alt.Tooltip(f"{y_name}:Q", format=".4g"),
                alt.Tooltip("Predicted:Q", format=".4g"),
                alt.Tooltip("Residual:Q", format=".4g"),
            ],
        )
    )

    conf_band = (
        alt.Chart(line_df)
        .mark_area(color="#4361EE", opacity=0.12)
        .encode(
            x=alt.X(f"{x_name}:Q"),
            y=alt.Y("CI_Lo:Q"),
            y2=alt.Y2("CI_Hi:Q"),
        )
    )

    reg_line = (
        alt.Chart(line_df)
        .mark_line(color="#EF233C", strokeWidth=2)
        .encode(
            x=alt.X(f"{x_name}:Q"),
            y=alt.Y("Fitted:Q"),
        )
    )

    title_text = (
        f"Regression: {y_name} ~ {x_name}  |  "
        f"R² = {result.r_squared:.4f}  |  "
        f"ŷ = {intercept:.4f} + {slope:.4f}·{x_name}"
    )

    return (
        alt.layer(conf_band, scatter, reg_line)
        .properties(width=560, height=350, title=title_text)
        .configure_view(stroke=None)
        .configure_axis(grid=True, gridColor="#EEEEEE")
    )


# ---------------------------------------------------------------------------
# Chart: Residual Plot
# ---------------------------------------------------------------------------

def residual_plot(
    x: List[float],
    y: List[float],
    result: RegressionResult,
) -> alt.Chart:
    """
    Fitted values vs residuals plot for assumption checking.

    Highlights observations with |standardised residual| > 2 in red.
    Includes a horizontal reference line at y = 0.

    Returns
    -------
    alt.LayerChart
    """
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)

    intercept = result.coefficients["intercept"]
    slope_key = [k for k in result.coefficients if k != "intercept"][0]
    slope     = result.coefficients[slope_key]

    fitted    = intercept + slope * x_arr
    residuals = y_arr - fitted
    rse       = result.residual_std_error if result.residual_std_error > 0 else 1.0
    std_resid = residuals / rse

    df = pd.DataFrame(
        {
            "Fitted":             fitted,
            "Residual":           residuals,
            "Std Residual":       std_resid,
            "Large Residual":     np.abs(std_resid) > 2,
            "Index":              np.arange(len(fitted)),
        }
    )
    df["Color Flag"] = df["Large Residual"].map(
        {True: "Large (|std resid| > 2)", False: "Normal"}
    )

    color_scale = alt.Scale(
        domain=["Normal", "Large (|std resid| > 2)"],
        range=["#4361EE", "#EF233C"],
    )

    scatter = (
        alt.Chart(df)
        .mark_circle(size=55, opacity=0.75)
        .encode(
            x=alt.X(
                "Fitted:Q",
                axis=alt.Axis(title="Fitted Values", grid=True),
            ),
            y=alt.Y(
                "Residual:Q",
                scale=alt.Scale(zero=True),
                axis=alt.Axis(title="Residuals", grid=True),
            ),
            color=alt.Color(
                "Color Flag:N",
                scale=color_scale,
                legend=alt.Legend(title=""),
            ),
            tooltip=[
                alt.Tooltip("Index:Q", title="Obs #"),
                alt.Tooltip("Fitted:Q", format=".4g"),
                alt.Tooltip("Residual:Q", format=".4g"),
                alt.Tooltip("Std Residual:Q", format=".3f"),
            ],
        )
        .properties(
            width=560,
            height=320,
            title="Residual Plot — check for patterns (should look random)",
        )
    )

    zero_line = (
        alt.Chart(pd.DataFrame({"y": [0]}))
        .mark_rule(color="#888888", strokeWidth=1.5)
        .encode(y=alt.Y("y:Q"))
    )

    # 2-sigma guide lines
    upper_2s = (
        alt.Chart(pd.DataFrame({"y": [2 * rse]}))
        .mark_rule(color="#FFB703", strokeDash=[4, 3], strokeWidth=1)
        .encode(y=alt.Y("y:Q"))
    )
    lower_2s = (
        alt.Chart(pd.DataFrame({"y": [-2 * rse]}))
        .mark_rule(color="#FFB703", strokeDash=[4, 3], strokeWidth=1)
        .encode(y=alt.Y("y:Q"))
    )

    return (
        alt.layer(scatter, zero_line, upper_2s, lower_2s)
        .configure_view(stroke=None)
        .configure_axis(grid=True, gridColor="#EEEEEE")
    )


# ---------------------------------------------------------------------------
# Utility: regression coefficient table
# ---------------------------------------------------------------------------

def regression_coeff_table(result: RegressionResult) -> pd.DataFrame:
    """Return a tidy DataFrame of coefficients, SEs, CIs, and p-values."""
    rows = []
    for name in result.coefficients:
        rows.append(
            {
                "Term":              name,
                "Coefficient":       result.coefficients[name],
                "Std Error":         result.standard_errors.get(name, float("nan")),
                "95% CI Lower":      result.confidence_intervals.get(name, (float("nan"), float("nan")))[0],
                "95% CI Upper":      result.confidence_intervals.get(name, (float("nan"), float("nan")))[1],
                "p-value":           result.p_values.get(name, float("nan")),
                "Significant":       result.p_values.get(name, 1.0) < 0.05,
            }
        )
    return pd.DataFrame(rows)
