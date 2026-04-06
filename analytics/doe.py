"""
Design of Experiments (DOE) Assistant
========================================
Generates screening and optimisation experimental designs for Lean Six Sigma
projects.  Supports 2-level full factorial, fractional factorial (half, quarter)
and Plackett-Burman designs.

All designs use coded levels: -1 (Low) and +1 (High).
Run randomisation is applied by default to protect against lurking time trends.

Methodology follows Montgomery, "Design and Analysis of Experiments" (9th ed.)
and the AIAG / ASQ Design of Experiments handbook.

Usage
-----
    from analytics.doe import DOEFactor, recommend_design, design_matrix_chart, effects_plot

    factors = [
        DOEFactor("Temperature",  160.0, 200.0, "°C",  True),
        DOEFactor("Pressure",     1.0,   3.0,   "bar", True),
        DOEFactor("Feed Rate",    10.0,  20.0,  "g/s", True),
        DOEFactor("Catalyst",     "A",   "B",   "",    False),
    ]
    design = recommend_design(factors, budget_runs=20)
    chart  = design_matrix_chart(design)
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from typing import List, Optional, Union

import altair as alt
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DOEFactor:
    """Describes one experimental factor for a 2-level design."""

    name: str
    low_level:  Union[float, str]
    high_level: Union[float, str]
    units: str
    is_continuous: bool


@dataclass
class DOEDesign:
    """Complete experimental design specification."""

    design_type: str            # Human-readable design name
    n_factors: int
    n_levels: int               # Always 2 for these designs
    n_runs_full: int            # 2^k (full factorial runs)
    n_runs_design: int          # Actual runs (before replication/centre runs)
    resolution: str             # "III" | "IV" | "V" | "Full"
    fraction: str               # e.g. "1/2", "1/4", "Full"
    alias_structure: List[str]  # Confounding / aliasing relationships
    run_matrix: pd.DataFrame            # Coded design matrix (-1/+1)
    randomized_run_matrix: pd.DataFrame # Same matrix in random run order
    center_runs: int            # Recommended centre-point runs
    replicates: int             # Recommended replicates
    total_runs: int             # n_runs_design * replicates + center_runs
    interpretation: str         # What this design can estimate
    recommended_action: str


# ---------------------------------------------------------------------------
# Resolution descriptions
# ---------------------------------------------------------------------------

RESOLUTION_DESCRIPTIONS = {
    "III":  (
        "Resolution III: Main effects are confounded with 2-factor interactions (2FI). "
        "Use for initial screening only — cannot estimate interactions."
    ),
    "IV":   (
        "Resolution IV: Main effects are clear of 2FI, but 2FI are confounded with "
        "each other. Good for screening with some interaction information."
    ),
    "V":    (
        "Resolution V: All main effects and 2FI are estimable. "
        "Good for optimisation when interactions are expected."
    ),
    "Full": (
        "Full Factorial: All main effects, 2FI, and higher-order interactions are "
        "estimable. Use when budget allows and k ≤ 5."
    ),
}


# ---------------------------------------------------------------------------
# Design generators (standard alias generators from Montgomery tables)
# ---------------------------------------------------------------------------

# Maps (k, fraction_exponent) -> list of generator strings
# Generator format: "factor = product_of_factors"
# e.g. k=3, 2^(3-1) (half fraction): C = AB
STANDARD_GENERATORS: dict[tuple[int, int], list[str]] = {
    (3, 1):  ["C = AB"],                         # 2^(3-1), Res III
    (4, 1):  ["D = ABC"],                        # 2^(4-1), Res IV
    (5, 1):  ["E = ABCD"],                       # 2^(5-1), Res V
    (5, 2):  ["D = AB", "E = AC"],               # 2^(5-2), Res III
    (6, 1):  ["F = ABCDE"],                      # 2^(6-1), Res VI
    (6, 2):  ["E = ABC", "F = BCD"],             # 2^(6-2), Res IV
    (7, 1):  ["G = ABCDEF"],                     # 2^(7-1), Res VII
    (7, 2):  ["F = ABC", "G = ABD"],             # 2^(7-2), Res IV
    (7, 3):  ["E = ABC", "F = ABD", "G = ACD"],  # 2^(7-3), Res IV
    (8, 4):  ["E=BCD", "F=ACD", "G=ABC", "H=ABD"],  # 2^(8-4) Plackett-Burman-like, Res IV
}


def _get_generators(k: int, p: int) -> list[str]:
    """Return standard generator strings for 2^(k-p) design."""
    return STANDARD_GENERATORS.get((k, p), [f"(Custom generators for 2^({k}-{p}))"])


# ---------------------------------------------------------------------------
# Full Factorial Builder
# ---------------------------------------------------------------------------

def build_full_factorial(factors: List[DOEFactor]) -> pd.DataFrame:
    """
    Generate a 2^k full factorial design matrix in coded units (-1, +1).

    Parameters
    ----------
    factors : list[DOEFactor]

    Returns
    -------
    pd.DataFrame with columns = factor names, values ∈ {-1, +1}
    """
    k = len(factors)
    combinations = list(itertools.product([-1, 1], repeat=k))
    data = {f.name: [c[i] for c in combinations] for i, f in enumerate(factors)}
    df = pd.DataFrame(data)
    df.insert(0, "RunOrder", range(1, len(df) + 1))
    return df


# ---------------------------------------------------------------------------
# Half-Fraction Builder (2^(k-1))
# ---------------------------------------------------------------------------

def build_half_fraction(
    factors: List[DOEFactor],
    generator: Optional[str] = None,
) -> pd.DataFrame:
    """
    Generate a 2^(k-1) fractional factorial design matrix.

    For k ≤ 6, the last factor is generated as the product of all others
    (highest resolution generator I = ±123...k).
    The design principal fraction uses the positive defining relation.

    Parameters
    ----------
    factors : list[DOEFactor]
        The last factor in the list is the "generated" factor.
    generator : str, optional
        Override string (e.g. "E = ABCD") for documentation; actual
        generation always uses product-of-all-others for k ≤ 6.

    Returns
    -------
    pd.DataFrame coded design matrix.
    """
    k = len(factors)
    if k < 3:
        raise ValueError("Half fraction requires at least 3 factors.")

    base_factors = factors[:-1]        # k-1 base factors
    generated_factor = factors[-1]    # factor generated by the relation

    # Build base full factorial (2^(k-1) runs)
    base_combinations = list(itertools.product([-1, 1], repeat=k - 1))

    data: dict[str, list] = {}
    for i, f in enumerate(base_factors):
        data[f.name] = [c[i] for c in base_combinations]

    # Generate last factor = product of all base factor columns
    gen_col = [
        int(np.prod([c[i] for i in range(k - 1)]))
        for c in base_combinations
    ]
    data[generated_factor.name] = gen_col

    df = pd.DataFrame(data)
    df.insert(0, "RunOrder", range(1, len(df) + 1))
    return df


# ---------------------------------------------------------------------------
# Quarter-Fraction Builder (2^(k-2))
# ---------------------------------------------------------------------------

def _build_fraction(factors: List[DOEFactor], p: int) -> pd.DataFrame:
    """
    Generic 2^(k-p) fractional factorial using standard generators from the table.
    For p=2 (quarter fraction) of k=6 factors, uses E=ABC, F=BCD generators.
    For p=3 (eighth fraction) of k=7 factors, uses E=ABC, F=ABD, G=ACD.

    Parameters
    ----------
    factors : list[DOEFactor]
    p : int   Number of generators (fraction exponent).

    Returns
    -------
    pd.DataFrame coded design matrix.
    """
    k = len(factors)
    n_base = k - p
    if n_base < 2:
        raise ValueError(
            f"Not enough base factors. k={k}, p={p}, base factors needed = {n_base}."
        )

    base_factors = factors[:n_base]
    added_factors = factors[n_base:]

    # Build base full factorial
    base_combos = list(itertools.product([-1, 1], repeat=n_base))

    data: dict[str, list] = {}
    for i, f in enumerate(base_factors):
        data[f.name] = [c[i] for c in base_combos]

    # Apply generators: each added factor = product of some base factors
    # Generators are keyed by (k, p) in STANDARD_GENERATORS
    gen_strings = STANDARD_GENERATORS.get((k, p), [])

    for fi, added_f in enumerate(added_factors):
        gen_str = gen_strings[fi] if fi < len(gen_strings) else None
        if gen_str:
            # Parse RHS of "X = YZW..."
            rhs = gen_str.split("=")[1].strip().replace(" ", "")
            # RHS uses positional letters A, B, C, ... for base factors
            letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            base_letter_map = {letters[i]: f.name for i, f in enumerate(base_factors)}
            col_product = [1] * len(base_combos)
            for letter in rhs:
                if letter in base_letter_map:
                    col_name = base_letter_map[letter]
                    col_product = [
                        col_product[r] * data[col_name][r]
                        for r in range(len(base_combos))
                    ]
            data[added_f.name] = col_product
        else:
            # Default: product of first (fi+2) base factors
            cols_to_multiply = list(data.keys())[: fi + 2]
            col_product = [1] * len(base_combos)
            for col in cols_to_multiply:
                col_product = [col_product[r] * data[col][r] for r in range(len(base_combos))]
            data[added_f.name] = col_product

    # Reorder columns to match original factor order
    ordered_cols = [f.name for f in factors]
    df = pd.DataFrame({col: data[col] for col in ordered_cols})
    df.insert(0, "RunOrder", range(1, len(df) + 1))
    return df


# ---------------------------------------------------------------------------
# Plackett-Burman Design (for k up to 11 factors, 12 runs)
# ---------------------------------------------------------------------------

# PB-12 base row (Hadamard matrix H12, first row)
_PB12_BASE_ROW = [1, -1, 1, -1, -1, -1, 1, 1, 1, -1, 1]

def _build_plackett_burman_12(factors: List[DOEFactor]) -> pd.DataFrame:
    """
    Build a 12-run Plackett-Burman design for up to 11 factors.
    Uses cyclic generation from the standard PB-12 base row.
    """
    k = len(factors)
    if k > 11:
        raise ValueError("PB-12 supports at most 11 factors.")

    n_runs = 12
    base = _PB12_BASE_ROW

    # Generate 11-column Hadamard matrix by cyclic shifts
    matrix = []
    for i in range(11):
        shifted = base[i:] + base[:i]
        matrix.append(shifted)

    # Add the all-(-1) row
    matrix.append([-1] * 11)

    full_matrix = np.array(matrix)  # shape (12, 11)

    # Select first k columns
    data = {factors[j].name: list(full_matrix[:, j]) for j in range(k)}
    df = pd.DataFrame(data)
    df.insert(0, "RunOrder", range(1, n_runs + 1))
    return df


# ---------------------------------------------------------------------------
# Alias structure calculator
# ---------------------------------------------------------------------------

def _compute_alias_structure(factors: List[DOEFactor], p: int) -> list[str]:
    """
    Return human-readable aliasing relationships for a 2^(k-p) design.
    """
    k = len(factors)
    alias_list: list[str] = []

    if p == 0:
        alias_list.append("Full factorial — no aliasing.")
        return alias_list

    gen_strings = STANDARD_GENERATORS.get((k, p), [])
    if gen_strings:
        alias_list.append("Generator(s):")
        for gs in gen_strings:
            alias_list.append(f"  I = {gs.split('=')[1].strip()}{gs.split('=')[0].strip()}")
    else:
        alias_list.append(f"Standard generators not tabulated for k={k}, p={p}.")

    # Resolution-based aliasing summary
    if k - p <= 3:
        resolution = "III"
    elif k - p <= 4:
        resolution = "IV"
    else:
        resolution = "V"

    alias_list.append(RESOLUTION_DESCRIPTIONS.get(resolution, ""))
    return alias_list


# ---------------------------------------------------------------------------
# Design Recommendation
# ---------------------------------------------------------------------------

def recommend_design(
    factors: List[DOEFactor],
    budget_runs: Optional[int] = None,
) -> DOEDesign:
    """
    Select and build the appropriate experimental design for the given factors.

    Selection rules (Montgomery, Chapter 8):
        k ≤ 4                    → Full Factorial  (2^k runs)
        k == 5 and budget ≥ 32   → Full Factorial  (32 runs)
        k == 5                   → Half fraction   (16 runs, Res V)
        k == 6 and budget ≥ 32   → Half fraction   (32 runs, Res VI)
        k == 6                   → Quarter fraction (16 runs, Res IV)
        k == 7                   → Quarter fraction (32 runs, Res IV)
        k >= 8 and k ≤ 11        → Plackett-Burman (12 runs)
        k >= 12                  → Plackett-Burman (next multiple of 4 ≥ k+1)

    If budget_runs is specified, pick the largest design that fits within budget
    (excluding centre runs and replicates).

    Parameters
    ----------
    factors : list[DOEFactor]
    budget_runs : int, optional
        Maximum total runs available (excluding centre runs).

    Returns
    -------
    DOEDesign
    """
    k = len(factors)
    if k < 2:
        raise ValueError("At least 2 factors are required for a DOE design.")
    if k > 15:
        raise ValueError(
            "This module supports up to 15 factors. "
            "For larger screening studies, consider a Definitive Screening Design."
        )

    n_runs_full = 2 ** k

    # ------------------------------------------------------------------
    # Select design type based on k and budget
    # ------------------------------------------------------------------

    def _fits(n: int) -> bool:
        return budget_runs is None or n <= budget_runs

    if k <= 4:
        if _fits(n_runs_full):
            design_type = "Full Factorial"
            n_runs_design = n_runs_full
            resolution = "Full"
            fraction = "Full"
            p = 0
            run_matrix = build_full_factorial(factors)
        else:
            # Force a half-fraction
            n_runs_design = n_runs_full // 2
            design_type = f"Fractional Factorial (Resolution {'IV' if k == 4 else 'III'})"
            resolution = "IV" if k == 4 else "III"
            fraction = "1/2"
            p = 1
            run_matrix = build_half_fraction(factors)

    elif k == 5:
        if _fits(32):
            design_type = "Full Factorial"
            n_runs_design = 32
            resolution = "Full"
            fraction = "Full"
            p = 0
            run_matrix = build_full_factorial(factors)
        elif _fits(16):
            design_type = "Fractional Factorial (Resolution V)"
            n_runs_design = 16
            resolution = "V"
            fraction = "1/2"
            p = 1
            run_matrix = build_half_fraction(factors)
        else:
            # Quarter fraction (8 runs, Res III)
            design_type = "Fractional Factorial (Resolution III)"
            n_runs_design = 8
            resolution = "III"
            fraction = "1/4"
            p = 2
            run_matrix = _build_fraction(factors, 2)

    elif k == 6:
        if _fits(32):
            design_type = "Fractional Factorial (Resolution VI)"
            n_runs_design = 32
            resolution = "VI"
            fraction = "1/2"
            p = 1
            run_matrix = build_half_fraction(factors)
        elif _fits(16):
            design_type = "Fractional Factorial (Resolution IV)"
            n_runs_design = 16
            resolution = "IV"
            fraction = "1/4"
            p = 2
            run_matrix = _build_fraction(factors, 2)
        else:
            design_type = "Plackett-Burman (12 runs)"
            n_runs_design = 12
            resolution = "III"
            fraction = "PB-12"
            p = 0   # not a standard fraction — PB
            run_matrix = _build_plackett_burman_12(factors)

    elif k == 7:
        if _fits(32):
            design_type = "Fractional Factorial (Resolution IV)"
            n_runs_design = 32
            resolution = "IV"
            fraction = "1/4"
            p = 2
            run_matrix = _build_fraction(factors, 2)
        elif _fits(16):
            design_type = "Fractional Factorial (Resolution IV)"
            n_runs_design = 16
            resolution = "IV"
            fraction = "1/8"
            p = 3
            run_matrix = _build_fraction(factors, 3)
        else:
            design_type = "Plackett-Burman (12 runs)"
            n_runs_design = 12
            resolution = "III"
            fraction = "PB-12"
            p = 0
            run_matrix = _build_plackett_burman_12(factors)

    else:
        # k >= 8: use Plackett-Burman
        if k <= 11:
            design_type = "Plackett-Burman (12 runs)"
            n_runs_design = 12
            resolution = "III"
            fraction = "PB-12"
            p = 0
            run_matrix = _build_plackett_burman_12(factors)
        else:
            # PB-20 for 12–19 factors (next multiple of 4 above k)
            raise ValueError(
                f"k={k} factors: consider a Plackett-Burman 20-run design "
                "(not yet implemented in this module) or reduce to ≤ 11 factors."
            )

    # ------------------------------------------------------------------
    # Alias structure
    # ------------------------------------------------------------------
    alias_structure = _compute_alias_structure(factors, p if fraction != "PB-12" else 0)
    if fraction == "PB-12":
        alias_structure = [
            "Plackett-Burman design — main effects are partially confounded with 2FI.",
            "Main effects have complex aliasing; this design is for screening only.",
            "Do not attempt to estimate interactions from a PB design.",
        ]

    # ------------------------------------------------------------------
    # Recommended centre runs and replicates
    # ------------------------------------------------------------------
    n_continuous = sum(1 for f in factors if f.is_continuous)
    center_runs = 4 if n_continuous >= 2 else 0   # Centre runs only for continuous factors
    replicates  = 1   # Standard screening recommendation
    total_runs  = n_runs_design * replicates + center_runs

    # ------------------------------------------------------------------
    # Randomised run matrix
    # ------------------------------------------------------------------
    # Exclude RunOrder column for shuffling, then reassign
    factor_cols = [c for c in run_matrix.columns if c != "RunOrder"]
    shuffled_idx = list(range(len(run_matrix)))
    random.shuffle(shuffled_idx)
    randomized_data = run_matrix[factor_cols].iloc[shuffled_idx].reset_index(drop=True)
    randomized_data.insert(0, "RunOrder", range(1, len(randomized_data) + 1))
    randomized_run_matrix = randomized_data

    # ------------------------------------------------------------------
    # Interpretation text
    # ------------------------------------------------------------------
    res_desc = RESOLUTION_DESCRIPTIONS.get(
        resolution if resolution != "VI" else "V",  # VI treated as V+ for text
        f"Resolution {resolution} design.",
    )
    if resolution == "VI":
        res_desc = (
            "Resolution VI: All main effects and 2FI are estimable and clear of "
            "3FI. This is a high-quality design for optimisation."
        )

    factor_list = ", ".join(f.name for f in factors)
    interpretation = (
        f"{design_type} with k={k} factors ({factor_list}).  "
        f"Fraction: {fraction}.  Runs: {n_runs_design} (plus {center_runs} centre "
        f"runs = {total_runs} total).  "
        f"{res_desc}"
    )

    # ------------------------------------------------------------------
    # Recommended action
    # ------------------------------------------------------------------
    if resolution in ("Full", "VI", "V"):
        recommended_action = (
            "This design supports full main effect and 2FI estimation. "
            "Add centre runs to check for curvature. "
            "Analyse using ANOVA or regression with interaction terms."
        )
    elif resolution == "IV":
        recommended_action = (
            "Screening design — useful for identifying significant main effects. "
            "2FI are partially confounded; follow up with a Resolution V design "
            "if interactions are significant."
        )
    elif resolution == "III":
        recommended_action = (
            "Coarse screening only. Main effects are aliased with 2FI — "
            "do not interpret main effects without follow-up experimentation. "
            "This design is best for identifying which factors to study further."
        )
    else:  # PB
        recommended_action = (
            "Plackett-Burman screening design. Identify top 3–5 significant "
            "factors, then conduct a follow-up factorial or RSM design with "
            "those factors to estimate interactions and find optimum settings."
        )

    return DOEDesign(
        design_type=design_type,
        n_factors=k,
        n_levels=2,
        n_runs_full=n_runs_full,
        n_runs_design=n_runs_design,
        resolution=resolution,
        fraction=fraction,
        alias_structure=alias_structure,
        run_matrix=run_matrix,
        randomized_run_matrix=randomized_run_matrix,
        center_runs=center_runs,
        replicates=replicates,
        total_runs=total_runs,
        interpretation=interpretation,
        recommended_action=recommended_action,
    )


# ---------------------------------------------------------------------------
# Chart: Design Matrix Heatmap
# ---------------------------------------------------------------------------

def design_matrix_chart(design: DOEDesign) -> alt.Chart:
    """
    Heatmap visualisation of the run matrix.

    x-axis : factor names
    y-axis : run number (top = run 1)
    color  : -1 = light blue, +1 = dark blue

    Returns
    -------
    alt.Chart
    """
    matrix = design.randomized_run_matrix.copy()
    factor_cols = [c for c in matrix.columns if c != "RunOrder"]

    # Melt to long form for Altair
    long_rows = []
    for _, row in matrix.iterrows():
        run = int(row["RunOrder"])
        for col in factor_cols:
            long_rows.append(
                {
                    "RunOrder": run,
                    "Factor":   col,
                    "Level":    int(row[col]),
                    "Label":    "High (+1)" if row[col] == 1 else "Low (−1)",
                }
            )
    df_long = pd.DataFrame(long_rows)

    n_rows = len(matrix)
    height = max(180, n_rows * 22)

    heatmap = (
        alt.Chart(df_long, title="Run Matrix — Coded (−1 = Low, +1 = High)")
        .mark_rect(stroke="white", strokeWidth=1)
        .encode(
            x=alt.X(
                "Factor:N",
                sort=factor_cols,
                axis=alt.Axis(labelAngle=-20, title="Factor"),
            ),
            y=alt.Y(
                "RunOrder:O",
                sort="ascending",
                axis=alt.Axis(title="Run Order"),
            ),
            color=alt.Color(
                "Level:O",
                scale=alt.Scale(
                    domain=[-1, 1],
                    range=["#BFD7EA", "#1D3557"],
                ),
                legend=alt.Legend(title="Level"),
            ),
            tooltip=[
                alt.Tooltip("RunOrder:O", title="Run"),
                alt.Tooltip("Factor:N"),
                alt.Tooltip("Label:N", title="Level"),
            ],
        )
        .properties(width=max(300, len(factor_cols) * 55), height=height)
    )

    # Text labels (-1 / +1)
    text_layer = (
        alt.Chart(df_long)
        .mark_text(fontSize=10, fontWeight="bold")
        .encode(
            x=alt.X("Factor:N", sort=factor_cols),
            y=alt.Y("RunOrder:O", sort="ascending"),
            text=alt.Text("Level:O"),
            color=alt.condition(
                alt.datum.Level == 1,
                alt.value("white"),
                alt.value("#1D3557"),
            ),
        )
    )

    return (
        (heatmap + text_layer)
        .configure_view(stroke=None)
        .configure_axis(grid=False)
    )


# ---------------------------------------------------------------------------
# Chart: Main Effects Plot
# ---------------------------------------------------------------------------

def effects_plot(
    factor_names: List[str],
    effects: List[float],
) -> alt.Chart:
    """
    Horizontal bar chart of main effects magnitudes.

    Color: positive effect = #06D6A0 (green), negative = #EF233C (red).
    Sorted by absolute effect magnitude (largest at top).
    Reference line at 0.

    Parameters
    ----------
    factor_names : list[str]
        Names of factors (must match length of effects).
    effects : list[float]
        Estimated main effect for each factor (y_high - y_low) / 2 convention
        or simply the raw contrast divided by the number of runs/2.

    Returns
    -------
    alt.LayerChart
    """
    if len(factor_names) != len(effects):
        raise ValueError("factor_names and effects must have the same length.")

    df = pd.DataFrame(
        {
            "Factor": factor_names,
            "Effect": effects,
            "AbsEffect": [abs(e) for e in effects],
            "Direction": ["Positive" if e >= 0 else "Negative" for e in effects],
        }
    )
    df.sort_values("AbsEffect", ascending=True, inplace=True)

    color_scale = alt.Scale(
        domain=["Positive", "Negative"],
        range=["#06D6A0", "#EF233C"],
    )

    bars = (
        alt.Chart(df, title="Main Effects Plot")
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
        .encode(
            y=alt.Y(
                "Factor:N",
                sort=list(df["Factor"]),
                axis=alt.Axis(title=None),
            ),
            x=alt.X(
                "Effect:Q",
                axis=alt.Axis(title="Estimated Main Effect"),
                scale=alt.Scale(zero=True),
            ),
            color=alt.Color(
                "Direction:N",
                scale=color_scale,
                legend=alt.Legend(title="Direction"),
            ),
            tooltip=[
                alt.Tooltip("Factor:N"),
                alt.Tooltip("Effect:Q", format=".4g"),
                alt.Tooltip("Direction:N"),
            ],
        )
        .properties(width=500, height=max(200, len(factor_names) * 30))
    )

    # Value labels
    label_layer = (
        alt.Chart(df)
        .mark_text(align="left", dx=5, fontSize=10, color="#333333")
        .encode(
            y=alt.Y("Factor:N", sort=list(df["Factor"])),
            x=alt.X("Effect:Q"),
            text=alt.Text("Effect:Q", format=".3g"),
        )
    )

    zero_line = (
        alt.Chart(pd.DataFrame({"x": [0]}))
        .mark_rule(color="#888888", strokeWidth=1.5)
        .encode(x=alt.X("x:Q"))
    )

    return (
        alt.layer(bars, zero_line, label_layer)
        .configure_view(stroke=None)
        .configure_axis(grid=True, gridColor="#EEEEEE")
    )


# ---------------------------------------------------------------------------
# Utility: decode run matrix back to actual factor levels
# ---------------------------------------------------------------------------

def decode_run_matrix(
    design: DOEDesign,
    factors: List[DOEFactor],
    use_randomized: bool = True,
) -> pd.DataFrame:
    """
    Convert coded (-1/+1) run matrix to actual factor levels for field use.

    Parameters
    ----------
    design : DOEDesign
    factors : list[DOEFactor]
    use_randomized : bool
        If True, use the randomised run order (recommended for execution).

    Returns
    -------
    pd.DataFrame with actual (decoded) factor levels.
    """
    matrix = design.randomized_run_matrix if use_randomized else design.run_matrix
    decoded = matrix.copy()
    for f in factors:
        if f.name not in decoded.columns:
            continue
        if f.is_continuous:
            low  = float(f.low_level)
            high = float(f.high_level)
            decoded[f.name] = decoded[f.name].map(
                {-1: low, 1: high}
            )
            decoded.rename(
                columns={f.name: f"{f.name} ({f.units})" if f.units else f.name},
                inplace=True,
            )
        else:
            decoded[f.name] = decoded[f.name].map(
                {-1: str(f.low_level), 1: str(f.high_level)}
            )

    decoded.insert(len(decoded.columns), "Response (Y)", "")  # blank column for data entry
    return decoded


# ---------------------------------------------------------------------------
# Utility: design summary table
# ---------------------------------------------------------------------------

def doe_summary_table(design: DOEDesign) -> pd.DataFrame:
    """Return a one-row summary DataFrame suitable for display."""
    return pd.DataFrame(
        [
            {
                "Design Type":       design.design_type,
                "Factors (k)":       design.n_factors,
                "Full Factorial Runs": design.n_runs_full,
                "Design Runs":       design.n_runs_design,
                "Centre Runs":       design.center_runs,
                "Replicates":        design.replicates,
                "Total Runs":        design.total_runs,
                "Resolution":        design.resolution,
                "Fraction":          design.fraction,
            }
        ]
    )
