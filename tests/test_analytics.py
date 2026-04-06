"""
test_analytics.py
=================
Complete unit-test suite for the LLM-powered Lean Six Sigma analytics modules.

Covers:
    - analytics.capability   (run_capability, CapabilityResult)
    - analytics.hypothesis_tests (one_sample_t, two_sample_t, chi_square_independence)
    - analytics.spc          (imr_chart, xbar_r_chart, p_chart, SPCResult)
    - analytics.msa          (run_gauge_rr, MSAResult)
    - analytics.fmea         (new_entry, fmea_pareto_chart, FMEAEntry)
    - analytics.benefits     (run_benefits_analysis, CostOfQualityEntry, BenefitsResult)
    - analytics.regression   (simple_regression, multiple_regression, RegressionResult)
    - analytics.doe          (recommend_design, DOEFactor, DOEDesign)

Run with:
    python -m pytest tests/test_analytics.py -v
  or:
    python tests/test_analytics.py
"""

from __future__ import annotations

import math
import sys
import os
import unittest

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Make sure the project root is on sys.path so imports resolve regardless
# of how the test runner is invoked.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from analytics.capability import run_capability
from analytics.hypothesis_tests import (
    one_sample_t,
    two_sample_t,
    chi_square_independence,
)
from analytics.spc import imr_chart, xbar_r_chart, p_chart, SPCResult
from analytics.msa import run_gauge_rr, MSAResult
from analytics.fmea import new_entry, fmea_pareto_chart
from analytics.benefits import (
    run_benefits_analysis,
    CostOfQualityEntry,
)
from analytics.regression import (
    simple_regression,
    multiple_regression,
)
from analytics.doe import recommend_design, DOEFactor

try:
    import importlib
    importlib.import_module("altair")
    _HAS_ALTAIR = True
except ImportError:
    _HAS_ALTAIR = False


# ===========================================================================
# TestCapability
# ===========================================================================

class TestCapability(unittest.TestCase):
    """Tests for analytics.capability.run_capability."""

    def test_perfect_process(self):
        """
        LSL=90, USL=110, data from N(100, 1, n=100).
        A very tight process should yield Cpk > 3.0 and Cp > 3.0.
        """
        np.random.seed(42)
        data = np.random.normal(100, 1, 100).tolist()
        result = run_capability(data, lsl=90, usl=110)
        self.assertIsNotNone(result.cpk)
        self.assertIsNotNone(result.cp)
        self.assertGreater(result.cpk, 3.0)
        self.assertGreater(result.cp, 3.0)

    def test_borderline_capable(self):
        """
        LSL=90, USL=110, data from N(100, 3.3, n=200).
        With sigma ~3.3 and tolerance 20, Cpk should be close to 1.0 (0.9 to 1.1).
        """
        np.random.seed(42)
        data = np.random.normal(100, 3.3, 200).tolist()
        result = run_capability(data, lsl=90, usl=110)
        self.assertIsNotNone(result.cpk)
        self.assertGreater(result.cpk, 0.9)
        self.assertLess(result.cpk, 1.1)

    def test_off_center_process(self):
        """
        Mean shifted to 105, USL=110, LSL=90.
        An off-centre process should have Cpk < Cp because the mean is closer
        to one specification limit than to the other.
        """
        np.random.seed(42)
        data = np.random.normal(105, 1.5, 100).tolist()
        result = run_capability(data, lsl=90, usl=110)
        self.assertIsNotNone(result.cpk)
        self.assertIsNotNone(result.cp)
        self.assertLess(result.cpk, result.cp)

    def test_sigma_level_world_class(self):
        """
        A highly capable process (tight distribution) should yield sigma_level >= 4.0.
        """
        np.random.seed(42)
        data = np.random.normal(100, 1, 100).tolist()
        result = run_capability(data, lsl=90, usl=110)
        self.assertIsNotNone(result.sigma_level)
        self.assertGreater(result.sigma_level, 4.0)

    def test_dpm_high_for_poor_process(self):
        """
        A very poor process (sigma ~3, tolerance 6 => Cpk ~0.33) should produce
        a DPM well above 100 000.
        """
        np.random.seed(42)
        data = np.random.normal(100, 3, 200).tolist()
        result = run_capability(data, lsl=97, usl=103)
        self.assertGreater(result.dpm, 100_000)

    def test_result_has_required_fields(self):
        """
        CapabilityResult must expose cp, cpk, pp, ppk, sigma_level, and dpm.
        """
        np.random.seed(42)
        data = np.random.normal(50, 2, 50).tolist()
        result = run_capability(data, lsl=40, usl=60)
        for attr in ("cp", "cpk", "pp", "ppk", "sigma_level", "dpm"):
            self.assertTrue(hasattr(result, attr), f"Missing attribute: {attr}")


