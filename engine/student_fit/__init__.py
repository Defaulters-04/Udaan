"""
engine/student_fit
UDAAN PRISM Engine — Student Fit Scoring Module

Standalone, pure-math package for evaluating multidimensional student-to-career fit.
"""

from .config import STAGE_WEIGHTS
from .models import AcademicProfile, AcademicRequirement, Career, Result, Student
from .scoring import (
    calculate_aptitude_fit,
    calculate_interest_fit,
    calculate_personality_fit,
    calculate_skill_fit,
    calculate_student_fit,
    evaluate_academic_gate,
    rank_careers,
)
from .swot import extract_strengths, extract_weaknesses

__all__ = [
    "STAGE_WEIGHTS",
    "AcademicProfile",
    "AcademicRequirement",
    "Career",
    "Result",
    "Student",
    "calculate_aptitude_fit",
    "calculate_interest_fit",
    "calculate_personality_fit",
    "calculate_skill_fit",
    "calculate_student_fit",
    "evaluate_academic_gate",
    "extract_strengths",
    "extract_weaknesses",
    "rank_careers",
]
