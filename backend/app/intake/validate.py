from typing import Any, Optional

from app.intake.bank import ALL_INTAKE_QUESTIONS_MAP, InternalQuestion


def validate_single_intake_answer(
    question: InternalQuestion, value: Any
) -> tuple[bool, Any, Optional[str]]:
    """
    Validates a single intake answer against its question specification.
    Returns: (is_valid, sanitized_value_or_none, error_message)
    Never echoes user-submitted values in error messages for privacy.
    """
    q_type = question.type

    # 1. Unanswered / Clear detection (Assumption b)
    if value is None:
        return True, None, None
    if isinstance(value, str) and not value.strip():
        return True, None, None
    if isinstance(value, list) and len(value) == 0:
        return True, None, None

    # 2. Type-specific manual validation (Assumption c)
    if q_type == "single_choice":
        if not isinstance(value, str):
            return False, None, f"Answer for '{question.id}' must be a string option id."
        valid_option_ids = {opt.id for opt in question.options}
        if value not in valid_option_ids:
            return False, None, f"Option chosen is not valid for question '{question.id}'."
        return True, value, None

    elif q_type == "multi_choice":
        if not isinstance(value, list):
            return False, None, f"Answer for '{question.id}' must be an array of option ids."
        valid_option_ids = {opt.id for opt in question.options}
        seen = set()
        sanitized = []
        for item in value:
            if not isinstance(item, str):
                return False, None, f"Items in '{question.id}' array must be string option ids."
            if item not in valid_option_ids:
                return False, None, f"Option chosen is not valid for question '{question.id}'."
            if item not in seen:
                seen.add(item)
                sanitized.append(item)

        # max_select validation
        if question.max_select is not None and len(sanitized) > question.max_select:
            return (
                False,
                None,
                f"Question '{question.id}' allows at most {question.max_select} selections.",
            )

        return True, sanitized, None

    elif q_type == "text":
        if not isinstance(value, str):
            return False, None, f"Answer for '{question.id}' must be a string."
        if "\n" in value or "\r" in value:
            return False, None, f"Single-line text answer for '{question.id}' must not contain line breaks."
        trimmed = value.strip()
        if question.max_length is not None and len(trimmed) > question.max_length:
            return False, None, f"Text answer for '{question.id}' exceeds maximum length of {question.max_length}."
        return True, trimmed, None

    elif q_type == "long_text":
        if not isinstance(value, str):
            return False, None, f"Answer for '{question.id}' must be a string."
        trimmed = value.strip()
        if question.max_length is not None and len(trimmed) > question.max_length:
            return False, None, f"Long text answer for '{question.id}' exceeds maximum length of {question.max_length}."
        return True, trimmed, None

    return False, None, f"Unknown question type '{q_type}'."


def validate_intake_answers_payload(
    answers: dict[str, Any]
) -> tuple[bool, dict[str, Any], Optional[str]]:
    """
    Validates an entire intake answers dict in an all-or-nothing manner.
    Returns: (is_valid, updates_dict, error_message)
    """
    updates: dict[str, Any] = {}

    for q_id, val in answers.items():
        question = ALL_INTAKE_QUESTIONS_MAP.get(q_id)
        if question is None:
            return False, {}, f"Unknown question id: '{q_id}'"

        is_valid, sanitized_val, err = validate_single_intake_answer(question, val)
        if not is_valid:
            return False, {}, err

        updates[q_id] = sanitized_val

    return True, updates, None
