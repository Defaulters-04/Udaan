"""
config.py
UDAAN PRISM Engine — Student Fit Configuration

Centralized configuration for stage weights, dimensions, scale bounds,
and sensitivity analysis parameters.
"""

from typing import Final

# Scale normalization bounds
SCALE_MIN: Final[float] = 0.0
SCALE_MAX: Final[float] = 1.0

# RIASEC 6-factor interest model dimensions (order-preserved for Pearson vectors)
RIASEC_DIMENSIONS: Final[list[str]] = ["R", "I", "A", "S", "E", "C"]

# Core aptitude dimensions evaluated in student cognitive profiling
APTITUDE_DIMENSIONS: Final[list[str]] = ["logical", "numerical", "verbal", "spatial"]

# Stage-specific scoring weights: w_I (Interest), w_A (Aptitude), w_S (Skill), w_P (Personality)
# school:  0.55, 0.35, 0.00, 0.10 (skips SkillFit entirely for early learners)
# college: 0.40, 0.30, 0.20, 0.10 (incorporates acquired domain skills)
STAGE_WEIGHTS: dict[str, dict[str, float]] = {
    "school": {
        "w_I": 0.55,
        "w_A": 0.35,
        "w_S": 0.00,
        "w_P": 0.10,
    },
    "college": {
        "w_I": 0.40,
        "w_A": 0.30,
        "w_S": 0.20,
        "w_P": 0.10,
    },
}

# SWOT Analysis configuration
# For strengths: "high u_j" criterion choice
# Option "mean": importance u_j >= mean(u) across that career's aptitude importances
# Option "median": top half of that career's aptitude importances
SWOT_IMPORTANCE_CRITERIA: Final[str] = "mean"

# Maximum count of top weaknesses to return
SWOT_MAX_WEAKNESSES: Final[int] = 3