# ===========================================================================
# TestHypothesisTests
# ===========================================================================

class TestHypothesisTests(unittest.TestCase):
    """Tests for analytics.hypothesis_tests."""

    def test_one_sample_t_reject(self):
        """
        Data drawn from N(110, 2) tested against H0: mu=100.
        The mean is 10 units above target — should strongly reject H0 (p < 0.05).
        """
        np.random.seed(42)
        data = np.random.normal(110, 2, 50).tolist()
        result = one_sample_t(data, target=100)
        self.assertLess(result.p_value, 0.05)
        self.assertTrue(result.reject_h0)

    def test_one_sample_t_fail_to_reject(self):
        """
        Data drawn from N(100, 2) tested against H0: mu=100.
        The true mean equals the target — should fail to reject H0 (p > 0.05).
        """
        np.random.seed(42)
        data = np.random.normal(100, 2, 50).tolist()
        result = one_sample_t(data, target=100)
        self.assertGreater(result.p_value, 0.05)
        self.assertFalse(result.reject_h0)

    def test_two_sample_t_different_groups(self):
        """
        Group A from N(100, 2), Group B from N(115, 2) — clearly different means.
        Should reject H0: muA == muB (p < 0.05).
        """
        np.random.seed(42)
        group_a = np.random.normal(100, 2, 50).tolist()
        group_b = np.random.normal(115, 2, 50).tolist()
        result = two_sample_t(group_a, group_b)
        self.assertLess(result.p_value, 0.05)
        self.assertTrue(result.reject_h0)

    def test_two_sample_t_same_groups(self):
        """
        Both groups drawn from N(100, 2) — same distribution.
        Should fail to reject H0: muA == muB (p > 0.05).
        """
        np.random.seed(42)
        group_a = np.random.normal(100, 2, 50).tolist()
        group_b = np.random.normal(100, 2, 50).tolist()
        result = two_sample_t(group_a, group_b)
        self.assertGreater(result.p_value, 0.05)

    def test_chi_square_independence(self):
        """
        Strongly dependent contingency table: [[90, 10], [10, 90]].
        Chi-square should detect the dependence (p < 0.05).
        """
        table = [[90, 10], [10, 90]]
        result = chi_square_independence(table)
        self.assertLess(result.p_value, 0.05)
        self.assertTrue(result.reject_h0)

    def test_result_has_interpretation(self):
        """
        HypothesisResult.interpretation must be a non-empty string.
        """
        np.random.seed(42)
        data = np.random.normal(100, 5, 30).tolist()
        result = one_sample_t(data, target=100)
        self.assertIsInstance(result.interpretation, str)
        self.assertGreater(len(result.interpretation.strip()), 0)


# ===========================================================================
# TestSPC
# ===========================================================================

