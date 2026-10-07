"""
scoring.py
UDAAN PRISM Engine — Student Fit Deterministic Scoring Functions

Implements the four sub-fit equations (InterestFit, AptitudeFit, SkillFit, PersonalityFit),
the academic gating rule (G_acad), the composite student fit (F_student),
and multi-career ranking.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any
import numpy as np

from .config import RIASEC_DIMENSIONS, STAGE_WEIGHTS
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
) -> float:
    """
    Computes InterestFit using Pearson correlation r over 6 RIASEC dimensions.

    Formula:
      r = Pearson(I_s, I_c) over (R, I, A, S, E, C)
      InterestFit = 50 * (1 + r)
      If either profile has zero variance: InterestFit = 50 (neutral).
    """
    if isinstance(I_s, dict):
        x = np.array([I_s[dim] for dim in RIASEC_DIMENSIONS], dtype=float)
    else:
        x = np.array(I_s, dtype=float)

    if isinstance(I_c, dict):
        y = np.array([I_c[dim] for dim in RIASEC_DIMENSIONS], dtype=float)
    else:
        y = np.array(I_c, dtype=float)

    var_x = float(np.var(x))
    var_y = float(np.var(y))

    # If either profile has zero variance, correlation is undefined -> neutral 50.0
    if var_x == 0.0 or var_y == 0.0 or math.isclose(var_x, 0.0, abs_tol=1e-12) or math.isclose(var_y, 0.0, abs_tol=1e-12):
        return 50.0

    mean_x = float(np.mean(x))
    mean_y = float(np.mean(y))
    cov_xy = float(np.mean((x - mean_x) * (y - mean_y)))

    std_x = math.sqrt(var_x)
    std_y = math.sqrt(var_y)
    r = cov_xy / (std_x * std_y)

    # Guard against minor floating-point boundary issues
    r = max(-1.0, min(1.0, r))

    interest_fit = 50.0 * (1.0 + r)
    return round(max(0.0, min(100.0, interest_fit)), 4)


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
    Computes PersonalityFit using weighted root-mean-square distance (style match).

    Formula:
      PersonalityFit = 100 * [ 1 - sqrt( sum_j v_j * (P_j - Pc_j)^2 / sum_j v_j ) ]
      Symmetric (style match). Clamp result to [0, 100].
    """
    if not Pc_j:
        return 100.0

    denominator = 0.0
    weighted_sq_diff = 0.0

    for trait, pc_val in Pc_j.items():
        weight = v_j.get(trait, 1.0)
        p_val = P_j.get(trait, 0.0)

        denominator += weight
        weighted_sq_diff += weight * ((p_val - pc_val) ** 2)

    if math.isclose(denominator, 0.0, abs_tol=1e-12):
        return 100.0

    rms_dist = math.sqrt(weighted_sq_diff / denominator)
    score = 100.0 * (1.0 - rms_dist)
    return round(max(0.0, min(100.0, score)), 4)


def evaluate_academic_gate(
    academics: AcademicProfile,
    requirements: AcademicRequirement,
) -> tuple[int, list[str]]:
    """
    Evaluates mandatory academic requirements.

    Formula:
      G_acad = 1 if ALL mandatory requirements are met, else 0.
      Record every failed requirement as a human-readable reason.
    """
    reasons: list[str] = []

    # 1. Marks comparison (handles both 0-1 ratio and 0-100 percentage scales)
    s_marks = academics.marks
    req_marks = requirements.min_marks

    # Normalize scales if one is percentage (>1.0) and other is ratio (<=1.0)
    norm_s_marks = s_marks * 100.0 if s_marks <= 1.0 and req_marks > 1.0 else s_marks
    norm_req_marks = req_marks * 100.0 if req_marks <= 1.0 and s_marks > 1.0 else req_marks

    if norm_s_marks < norm_req_marks:
        reasons.append(
            f"Academic marks ({norm_s_marks:.1f}%) did not meet mandatory minimum requirement ({norm_req_marks:.1f}%)."
        )

    # 2. Required subjects
    missing_subjects = [
        sub for sub in requirements.required_subjects
        if sub not in academics.subjects
    ]
    if missing_subjects:
        reasons.append(
            f"Missing mandatory required subject(s): {', '.join(sorted(missing_subjects))}."
        )

    # 3. Required qualifying exams
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

    Formula:
      F_student = G_acad * (w_I*InterestFit + w_A*AptitudeFit + w_S*SkillFit + w_P*PersonalityFit)
      Range: [0, 100]
    """
    # 1. Stage weights selection
    if weights_override is not None:
        weights = weights_override
    else:
        stage = student.stage
        if stage not in STAGE_WEIGHTS:
            raise ValueError(f"Unknown student stage: {stage}")
        weights = STAGE_WEIGHTS[stage]

    w_I = weights.get("w_I", 0.0)
    w_A = weights.get("w_A", 0.0)
    w_S = weights.get("w_S", 0.0)
    w_P = weights.get("w_P", 0.0)

    # 2. Sub-score calculations
    interest_fit = calculate_interest_fit(student.I_s, career.I_c)
    aptitude_fit = calculate_aptitude_fit(student.a_j, career.c_j, career.u_j)

    # Skill fit: skipped if w_S is 0.0 (e.g. school stage) to avoid redundant computation
    if math.isclose(w_S, 0.0, abs_tol=1e-12):
        skill_fit = 0.0
    else:
        skill_fit = calculate_skill_fit(student.P_k, career.R_k, career.s_k)

    personality_fit = calculate_personality_fit(
        student.P_j, career.Pc_j, career.v_j
    )

    # 3. Academic Gate
    g_acad, blocked_reasons = evaluate_academic_gate(
        student.academics, career.academic_requirements
    )
    blocked = (g_acad == 0)

    # 4. Composite Fit
    raw_composite = (
        (w_I * interest_fit)
        + (w_A * aptitude_fit)
        + (w_S * skill_fit)
        + (w_P * personality_fit)
    )
    f_student = float(g_acad) * raw_composite
    f_student = round(max(0.0, min(100.0, f_student)), 4)

    # 5. SWOT Analysis
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
        weights_used={k: float(v) for k, v in weights.items()},
        strengths=strengths,
        weaknesses=weaknesses,
        blocked=blocked,
        blocked_reasons=blocked_reasons,
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

    # Sort eligible careers by F_student descending, then career_id ascending
    eligible.sort(key=lambda r: (-r.F_student, r.career_id))

    # Sort blocked careers alphabetically by career_id for deterministic output
    blocked.sort(key=lambda r: r.career_id)

    return RankingResult(eligible=eligible, blocked=blocked)
