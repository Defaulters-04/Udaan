"""
models.py
UDAAN PRISM Engine — Student Fit Domain Models

Strictly-typed dataclasses for Student, Career, Academic Requirements,
and JSON-serializable Fit Results.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .config import APTITUDE_DIMENSIONS, RIASEC_DIMENSIONS, SCALE_MAX, SCALE_MIN


def _clamp(val: float, key_name: str) -> float:
    """Validates that val is a real number and clamps it to [0.0, 1.0]."""
    try:
        f_val = float(val)
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Expected numeric level for '{key_name}', got {val!r}"
        ) from err
    return max(SCALE_MIN, min(SCALE_MAX, f_val))


def _validate_and_clamp_dict(
    d: dict[str, float],
    field_name: str,
    required_keys: list[str] | None = None,
    allow_empty: bool = True,
) -> dict[str, float]:
    """
    Validates dictionary values, ensuring required keys exist and values are clamped to [0, 1].
    """
    if d is None:
        if allow_empty:
            return {}
        raise ValueError(f"Field '{field_name}' cannot be None.")

    if required_keys:
        missing = [k for k in required_keys if k not in d]
        if missing:
            raise ValueError(
                f"Missing required key(s) in '{field_name}': {missing}. "
                f"Required keys: {required_keys}"
            )

    clamped: dict[str, float] = {}
    for k, v in d.items():
        if not isinstance(k, str) or not k.strip():
            raise ValueError(f"Invalid non-string key in '{field_name}': {k!r}")
        clamped[k.strip()] = _clamp(v, f"{field_name}[{k}]")

    return clamped


def _validate_riasec(
    riasec: dict[str, float] | list[float] | tuple[float, ...], field_name: str
) -> dict[str, float]:
    """
    Validates and standardizes RIASEC 6-factor inputs into a dict with keys R, I, A, S, E, C.
    """
    if isinstance(riasec, (list, tuple)):
        if len(riasec) != 6:
            raise ValueError(
                f"RIASEC vector in '{field_name}' must have exactly 6 scores (R, I, A, S, E, C). Got length {len(riasec)}."
            )
        return {
            dim: _clamp(val, f"{field_name}[{dim}]")
            for dim, val in zip(RIASEC_DIMENSIONS, riasec)
        }
    if isinstance(riasec, dict):
        return _validate_and_clamp_dict(
            riasec, field_name, required_keys=RIASEC_DIMENSIONS
        )

    raise ValueError(
        f"'{field_name}' must be a dict with keys {RIASEC_DIMENSIONS} or a 6-element list/tuple."
    )


@dataclass(frozen=True)
class AcademicProfile:
    """Academic achievements, subject completions, and qualifying exams passed."""

    marks: float = 0.0  # Percentage marks (0-100 or normalized 0-1)
    subjects: set[str] = field(default_factory=set)
    exams: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        # Standardize subjects and exams to title-case trimmed strings
        clean_subs = {
            s.strip().lower() for s in self.subjects if isinstance(s, str) and s.strip()
        }
        clean_exams = {
            e.strip().lower() for e in self.exams if isinstance(e, str) and e.strip()
        }
        object.__setattr__(self, "subjects", clean_subs)
        object.__setattr__(self, "exams", clean_exams)
        try:
            m = float(self.marks)
            object.__setattr__(self, "marks", max(0.0, m))
        except (TypeError, ValueError) as err:
            raise ValueError(f"Invalid marks value: {self.marks!r}") from err


@dataclass(frozen=True)
class AcademicRequirement:
    """Mandatory academic gate requirements for a career."""

    min_marks: float = 0.0  # Minimum percentage marks required
    required_subjects: list[str] = field(default_factory=list)
    required_exams: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        clean_subs = [
            s.strip().lower()
            for s in self.required_subjects
            if isinstance(s, str) and s.strip()
        ]
        clean_exams = [
            e.strip().lower()
            for e in self.required_exams
            if isinstance(e, str) and e.strip()
        ]
        object.__setattr__(self, "required_subjects", clean_subs)
        object.__setattr__(self, "required_exams", clean_exams)
        try:
            m = float(self.min_marks)
            object.__setattr__(self, "min_marks", max(0.0, m))
        except (TypeError, ValueError) as err:
            raise ValueError(f"Invalid min_marks value: {self.min_marks!r}") from err


@dataclass
class Student:
    """
    Student profile containing multidimensional psychometric, cognitive,
    skill, and academic attributes.

    Shared dimensions with Parent profile (for Conflict Index):
    - risk_appetite: Student's risk tolerance (0-1)
    - domain_preference: Dict of domain ratings (1-5 scale, like parent's domain_ratings)
    - relocation_willingness: Willingness to relocate (0-1)
    - max_years_to_income: Maximum acceptable years until first income (years)
    """

    student_id: str
    stage: str  # 'school' or 'college'
    I_s: dict[str, float]  # RIASEC 6-factor interest scores
    a_j: dict[str, float]  # Aptitude levels: logical, numerical, verbal, spatial
    P_k: dict[str, float] = field(default_factory=dict)  # Skill proficiencies
    P_j: dict[str, float] = field(default_factory=dict)  # Personality traits
    academics: AcademicProfile = field(default_factory=AcademicProfile)

    # Shared dimensions for Parent-Student Conflict Index
    risk_appetite: float = 0.5  # 0 = risk-averse, 1 = risk-seeking
    domain_preference: dict[str, float] = field(default_factory=dict)  # domain -> rating (1-5)
    relocation_willingness: float = 0.5  # 0 = unwilling, 1 = willing
    max_years_to_income: float = 4.0  # years

    def __post_init__(self) -> None:
        if self.stage not in {"school", "college"}:
            raise ValueError(
                f"Invalid stage '{self.stage}'. Must be 'school' or 'college'."
            )

        self.I_s = _validate_riasec(self.I_s, "Student.I_s")
        self.a_j = _validate_and_clamp_dict(
            self.a_j, "Student.a_j", required_keys=APTITUDE_DIMENSIONS
        )
        self.P_k = _validate_and_clamp_dict(self.P_k, "Student.P_k", allow_empty=True)
        self.P_j = _validate_and_clamp_dict(self.P_j, "Student.P_j", allow_empty=True)

        # Validate shared dimensions
        if not (0.0 <= self.risk_appetite <= 1.0):
            raise ValueError(f"risk_appetite must be in [0, 1], got {self.risk_appetite}")
        if not (0.0 <= self.relocation_willingness <= 1.0):
            raise ValueError(f"relocation_willingness must be in [0, 1], got {self.relocation_willingness}")
        if self.max_years_to_income < 0:
            raise ValueError(f"max_years_to_income must be >= 0, got {self.max_years_to_income}")

        # Validate domain_preference ratings (1-5 scale)
        for domain, rating in self.domain_preference.items():
            r = float(rating)
            if not (1.0 <= r <= 5.0):
                raise ValueError(f"Rating for domain '{domain}' must be between 1 and 5, got {rating}")

        if not isinstance(self.academics, AcademicProfile):
            if isinstance(self.academics, dict):
                self.academics = AcademicProfile(**self.academics)
            else:
                raise ValueError("Student.academics must be an AcademicProfile instance.")


@dataclass
class Career:
    """
    Career benchmark profile defining target multidimensional requirements
    and importance weights.
    """

    career_id: str
    career_name: str
    I_c: dict[str, float]  # RIASEC benchmark scores
    c_j: dict[str, float]  # Required aptitude levels
    u_j: dict[str, float]  # Aptitude importance weights
    R_k: dict[str, float] = field(default_factory=dict)  # Required skill levels
    s_k: dict[str, float] = field(default_factory=dict)  # Skill importance weights
    Pc_j: dict[str, float] = field(default_factory=dict)  # Target personality traits
    v_j: dict[str, float] = field(default_factory=dict)  # Personality importance weights
    academic_requirements: AcademicRequirement = field(
        default_factory=AcademicRequirement
    )

    def __post_init__(self) -> None:
        self.I_c = _validate_riasec(self.I_c, "Career.I_c")
        self.c_j = _validate_and_clamp_dict(
            self.c_j, "Career.c_j", required_keys=APTITUDE_DIMENSIONS
        )
        self.u_j = _validate_and_clamp_dict(
            self.u_j, "Career.u_j", required_keys=APTITUDE_DIMENSIONS
        )

        self.R_k = _validate_and_clamp_dict(self.R_k, "Career.R_k", allow_empty=True)
        self.s_k = _validate_and_clamp_dict(self.s_k, "Career.s_k", allow_empty=True)
        self.Pc_j = _validate_and_clamp_dict(self.Pc_j, "Career.Pc_j", allow_empty=True)
        self.v_j = _validate_and_clamp_dict(self.v_j, "Career.v_j", allow_empty=True)

        # Ensure skill weights cover required skills
        for k in self.R_k:
            if k not in self.s_k:
                self.s_k[k] = 1.0  # Default unit importance if unspecified

        # Ensure personality weights cover personality traits
        for k in self.Pc_j:
            if k not in self.v_j:
                self.v_j[k] = 1.0  # Default unit importance if unspecified

        if not isinstance(self.academic_requirements, AcademicRequirement):
            if isinstance(self.academic_requirements, dict):
                self.academic_requirements = AcademicRequirement(
                    **self.academic_requirements
                )
            else:
                raise ValueError(
                    "Career.academic_requirements must be an AcademicRequirement instance."
                )


@dataclass
class Result:
    """
    Deterministic Student-to-Career Fit evaluation output.
    JSON-serializable with diagnostic SWOT sub-components.
    """

    career_id: str
    career_name: str
    F_student: float
    InterestFit: float
    AptitudeFit: float
    SkillFit: float
    PersonalityFit: float
    G_acad: int
    stage: str
    weights_used: dict[str, float]
    strengths: list[dict[str, Any]]
    weaknesses: list[dict[str, Any]]
    blocked: bool
    blocked_reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Returns a clean JSON-serializable dictionary."""
        return asdict(self)