class TestSPC(unittest.TestCase):
    """Tests for analytics.spc."""

    def test_imr_stable_process(self):
        """
        30 points from N(50, 1): a stable process.
        Expected: no or very few OOC signals.
        The OOC point count should be much less than 30.
        """
        np.random.seed(42)
        data = np.random.normal(50, 1, 30).tolist()
        result, _ = imr_chart(data)
        self.assertIsInstance(result, SPCResult)
        # A stable normal process should produce very few false signals
        self.assertLess(len(result.ooc_points), 5)

    def test_imr_out_of_control(self):
        """
        Inject a point 8 sigma above the mean into otherwise stable data.
        The I-MR chart must detect at least one OOC signal.
        """
        np.random.seed(42)
        data = np.random.normal(50, 1, 30).tolist()
        data[15] = 50 + 8 * 1  # spike at position 15 (8 sigma above mean)
        result, _ = imr_chart(data)
        self.assertGreater(len(result.ooc_points), 0)
        self.assertFalse(result.is_in_control)

    def test_imr_result_has_ucl_lcl(self):
        """
        SPCResult from imr_chart must have ucl and lcl attributes with finite values.
        """
        np.random.seed(42)
        data = np.random.normal(50, 1, 20).tolist()
        result, _ = imr_chart(data)
        self.assertTrue(hasattr(result, "ucl"))
        self.assertTrue(hasattr(result, "lcl"))
        self.assertTrue(math.isfinite(result.ucl))
        self.assertTrue(math.isfinite(result.lcl))
        self.assertGreater(result.ucl, result.lcl)

    def test_xbar_r_subgroups(self):
        """
        Pass 6 subgroups of 4 measurements each.
        SPCResult should be returned and have subgroup xbar values stored (centerline set).
        """
        np.random.seed(42)
        subgroups = [
            np.random.normal(50, 1, 4).tolist()
            for _ in range(6)
        ]
        result, _ = xbar_r_chart(subgroups)
        self.assertIsInstance(result, SPCResult)
        self.assertEqual(result.chart_type, "Xbar-R")
        self.assertTrue(math.isfinite(result.centerline))
        self.assertTrue(math.isfinite(result.ucl))
        self.assertTrue(math.isfinite(result.lcl))

    def test_p_chart_basic(self):
        """
        Pass proportions data (defectives and sample sizes).
        p-chart should compute a centerline between 0 and 1.
        """
        np.random.seed(42)
        sample_sizes = [100] * 20
        # Approximately 5% defect rate with random variation
        defectives = [int(np.random.binomial(100, 0.05)) for _ in range(20)]
        result, _ = p_chart(defectives, sample_sizes)
        self.assertIsInstance(result, SPCResult)
        self.assertEqual(result.chart_type, "p-chart")
        self.assertGreater(result.centerline, 0.0)
        self.assertLess(result.centerline, 1.0)
        self.assertGreater(result.ucl, result.centerline)


# ===========================================================================
# TestMSA
# ===========================================================================

class TestMSA(unittest.TestCase):
    """Tests for analytics.msa.run_gauge_rr."""

    @staticmethod
    def _make_msa_dataframe(n_parts, n_operators, n_reps,
                            part_variation, measurement_noise,
                            operator_bias=None, seed=42):
        """
        Build a balanced long-form MSA DataFrame.

        Parameters
        ----------
        n_parts : int
        n_operators : int
        n_reps : int
        part_variation : float
            Std dev of true part-to-part values.
        measurement_noise : float
            Std dev of repeatability (equipment) noise.
        operator_bias : list[float] or None
            Per-operator systematic offset; defaults to all zeros.
        seed : int
        """
        np.random.seed(seed)
        if operator_bias is None:
            operator_bias = [0.0] * n_operators

        true_part_values = np.random.normal(50, part_variation, n_parts)

        rows = []
        for p_idx in range(n_parts):
            for o_idx in range(n_operators):
                for _ in range(n_reps):
                    measurement = (
                        true_part_values[p_idx]
                        + operator_bias[o_idx]
                        + np.random.normal(0, measurement_noise)
                    )
                    rows.append({
                        "Part":     f"P{p_idx + 1}",
                        "Operator": f"Op{o_idx + 1}",
                        "Value":    measurement,
                    })
        return pd.DataFrame(rows)

    def test_good_gauge_rr(self):
        """
        High part variation (5.0) and very low measurement noise (0.1).
        GRR% (study) should be well below 10%.
        """
        df = self._make_msa_dataframe(
            n_parts=10, n_operators=3, n_reps=3,
            part_variation=5.0, measurement_noise=0.1,
        )
        result = run_gauge_rr(df, "Part", "Operator", "Value")
        self.assertIsInstance(result, MSAResult)
        self.assertLess(result.pct_grr_study, 10.0)

    def test_poor_gauge_rr(self):
        """
        Low part variation (0.5) and high measurement noise (2.0).
        GRR% (study) should exceed 30%.
        """
        df = self._make_msa_dataframe(
            n_parts=10, n_operators=3, n_reps=3,
            part_variation=0.5, measurement_noise=2.0,
        )
        result = run_gauge_rr(df, "Part", "Operator", "Value")
        self.assertGreater(result.pct_grr_study, 30.0)

    def test_ndc_good_system(self):
        """
        A good measurement system (low noise relative to part variation)
        should yield NDC >= 5 (able to distinguish at least 5 categories of parts).
        """
        df = self._make_msa_dataframe(
            n_parts=10, n_operators=3, n_reps=3,
            part_variation=5.0, measurement_noise=0.1,
        )
        result = run_gauge_rr(df, "Part", "Operator", "Value")
        self.assertGreaterEqual(result.ndc, 5)

    def test_result_fields_present(self):
        """
        MSAResult must expose pct_grr_study, pct_grr_tolerance, repeatability_var,
        and reproducibility_var fields (as defined in MSAResult dataclass).
        """
        df = self._make_msa_dataframe(
            n_parts=8, n_operators=2, n_reps=2,
            part_variation=3.0, measurement_noise=0.5,
        )
        result = run_gauge_rr(df, "Part", "Operator", "Value",
                              lsl=40.0, usl=60.0)
        for attr in ("pct_grr_study", "pct_grr_tolerance",
                     "repeatability_var", "reproducibility_var"):
            self.assertTrue(hasattr(result, attr), f"Missing attribute: {attr}")
        # With tolerance supplied, pct_grr_tolerance should be positive
        self.assertGreater(result.pct_grr_tolerance, 0.0)


