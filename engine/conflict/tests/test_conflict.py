"""
test_conflict.py
PRISM Engine — Conflict Index unit tests.

Tests:
1. Sanity case — aligned student and parent produce near-zero conflict.
2. Opposite risk appetite produces high risk gap.
3. Domain preference divergence on a shared domain.
4. Relocation mismatch.
5. Time-to-income mismatch.
6. Per-career conflict: student loves a risky route, parent hates it.
7. Config with_penalty enters composite scoring.
8. Property tests: conflict in [0, 1], determinism.
"""

import pytest
from types import SimpleNamespace
from dataclasses import dataclass

from engine.conflict.config import ConflictConfig, DEFAULT_CONFIG
from engine.conflict.scores import (
    compute_overall_conflict,
    compute_career_conflict,
    evaluate_conflict,
)
from engine.conflict.models import (
    OverallConflictReport,
    CareerConflictReport,
)


def _make_student(**kw) -> SimpleNamespace:
    """Build a student-like object with shared dimensions."""
    defaults = dict(
        risk_appetite=0.5,
        domain_preference={"Technology & Engineering": 5, "Healthcare & Medicine": 3},
        relocation_willingness=0.5,
        max_years_to_income=4.0,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _make_parent(**kw) -> SimpleNamespace:
    """Build a parent-like object (ParentProfile-compatible attributes)."""
    defaults = dict(
        risk=0.5,
        domain_ratings={"Technology & Engineering": 5, "Healthcare & Medicine": 3},
        relocation_willingness=0.5,
        max_years_to_income=4.0,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _make_route(**kw) -> SimpleNamespace:
    """Build a route-like object with shared dimension attributes."""
    defaults = dict(
        career_id="test_career",
        route_id="route_1",
        career_risk=0.5,
        domain="Technology & Engineering",
        relocation_need=0.5,
        years_to_first_income=4.0,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


class TestOverallConflict:

    def test_1_sanity_aligned_produces_low_conflict(self):
        """Aligned student and parent should produce near-zero conflict."""
        s = _make_student(
            risk_appetite=0.6,
            relocation_willingness=0.7,
            max_years_to_income=3.0,
        )
        p = _make_parent(
            risk=0.6,
            relocation_willingness=0.7,
            max_years_to_income=3.0,
        )
        report = compute_overall_conflict(s, p)
        assert isinstance(report, OverallConflictReport)
        assert report.overall_conflict < 0.05
        assert report.is_high_conflict is False

    def test_2_opposite_risk_appetite(self):
        """Student risk 1.0 vs parent risk 0.0 should produce gap 1.0 on risk."""
        s = _make_student(risk_appetite=1.0)
        p = _make_parent(risk=0.0)
        report = compute_overall_conflict(s, p)
        assert report.risk_conflict.gap == pytest.approx(1.0)
        assert report.overall_conflict > 0.2  # risk contributes 25% weight
        assert report.is_high_conflict is True

    def test_3_domain_preference_divergence(self):
        """Student loves domain 5, parent hates it 1 → gap should be large."""
        s = _make_student(domain_preference={"Technology & Engineering": 5.0})
        p = _make_parent(domain_ratings={"Technology & Engineering": 1.0})
        report = compute_overall_conflict(s, p)
        assert report.domain_conflict.gap == pytest.approx(1.0)
        assert report.is_high_conflict is True

    def test_4_relocation_mismatch(self):
        s = _make_student(relocation_willingness=0.9)
        p = _make_parent(relocation_willingness=0.1)
        report = compute_overall_conflict(s, p)
        assert report.relocation_conflict.gap == pytest.approx(0.8)
        assert report.is_high_conflict is True

    def test_5_time_to_income_mismatch(self):
        """Student ok with 6 years, parent wants income in 2 → strong gap."""
        s = _make_student(max_years_to_income=6.0)
        p = _make_parent(max_years_to_income=2.0)
        report = compute_overall_conflict(s, p)
        assert report.time_conflict.gap == pytest.approx(4.0 / 6.0, rel=1e-6)
        assert report.is_high_conflict is True

    def test_6_composite_score_is_weighted_sum(self):
        """Verify overall_conflict = sum(gap_i * w_i)."""
        s = _make_student(risk_appetite=0.8, relocation_willingness=0.2, max_years_to_income=6.0)
        p = _make_parent(risk=0.2, relocation_willingness=0.8, max_years_to_income=2.0)
        cfg = ConflictConfig(w_risk=0.25, w_domain=0.25, w_relocation=0.25, w_time=0.25)
        report = compute_overall_conflict(s, p, cfg)

        expected = (
            report.risk_conflict.gap * 0.25
            + report.domain_conflict.gap * 0.25
            + report.relocation_conflict.gap * 0.25
            + report.time_conflict.gap * 0.25
        )
        assert report.overall_conflict == pytest.approx(expected, abs=1e-10)


class TestPerCareerConflict:

    def test_1_student_loves_risky_parent_hates(self):
        """Student risk-tolerant, parent risk-averse → route with high risk = high conflict."""
        s = _make_student(risk_appetite=0.9)
        p = _make_parent(risk=0.1)
        route = _make_route(career_risk=0.95, domain="Technology & Engineering")
        report = compute_career_conflict(s, p, route)

        assert isinstance(report, CareerConflictReport)
        assert report.risk_gap > 0.7  # strong disagreement on route's risk
        assert report.career_conflict >= 0.20
        assert report.is_high_conflict is True

    def test_2_aligned_pair_low_career_conflict(self):
        """Both sides identical, route matches their shared preference → near-zero conflict."""
        s = _make_student(risk_appetite=0.5, relocation_willingness=0.3, max_years_to_income=4.0)
        p = _make_parent(risk=0.5, relocation_willingness=0.3, max_years_to_income=4.0)
        route = _make_route(career_risk=0.5, relocation_need=0.3, years_to_first_income=4.0)
        report = compute_career_conflict(s, p, route)

        assert report.career_conflict < 0.05
        assert report.is_high_conflict is False

    def test_3_time_fit_capped_at_one(self):
        """If t_r < T_p, student_time_fit should be 1.0 (route pays faster than acceptable)."""
        s = _make_student(max_years_to_income=4.0)
        p = _make_parent(max_years_to_income=2.0)
        route = _make_route(years_to_first_income=1.0)
        report = compute_career_conflict(s, p, route)

        assert report.student_time_fit == 1.0  # 4.0 / 1.0 capped
        assert report.parent_time_fit == 1.0   # 2.0 / 1.0 capped


class TestConfigOverrides:

    def test_1_custom_threshold_changes_flag(self):
        """With threshold=0.1, a gap of 0.15 becomes high conflict."""
        s = _make_student(risk_appetite=0.5)
        p = _make_parent(risk=0.65)
        cfg = ConflictConfig(conflict_threshold=0.10)
        report = compute_overall_conflict(s, p, cfg)
        assert report.risk_conflict.gap == pytest.approx(0.15)
        assert report.is_high_conflict is True

    def test_2_with_overrides_returns_new_instance(self):
        cfg = DEFAULT_CONFIG.with_overrides(w_risk=0.40)
        assert cfg.w_risk == 0.40
        assert DEFAULT_CONFIG.w_risk == 0.25  # original unchanged


class TestPropertyTests:

    def test_1_conflict_in_unit_range(self):
        """Conflict scores should always be in [0, 1]."""
        s = _make_student(
            risk_appetite=0.9,
            domain_preference={"Technology & Engineering": 5.0},
            relocation_willingness=0.9,
            max_years_to_income=10.0,
        )
        p = _make_parent(
            risk=0.1,
            domain_ratings={"Technology & Engineering": 1.0},
            relocation_willingness=0.1,
            max_years_to_income=1.0,
        )
        report = compute_overall_conflict(s, p)
        assert 0.0 <= report.overall_conflict <= 1.0
        assert report.risk_conflict.gap <= 1.0
        assert report.domain_conflict.gap <= 1.0
        assert report.relocation_conflict.gap <= 1.0
        assert report.time_conflict.gap <= 1.0

    def test_2_determinism(self):
        """Repeated calls with same input must produce identical output."""
        s = _make_student(risk_appetite=0.7, relocation_willingness=0.4, max_years_to_income=5.0)
        p = _make_parent(risk=0.3, relocation_willingness=0.8, max_years_to_income=2.0)
        r1 = compute_overall_conflict(s, p)
        r2 = compute_overall_conflict(s, p)
        assert r1.overall_conflict == r2.overall_conflict
        assert r1.risk_conflict.gap == r2.risk_conflict.gap

    def test_3_empty_domain_preferences(self):
        """No domains rated by either side → domain gap = 0."""
        s = _make_student(domain_preference={})
        p = _make_parent(domain_ratings={})
        report = compute_overall_conflict(s, p)
        assert report.domain_conflict.gap == 0.0

    def test_4_evaluate_conflict_returns_structured_result(self):
        """Top-level function returns ConflictEvaluation with all expected fields."""
        s = _make_student()
        p = _make_parent()
        routes = [_make_route(career_id=f"c{i}", route_id=f"r{i}") for i in range(3)]
        result = evaluate_conflict(s, p, routes)

        assert result.overall is not None
        assert len(result.career_conflicts) == 3
        assert result.num_high_conflict_careers == 0  # all aligned
        assert result.avg_career_conflict == pytest.approx(0.0, abs=0.01)