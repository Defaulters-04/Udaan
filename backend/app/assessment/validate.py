from typing import Any, Optional

from app.assessment.bank import ALL_QUESTIONS_MAP, InternalQuestion


def validate_single_answer(
    question: InternalQuestion, value: Any
) -> tuple[bool, Any, Optional[str]]:
    """
    Validates a single answer against its question specification.
    Returns: (is_valid, sanitized_value_or_none, error_message)
    If the value indicates 'unanswered' (None, empty string, whitespace, empty list),
    sanitized_value_or_none is None, indicating removal from stored answers.
    """
    q_type = question.type

    # 1. Unanswered / Clear detection (Assumption b)
    if value is None:
        return True, None, None
    if isinstance(value, str) and not value.strip():
        return True, None, None
    if isinstance(value, list) and len(value) == 0:
        return True, None, None

    # 2. Type-specific manual validation (Assumption c: no loose coercion)
    if q_type == "single_choice":
        if not isinstance(value, str):
            return False, None, f"Answer for '{question.id}' must be a string option id."
        valid_option_ids = {opt.id for opt in question.options}
        if value not in valid_option_ids:
            return False, None, f"Option '{value}' is not valid for question '{question.id}'."
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
                return False, None, f"Option '{item}' is not valid for question '{question.id}'."
            if item not in seen:
                seen.add(item)
                sanitized.append(item)
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

    elif q_type in ("scale", "slider"):
        # Booleans are a subclass of int in Python (isinstance(True, int) is True), so check bool explicitly!
        # Also reject floats (even 3.0) per Assumption c.
        if isinstance(value, bool) or not isinstance(value, int):
            return False, None, f"Answer for '{question.id}' must be an integer, got {type(value).__name__}."
        min_val = question.min if question.min is not None else 0
        max_val = question.max if question.max is not None else 10
        if not (min_val <= value <= max_val):
            return False, None, f"Value {value} for '{question.id}' is out of range [{min_val}, {max_val}]."
        return True, value, None

    return False, None, f"Unknown question type '{q_type}'."


def validate_answers_payload(
    answers: dict[str, Any]
) -> tuple[bool, dict[str, Any], Optional[str]]:
    """
    Validates an entire answers dict in an all-or-nothing manner.
    Returns: (is_valid, updates_dict, error_message)
    updates_dict maps question_id -> value (or None if answer should be cleared).
    """
    updates: dict[str, Any] = {}

    for q_id, val in answers.items():
        question = ALL_QUESTIONS_MAP.get(q_id)
        if question is None:
            return False, {}, f"Unknown question id: '{q_id}'"

        is_valid, sanitized_val, err = validate_single_answer(question, val)
        if not is_valid:
            return False, {}, err

        updates[q_id] = sanitized_val

    return True, updates, None