# ===========================================================================
# TestFMEA
# ===========================================================================

class TestFMEA(unittest.TestCase):
    """Tests for analytics.fmea."""

    def test_rpn_calculation(self):
        """
        S=8, O=7, D=6 => RPN must equal 336 (8*7*6).
        """
        entry = new_entry(
            process_step="Assembly",
            failure_mode="Missing component",
            failure_effect="Product non-functional",
            failure_cause="Operator error",
            current_controls="Visual check",
            severity=8,
            occurrence=7,
            detection=6,
        )
        self.assertEqual(entry.rpn, 336)

    def test_high_risk_threshold(self):
        """
        RPN >= 200 (here 8*7*6=336) or S >= 9 should produce action_priority == 'High'.
        Test both: RPN >= 200 case and severity >= 9 case.
        """
        # RPN >= 200 case
        entry_rpn = new_entry(
            process_step="Welding",
            failure_mode="Crack",
            failure_effect="Structural failure",
            failure_cause="Material defect",
            current_controls="NDT inspection",
            severity=8,
            occurrence=6,
            detection=5,  # 8*6*5 = 240 >= 200
        )
        self.assertEqual(entry_rpn.action_priority, "High")

        # Severity >= 9 case (even with low RPN)
        entry_sev = new_entry(
            process_step="Braking",
            failure_mode="Brake failure",
            failure_effect="Safety hazard",
            failure_cause="Fluid leak",
            current_controls="Pressure test",
            severity=9,
            occurrence=1,
            detection=1,  # RPN=9 but severity=9 => High
        )
        self.assertEqual(entry_sev.action_priority, "High")

    def test_medium_risk_threshold(self):
        """
        RPN around 100 (>=80, <200) with severity < 9 should produce
        action_priority == 'Medium'.
        """
        entry = new_entry(
            process_step="Painting",
            failure_mode="Surface defect",
            failure_effect="Cosmetic issue",
            failure_cause="Contamination",
            current_controls="Visual inspection",
            severity=5,
            occurrence=5,
            detection=4,  # 5*5*4 = 100 => Medium
        )
        self.assertEqual(entry.action_priority, "Medium")
        self.assertEqual(entry.rpn, 100)

    def test_pareto_chart_type(self):
        """
        fmea_pareto_chart should return an Altair chart object
        (has a to_dict method or is an alt.Chart / alt.LayerChart).
        """
        if not _HAS_ALTAIR:
            self.skipTest("altair not installed")
        entries = [
            new_entry("Step A", "Mode 1", "Effect 1", "Cause 1", "Control 1",
                      severity=8, occurrence=7, detection=6),
            new_entry("Step B", "Mode 2", "Effect 2", "Cause 2", "Control 2",
                      severity=5, occurrence=4, detection=3),
        ]
        chart = fmea_pareto_chart(entries)
        self.assertTrue(
            hasattr(chart, "to_dict"),
            "fmea_pareto_chart should return an Altair chart (has to_dict)."
        )


