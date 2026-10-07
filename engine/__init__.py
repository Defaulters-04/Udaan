"""PRISM Engine root package.

Multi-dimensional AI career guidance engine for Indian students and their families.
Combines Student Fit, Parent Financial Constraint Solver, Market Machine,
and Conflict Index into an actionable, financially viable career roadmap.
"""

from .synthesis import (
    generate_unified_roadmap,
    FullRoadmapReport,
    RoadmapItem,
    BlockedRoadmapItem,
)

__all__ = [
    "generate_unified_roadmap",
    "FullRoadmapReport",
    "RoadmapItem",
    "BlockedRoadmapItem",
]
