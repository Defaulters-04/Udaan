"""
swot.py
UDAAN PRISM Engine — Cognitive SWOT Diagnostic Extraction

Identifies student aptitude strengths (high importance, requirement met/exceeded)
and weaknesses (largest weighted shortfalls, top 3).
"""

from typing import Any
import numpy as np


def extract_strengths(
    a_j: dict[str, float],
    c_j: dict[str, float],
    u_j: dict[str, float],
    criteria: str = "mean",
) -> list[dict[str, Any]]:
    """
    Identifies aptitude traits where the student meets or exceeds the career requirement
    (a_j >= c_j) and the trait has high importance (u_j).

    DESIGN CHOICE DOCUMENTATION:
    We define 'high importance' as u_j >= mean(u) across all aptitude traits defined
    for the career. If criteria is 'median', the top half (u_j >= median(u)) is used.
    Traits are ranked primarily by importance u_j descending, and secondarily
    by surplus (a_j - c_j) descending.

    Formula:
      Strength condition: a_j >= c_j AND u_j >= threshold
      Rank by: u_j DESC, (a_j - c_j) DESC
    """
    if not u_j or not c_j:
        return []

    u_values = list(u_j.values())
    if criteria == "median":
        threshold = float(np.median(u_values))
    else:  # default 'mean'
        threshold = float(np.mean(u_values))

    strengths = []
    for trait, u_val in u_j.items():
        c_val = c_j.get(trait, 0.0)
        a_val = a_j.get(trait, 0.0)

        # Must meet or exceed requirement, and importance must meet threshold
        if a_val >= c_val and u_val >= threshold:
            surplus = a_val - c_val
            strengths.append(
                {
                    "trait": trait,
                    "student_level": round(a_val, 4),
                    "required_level": round(c_val, 4),
                    "importance": round(u_val, 4),
                    "surplus": round(surplus, 4),
                }
            )

    # Rank by importance descending, then surplus descending
    strengths.sort(key=lambda s: (s["importance"], s["surplus"]), reverse=True)
    return strengths


def extract_weaknesses(
    a_j: dict[str, float],
    c_j: dict[str, float],
    u_j: dict[str, float],
    max_count: int = 3,
) -> list[dict[str, Any]]:
    """
    Identifies and ranks aptitude traits with deficits (shortfall > 0),
    weighted by occupational importance.

    Formula:
      shortfall = max(0, c_j - a_j)
      weighted_shortfall = u_j * shortfall
      Rank by: weighted_shortfall DESC (top max_count)
    """
    candidates = []
    for trait, c_val in c_j.items():
        a_val = a_j.get(trait, 0.0)
        u_val = u_j.get(trait, 1.0)
        shortfall = max(0.0, c_val - a_val)

        if shortfall > 0.0:
            weighted_shortfall = u_val * shortfall
            candidates.append(
                {
                    "trait": trait,
                    "student_level": round(a_val, 4),
                    "required_level": round(c_val, 4),
                    "importance": round(u_val, 4),
                    "shortfall": round(shortfall, 4),
                    "weighted_shortfall": round(weighted_shortfall, 4),
                }
            )

    # Rank by weighted shortfall descending
    candidates.sort(
        key=lambda w: (w["weighted_shortfall"], w["shortfall"]), reverse=True
    )
    return candidates[:max_count]