# ===========================================================================
# TestBenefits
# ===========================================================================

class TestBenefits(unittest.TestCase):
    """Tests for analytics.benefits.run_benefits_analysis."""

    @staticmethod
    def _make_entries(hard_savings_total: float, soft_savings_total: float):
        """Helper: build minimal CostOfQualityEntry list."""
        return [
            CostOfQualityEntry(
                category="Internal Failure",
                description="Scrap",
                annual_cost=hard_savings_total,
                is_hard_saving=True,
            ),
            CostOfQualityEntry(
                category="Appraisal",
                description="Inspection labour",
                annual_cost=soft_savings_total,
                is_hard_saving=False,
            ),
        ]

    def test_roi_calculation(self):
        """
        Implementation cost = $100 000, projected savings from COPQ = $200 000 at 100%
        improvement => net_benefit_year1 = $100 000 => roi_pct should be ~100%.
        """
        entries = self._make_entries(200_000, 0)
        result = run_benefits_analysis(
            copq_entries=entries,
            projected_improvement_pct=100.0,
            implementation_cost=100_000,
            discount_rate=0.10,
            confidence="High",
        )
        self.assertAlmostEqual(result.roi_pct, 100.0, places=1)

    def test_payback_period(self):
        """
        Implementation cost = $120 000, total annual savings = $120 000
        (at 100% improvement) => payback_months = 12.
        """
        entries = self._make_entries(120_000, 0)
        result = run_benefits_analysis(
            copq_entries=entries,
            projected_improvement_pct=100.0,
            implementation_cost=120_000,
            discount_rate=0.10,
            confidence="Medium",
        )
        self.assertAlmostEqual(result.payback_months, 12.0, places=1)

    def test_npv_positive_good_project(self):
        """
        Large savings ($500 000/yr at 100% improvement) vs small implementation cost
        ($100 000) => npv_3yr must be positive.
        """
        entries = self._make_entries(500_000, 0)
        result = run_benefits_analysis(
            copq_entries=entries,
            projected_improvement_pct=100.0,
            implementation_cost=100_000,
            discount_rate=0.10,
            confidence="High",
        )
        self.assertGreater(result.npv_3yr, 0)

    def test_npv_negative_bad_project(self):
        """
        Tiny savings ($1 000/yr at 100% improvement) vs large implementation cost
        ($1 000 000) => npv_3yr must be negative.
        """
        entries = self._make_entries(1_000, 0)
        result = run_benefits_analysis(
            copq_entries=entries,
            projected_improvement_pct=100.0,
            implementation_cost=1_000_000,
            discount_rate=0.10,
            confidence="Low",
        )
        self.assertLess(result.npv_3yr, 0)

    def test_result_fields(self):
        """
        BenefitsResult must expose total_copq, total_projected_savings,
        implementation_cost, roi_pct, payback_months, and npv_3yr.
        """
        entries = self._make_entries(100_000, 50_000)
        result = run_benefits_analysis(
            copq_entries=entries,
            projected_improvement_pct=50.0,
            implementation_cost=30_000,
        )
        for attr in (
            "total_copq",
            "total_projected_savings",
            "implementation_cost",
            "roi_pct",
            "payback_months",
            "npv_3yr",
        ):
            self.assertTrue(hasattr(result, attr), f"Missing attribute: {attr}")


# ===========================================================================
# TestRegression
# ===========================================================================

