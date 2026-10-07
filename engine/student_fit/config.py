"""
config.py
UDAAN PRISM Engine — Student Fit Configuration

Centralized configuration for stage weights, dimensions, scale bounds,
sensitivity analysis parameters, stretch criteria, and blended interest fit.
"""

from typing import Final
from engine.config import DEFAULT_CONFIG as MASTER_CONFIG, StudentFitConfig

# Link to master engine config
DEFAULT_STUDENT_CONFIG: StudentFitConfig = MASTER_CONFIG.student_fit

# Scale normalization bounds
SCALE_MIN: Final[float] = DEFAULT_STUDENT_CONFIG.scale_min
SCALE_MAX: Final[float] = DEFAULT_STUDENT_CONFIG.scale_max

# RIASEC 6-factor interest model dimensions (order-preserved for Pearson vectors)
RIASEC_DIMENSIONS: Final[list[str]] = list(DEFAULT_STUDENT_CONFIG.riasec_dimensions)

# Core aptitude dimensions evaluated in student cognitive profiling
APTITUDE_DIMENSIONS: Final[list[str]] = list(DEFAULT_STUDENT_CONFIG.aptitude_dimensions)

# Stage-specific scoring weights: w_I (Interest), w_A (Aptitude), w_S (Skill), w_P (Personality)
STAGE_WEIGHTS: dict[str, dict[str, float]] = {
    "school": dict(DEFAULT_STUDENT_CONFIG.stage_weights_school),
    "college": dict(DEFAULT_STUDENT_CONFIG.stage_weights_college),
}

# Stretch career threshold (Fix 3)
# Weighted aptitude shortfall ratio threshold
STRETCH_SHORTFALL_RATIO: Final[float] = DEFAULT_STUDENT_CONFIG.stretch_shortfall_ratio  # design assumption, unsourced

# InterestFit blend weights (Fix 6)
W_PEARSON: Final[float] = DEFAULT_STUDENT_CONFIG.w_pearson  # design assumption, unsourced
W_OVERLAP: Final[float] = DEFAULT_STUDENT_CONFIG.w_overlap  # design assumption, unsourced

# Flat RIASEC standard deviation threshold (Fix 6)
RIASEC_FLAT_STD_THRESHOLD: Final[float] = DEFAULT_STUDENT_CONFIG.riasec_flat_std_threshold  # design assumption, unsourced

# SWOT Analysis configuration
SWOT_IMPORTANCE_CRITERIA: Final[str] = DEFAULT_STUDENT_CONFIG.swot_importance_criteria
SWOT_MAX_WEAKNESSES: Final[int] = DEFAULT_STUDENT_CONFIG.swot_max_weaknesses
