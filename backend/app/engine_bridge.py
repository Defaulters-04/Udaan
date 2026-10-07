"""Thin bridge connecting Udaan family records to the PRISM Engine.

Calls the engine's answer_mapping functions to build strongly-typed
Student and ParentProfile models without writing any formulas, scoring
rules, or persisting data. Never logs answers.
"""

from __future__ import annotations
from typing import Any, Optional, Union

from engine.answer_mapping import parent_from_answers, student_from_answers
from engine.parent.models import ParentProfile
from engine.student_fit.models import Student

from app.assessment.bank import get_interest_item_to_dimension, score_aptitude_answers
from app.schemas.families import RoleEnum
from app.store.families import FamilyRecord


def build_engine_profiles(
    family_or_student_answers: Union[FamilyRecord, dict[str, Any]],
    parent_answers: Optional[dict[str, Any]] = None,
) -> tuple[Student, ParentProfile]:
    """Pure bridge function building Student and ParentProfile from questionnaire answers.

    Accepts either:
    1. A FamilyRecord instance (extracts student.answers and parent.intake_answers).
    2. Explicit (student_answers_dict, parent_answers_dict).

    Inputs supplied to engine:
    - aptitude_correct: scored booleans from score_aptitude_answers(student_answers)
    - item_to_dimension: hidden interest-to-dimension table from get_interest_item_to_dimension()

    Pure function: no formulas, no mapping rules, calls no scoring code of its own,
    stores nothing, and never logs answers.
    """
    if isinstance(family_or_student_answers, FamilyRecord):
        student_member = family_or_student_answers.get_member_by_role(RoleEnum.STUDENT)
        parent_member = family_or_student_answers.get_member_by_role(RoleEnum.PARENT)
        s_answers = student_member.answers if student_member else {}
        p_answers = parent_member.intake_answers if parent_member else {}
        student_id = f"family_{family_or_student_answers.family_code}_student"
    else:
        s_answers = family_or_student_answers or {}
        p_answers = parent_answers or {}
        student_id = "student"

    # 1. Aptitude booleans from internal scoring helper
    aptitude_correct = score_aptitude_answers(s_answers)

    # 2. RIASEC interest item to dimension mapping from bank's hidden attributes
    item_to_dimension = get_interest_item_to_dimension()

    # 3. Call engine mapping functions directly
    student: Student = student_from_answers(
        answers=s_answers,
        aptitude_correct=aptitude_correct,
        item_to_dimension=item_to_dimension,
        student_id=student_id,
    )

    parent: ParentProfile = parent_from_answers(
        answers=p_answers,
    )

    return student, parent


# Convenient aliases
bridge_family = build_engine_profiles
build_family_profiles = build_engine_profiles