class TestRegression(unittest.TestCase):
    """Tests for analytics.regression."""

    def test_perfect_linear_relationship(self):
        """
        y = 2x + 5 plus tiny noise => R-squared should be > 0.99.
        """
        np.random.seed(42)
        x = list(range(1, 51))
        y = [2.0 * xi + 5.0 + np.random.normal(0, 0.01) for xi in x]
        result = simple_regression(x, y, x_name="X", y_name="Y")
        self.assertGreater(result.r_squared, 0.99)

    def test_no_relationship(self):
        """
        Random x and random y with no relationship => R-squared should be < 0.2.
        """
        np.random.seed(42)
        x = np.random.uniform(0, 100, 60).tolist()
        y = np.random.uniform(0, 100, 60).tolist()
        result = simple_regression(x, y, x_name="X", y_name="Y")
        self.assertLess(result.r_squared, 0.2)

    def test_coefficients_direction(self):
        """
        Positive linear relationship => the slope coefficient for X should be positive.
        """
        np.random.seed(42)
        x = list(range(1, 31))
        y = [3.0 * xi + np.random.normal(0, 1) for xi in x]
        result = simple_regression(x, y, x_name="X", y_name="Y")
        slope = result.coefficients.get("X")
        self.assertIsNotNone(slope)
        self.assertGreater(slope, 0.0)

    def test_multiple_regression(self):
        """
        y = 3*x1 + 2*x2 + small noise; both predictors should be significant (p < 0.05).
        """
        np.random.seed(42)
        n = 80
        x1 = np.random.uniform(0, 10, n)
        x2 = np.random.uniform(0, 10, n)
        y = 3.0 * x1 + 2.0 * x2 + np.random.normal(0, 0.5, n)

        X_df = pd.DataFrame({"x1": x1, "x2": x2})
        result = multiple_regression(X_df, y.tolist(), y_name="Y")

        self.assertGreater(result.r_squared, 0.90)
        # Both predictors should appear in significant_predictors
        self.assertIn("x1", result.significant_predictors)
        self.assertIn("x2", result.significant_predictors)

    def test_result_has_required_fields(self):
        """
        RegressionResult must expose r_squared, coefficients, and p_values.
        """
        np.random.seed(42)
        x = list(range(1, 21))
        y = [2.0 * xi + np.random.normal(0, 1) for xi in x]
        result = simple_regression(x, y)
        for attr in ("r_squared", "coefficients", "p_values"):
            self.assertTrue(hasattr(result, attr), f"Missing attribute: {attr}")
        self.assertIsInstance(result.coefficients, dict)
        self.assertIsInstance(result.p_values, dict)


# ===========================================================================
# TestDOE
# ===========================================================================

class TestDOE(unittest.TestCase):
    """Tests for analytics.doe.recommend_design."""

    @staticmethod
    def _make_factors(k: int) -> list:
        """Return k generic continuous DOEFactor objects."""
        return [
            DOEFactor(
                name=f"Factor{i + 1}",
                low_level=float(i),
                high_level=float(i + 10),
                units="units",
                is_continuous=True,
            )
            for i in range(k)
        ]

    def test_2_factor_full_factorial(self):
        """
        2 factors => 2^2 = 4 runs. Should select a Full Factorial design.
        """
        factors = self._make_factors(2)
        design = recommend_design(factors)
        self.assertEqual(design.n_runs_design, 4)
        self.assertIn("Full", design.design_type)

    def test_3_factor_full_factorial(self):
        """
        3 factors => 2^3 = 8 runs. Should select a Full Factorial design.
        """
        factors = self._make_factors(3)
        design = recommend_design(factors)
        self.assertEqual(design.n_runs_design, 8)
        self.assertIn("Full", design.design_type)

    def test_4_factor_full_factorial(self):
        """
        4 factors => 2^4 = 16 runs. Should select a Full Factorial design.
        """
        factors = self._make_factors(4)
        design = recommend_design(factors)
        self.assertEqual(design.n_runs_design, 16)
        self.assertIn("Full", design.design_type)

    def test_5_factor_half_fraction(self):
        """
        5 factors with budget_runs=16 forces a half-fraction (2^(5-1) = 16 runs,
        Resolution V). n_runs_design must equal 16.
        """
        factors = self._make_factors(5)
        design = recommend_design(factors, budget_runs=16)
        self.assertEqual(design.n_runs_design, 16)
        self.assertEqual(design.fraction, "1/2")


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
