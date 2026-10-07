"""
scoring.py
UDAAN PRISM Engine — Student Fit Deterministic Scoring Functions

Implements the four sub-fit equations (InterestFit, AptitudeFit, SkillFit, PersonalityFit),
stretch flag evaluation, academic gating (G_acad), missing data weight rescaling,
composite student fit (F_student), and multi-career ranking.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any
import numpy as np

from engine.config import DEFAULT_CONFIG as MASTER_CONFIG
from .config import (
    RIASEC_DIMENSIONS,
    STAGE_WEIGHTS,
    STRETCH_SHORTFALL_RATIO,
    W_PEARSON,
    W_OVERLAP,
    RIASEC_FLAT_STD_THRESHOLD,
)
from .models import AcademicProfile, AcademicRequirement, Career, Result, Student
from .swot import extract_strengths, extract_weaknesses


@dataclass
class RankingResult:
    """Container for career ranking output supporting tuple unpacking."""

    eligible: list[Result]
    blocked: list[Result]

    def __iter__(self):
        return iter((self.eligible, self.blocked))

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": [r.to_dict() for r in self.eligible],
            "blocked": [r.to_dict() for r in self.blocked],
        }


def calculate_interest_fit(
    I_s: dict[str, float] | list[float],
    I_c: dict[str, float] | list[float],
    return_low_signal: bool = False,
) -> float | tuple[float, bool]:
    """
    Computes blended InterestFit (Fix 6).

    Formula:
      interest_term = 50 * (1 + Pearson(I_s, I_c))
      overlap_term = 100 * |top3(student) intersect top3(career)| / 3
      InterestFit = w_pearson * interest_term + w_overlap * overlap_term
      If student RIASEC vector standard deviation < riasec_flat_std_threshold:
        return 50.0 and low_signal = True
    """
    if isinstance(I_s, dict):
        x = np.array([I_s[dim] for dim in RIASEC_DIMENSIONS], dtype=float)
        s_dict = I_s
    else:
        x = np.array(I_s, dtype=float)
        s_dict = {dim: float(x[i]) for i, dim in enumerate(RIASEC_DIMENSIONS)}

    if isinstance(I_c, dict):
        y = np.array([I_c[dim] for dim in RIASEC_DIMENSIONS], dtype=float)
        c_dict = I_c
    else:
        y = np.array(I_c, dtype=float)
        c_dict = {dim: float(y[i]) for i, dim in enumerate(RIASEC_DIMENSIONS)}

    var_x = float(np.var(x))
    std_x = math.sqrt(max(0.0, var_x))

    # Fix 6: Check for flat student RIASEC vector
    if std_x < RIASEC_FLAT_STD_THRESHOLD or math.isclose(std_x, 0.0, abs_tol=1e-12):
        if return_low_signal:
            return 50.0, True
        return 50.0

    var_y = float(np.var(y))
    std_y = math.sqrt(max(0.0, var_y))

    if std_y < RIASEC_FLAT_STD_THRESHOLD or math.isclose(std_y, 0.0, abs_tol=1e-12):
        if return_low_signal:
            return 50.0, False
        return 50.0
    else:
        mean_x = float(np.mean(x))
        mean_y = float(np.mean(y))
        cov_xy = float(np.mean((x - mean_x) * (y - mean_y)))
        r = cov_xy / (std_x * std_y)
        r = max(-1.0, min(1.0, r))
        interest_term = 50.0 * (1.0 + r)

    # Top 3 RIASEC overlap
    top3_s = sorted(RIASEC_DIMENSIONS, key=lambda d: s_dict[d], reverse=True)[:3]
    top3_c = sorted(RIASEC_DIMENSIONS, key=lambda d: c_dict[d], reverse=True)[:3]
    overlap_count = len(set(top3_s).intersection(set(top3_c)))
    overlap_term = 100.0 * (overlap_count / 3.0)

    interest_fit = round((W_PEARSON * interest_term) + (W_OVERLAP * overlap_term), 4)
    interest_fit = max(0.0, min(100.0, interest_fit))

    if return_low_signal:
        return interest_fit, False
    return interest_fit


def calculate_aptitude_fit(
    a_j: dict[str, float],
    c_j: dict[str, float],
    u_j: dict[str, float],
) -> float:
    """
    Computes AptitudeFit penalizing only deficits against required cognitive levels.

    Formula:
      AptitudeFit = 100 * [ 1 - sum_j u_j * max(0, c_j - a_j) / sum_j u_j * c_j ]
      Only shortfalls are penalized.
      If denominator == 0: AptitudeFit = 100.
    """
    denominator = 0.0
    total_shortfall = 0.0

    for trait, c_val in c_j.items():
        u_val = u_j.get(trait, 1.0)
        a_val = a_j.get(trait, 0.0)

        shortfall = max(0.0, c_val - a_val)
        denominator += u_val * c_val
        total_shortfall += u_val * shortfall

    if math.isclose(denominator, 0.0, abs_tol=1e-12):
        return 100.0

    penalty = total_shortfall / denominator
    score = 100.0 * (1.0 - penalty)
    return round(max(0.0, min(100.0, score)), 4)


def calculate_stretch(
    a_j: dict[str, float],
    c_j: dict[str, float],
    u_j: dict[str, float],
) -> tuple[bool, list[str], float]:
    """
    Computes weighted aptitude shortfall ratio = sum(u_j*max(0, c_j - a_j)) / sum(u_j*c_j) (Fix 3).
    If it exceeds stretch_shortfall_ratio, returns stretch=True with specific shortfall reasons.
    """
    denominator = 0.0
    total_shortfall = 0.0
    reasons: list[str] = []

    for trait, c_val in c_j.items():
        u_val = u_j.get(trait, 1.0)
        a_val = a_j.get(trait, 0.0)
        shortfall = max(0.0, c_val - a_val)
        denominator += u_val * c_val
        total_shortfall += u_val * shortfall
        if shortfall > 0.0:
            reasons.append(
                f"{trait}: shortfall of {shortfall:.2f} (required {c_val:.2f}, student {a_val:.2f})"
            )

    ratio = total_shortfall / denominator if denominator > 0.0 else 0.0
    is_stretch = ratio > STRETCH_SHORTFALL_RATIO
    return is_stretch, reasons if is_stretch else [], round(ratio, 4)


def calculate_skill_fit(
    P_k: dict[str, float],
    R_k: dict[str, float],
    s_k: dict[str, float],
) -> float:
    """
    Computes SkillFit as weighted proficiency attainment against career requirements.

    Formula:
      SkillFit = 100 * sum_k s_k * min(1, P_k / R_k) / sum_k s_k
      Missing student skill counts as 0.
      If R_k = 0, treat that term as 1.
      If no skills are required: SkillFit = 100.
    """
    if not R_k:
        return 100.0

    denominator = 0.0
    numerator = 0.0

    for skill, r_val in R_k.items():
        weight = s_k.get(skill, 1.0)
        denominator += weight

        if math.isclose(r_val, 0.0, abs_tol=1e-12):
            term = 1.0
        else:
            p_val = P_k.get(skill, 0.0)
            term = min(1.0, p_val / r_val)

        numerator += weight * term

    if math.isclose(denominator, 0.0, abs_tol=1e-12):
        return 100.0

    score = 100.0 * (numerator / denominator)
    return round(max(0.0, min(100.0, score)), 4)


def calculate_personality_fit(
    P_j: dict[str, float],
    Pc_j: dict[str, float],
    v_j: dict[str, float],
) -> float:
    """
    Computes PersonalityFit using weighted Euclidean distance across Big Five traits.

    Formula:
      dist = sqrt( sum_j v_j * (P_j - Pc_j)^2 / sum_j v_j )
      PersonalityFit = 100 * [ 1 - dist ]
      If no personality targets: PersonalityFit = 100.
    """
    if not Pc_j:
        return 100.0

    denominator = 0.0
    weighted_sq_diff = 0.0

    for trait, pc_val in Pc_j.items():
        weight = v_j.get(trait, 1.0)
        p_val = P_j.get(trait, 0.5)
        denominator += weight
        weighted_sq_diff += weight * ((p_val - pc_val) ** 2)

    if math.isclose(denominator, 0.0, abs_tol=1e-12):
        return 100.0

    dist = math.sqrt(weighted_sq_diff / denominator)
    score = 100.0 * (1.0 - dist)
    return round(max(0.0, min(100.0, score)), 4)


def evaluate_academic_gate(
    academics: AcademicProfile,
    requirements: AcademicRequirement,
) -> tuple[int, list[str]]:
    """
    Evaluates mandatory academic threshold requirements (G_acad).
    """
    reasons: list[str] = []

    s_marks = academics.marks
    req_marks = requirements.min_marks

    norm_s_marks = s_marks * 100.0 if s_marks <= 1.0 and req_marks > 1.0 else s_marks
    norm_req_marks = req_marks * 100.0 if req_marks <= 1.0 and s_marks > 1.0 else req_marks

    if norm_s_marks < norm_req_marks:
        reasons.append(
            f"Academic marks ({norm_s_marks:.1f}%) did not meet mandatory minimum requirement ({norm_req_marks:.1f}%)."
        )

    missing_subjects = [
        sub for sub in requirements.required_subjects
        if sub not in academics.subjects
    ]
    if missing_subjects:
        reasons.append(
            f"Missing mandatory required subject(s): {', '.join(sorted(missing_subjects))}."
        )

    missing_exams = [
        exam for exam in requirements.required_exams
        if exam not in academics.exams
    ]
    if missing_exams:
        reasons.append(
            f"Missing mandatory qualifying exam(s): {', '.join(sorted(missing_exams))}."
        )

    g_acad = 1 if not reasons else 0
    return g_acad, reasons


def calculate_student_fit(
    student: Student,
    career: Career,
    weights_override: dict[str, float] | None = None,
) -> Result:
    """
    Computes overall composite student fit F_student for a single student x career pair.

    Handles:
    - Fix 3: Stretch calculation and reasons
    - Fix 4: Missing data weight dropping & rescaling to total 1, data_confidence
    - Fix 6: Blended InterestFit and low_signal detection
    """
    # 1. Stage weights selection
    if weights_override is not None:
        weights = dict(weights_override)
    else:
        stage = student.stage
        if stage not in STAGE_WEIGHTS:
            raise ValueError(f"Unknown student stage: {stage}")
        weights = dict(STAGE_WEIGHTS[stage])

    # 2. Sub-score calculations
    # Fix 6: check low_signal
    interest_fit, low_signal = calculate_interest_fit(
        student.I_s, career.I_c, return_low_signal=True
    )
    aptitude_fit = calculate_aptitude_fit(student.a_j, career.c_j, career.u_j)

    # Fix 3: Stretch calculation
    is_stretch, stretch_reasons, stretch_ratio = calculate_stretch(
        student.a_j, career.c_j, career.u_j
    )

    # Skill fit: skipped if w_S is 0.0 (e.g. school stage)
    w_S_nom = weights.get("w_S", 0.0)
    if math.isclose(w_S_nom, 0.0, abs_tol=1e-12):
        skill_fit = 0.0
    else:
        skill_fit = calculate_skill_fit(student.P_k, career.R_k, career.s_k)

    personality_fit = calculate_personality_fit(
        student.P_j, career.Pc_j, career.v_j
    )

    # 3. Fix 4: Missing data handling in weighted sum
    # Any sub-score whose value is None or "NOT FOUND" is dropped, remaining weights rescaled
    sub_scores_map: dict[str, float | None] = {
        "w_I": interest_fit,
        "w_A": aptitude_fit,
        "w_S": skill_fit if not math.isclose(w_S_nom, 0.0, abs_tol=1e-12) else 0.0,
        "w_P": personality_fit,
    }

    # Identify present vs dropped components
    active_weights: dict[str, float] = {}
    dropped_weight = 0.0
    total_nominal_weight = sum(weights.get(k, 0.0) for k in ("w_I", "w_A", "w_S", "w_P"))

    for k in ("w_I", "w_A", "w_S", "w_P"):
        val = sub_scores_map.get(k)
        nom_w = weights.get(k, 0.0)
        if val is None or val == "NOT FOUND":
            dropped_weight += nom_w
        else:
            active_weights[k] = nom_w

    kept_weight = sum(active_weights.values())
    weights_used: dict[str, float] = {}
    if kept_weight > 0.0:
        for k, w_val in active_weights.items():
            weights_used[k] = round(w_val / kept_weight, 4)
    else:
        weights_used = {k: 0.0 for k in weights}

    # Fraction of weight dropped for data confidence
    fraction_dropped = (dropped_weight / total_nominal_weight) if total_nominal_weight > 0.0 else 0.0
    if fraction_dropped <= MASTER_CONFIG.missing_data.data_confidence_high_max_dropped:
        data_confidence = "high"
    elif fraction_dropped <= MASTER_CONFIG.missing_data.data_confidence_med_max_dropped:
        data_confidence = "medium"
    else:
        data_confidence = "low"

    # 4. Academic Gate
    g_acad, blocked_reasons = evaluate_academic_gate(
        student.academics, career.academic_requirements
    )
    blocked = (g_acad == 0)

    # 5. Composite Student Fit with rescaled weights
    raw_composite = sum(
        weights_used.get(k, 0.0) * float(sub_scores_map[k])
        for k in weights_used
        if sub_scores_map[k] is not None and sub_scores_map[k] != "NOT FOUND"
    )
    f_student = float(g_acad) * raw_composite
    f_student = round(max(0.0, min(100.0, f_student)), 4)

    # 6. SWOT Analysis
    strengths = extract_strengths(student.a_j, career.c_j, career.u_j)
    weaknesses = extract_weaknesses(student.a_j, career.c_j, career.u_j)

    return Result(
        career_id=career.career_id,
        career_name=career.career_name,
        F_student=f_student,
        InterestFit=interest_fit,
        AptitudeFit=aptitude_fit,
        SkillFit=skill_fit,
        PersonalityFit=personality_fit,
        G_acad=g_acad,
        stage=student.stage,
        weights_used=weights_used,
        strengths=strengths,
        weaknesses=weaknesses,
        blocked=blocked,
        blocked_reasons=blocked_reasons,
        stretch=is_stretch,
        stretch_reasons=stretch_reasons,
        stretch_shortfall_ratio=stretch_ratio,
        low_signal=low_signal,
        data_confidence=data_confidence,
    )


def rank_careers(
    student: Student,
    careers: list[Career],
    weights_override: dict[str, float] | None = None,
) -> RankingResult:
    """
    Evaluates and ranks a portfolio of careers for a student.

    Returns:
      RankingResult(eligible, blocked)
      - eligible: sorted by F_student DESC (tie-broken by career_id ASC)
      - blocked: careers where G_acad == 0 (with reasons, F_student = 0)
    """
    eligible: list[Result] = []
    blocked: list[Result] = []

    for career in careers:
        result = calculate_student_fit(student, career, weights_override)
        if result.blocked:
            blocked.append(result)
        else:
            eligible.append(result)

    eligible.sort(key=lambda r: (-r.F_student, r.career_id))
    blocked.sort(key=lambda r: r.career_id)

    return RankingResult(eligible=eligible, blocked=blocked)
