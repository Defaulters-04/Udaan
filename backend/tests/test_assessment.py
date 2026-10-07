import pytest
from fastapi.testclient import TestClient

from app.assessment.bank import (
    ALL_QUESTIONS_MAP,
    PUBLIC_QUESTION_ALLOWED_KEYS,
    REQUIRED_QUESTION_IDS,
    SECTIONS_ORDER,
)
from app.config import settings
from app.main import app
from app.store.families import family_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_store():
    family_store.clear()
    original_ttl = settings.family_ttl_minutes
    yield
    settings.family_ttl_minutes = original_ttl
    family_store.clear()


def create_linked_family():
    create_res = client.post(
        "/families",
        json={"role": "student", "name": "Aarav", "lang": "en"},
    )
    assert create_res.status_code == 201
    create_data = create_res.json()
    code = create_data["family_code"]
    student_token = create_data["member_token"]

    join_res = client.post(
        f"/families/{code}/join",
        json={"role": "parent", "name": "Sunita", "lang": "hi"},
    )
    assert join_res.status_code == 200
    parent_token = join_res.json()["member_token"]

    return code, student_token, parent_token


def test_bank_integrity():
    assert len(ALL_QUESTIONS_MAP) == 26
    section_counts = [len(s.questions) for s in SECTIONS_ORDER]
    assert section_counts == [4, 12, 4, 5, 1]

    # Unique IDs
    ids = list(ALL_QUESTIONS_MAP.keys())
    assert len(ids) == len(set(ids))

    # Check interest dimensions
    interests = [q for q in ALL_QUESTIONS_MAP.values() if q.id.startswith("int_")]
    assert len(interests) == 12
    dim_counts = {}
    last_dim = None
    for q in interests:
        assert q.min == 1 and q.max == 5
        assert q.dimension is not None
        assert q.dimension != last_dim  # No two adjacent items share dimension
        last_dim = q.dimension
        dim_counts[q.dimension] = dim_counts.get(q.dimension, 0) + 1
    assert set(dim_counts.keys()) == {"R", "I", "A", "S", "E", "C"}
    for count in dim_counts.values():
        assert count == 2

    # Check aptitude questions
    aptitude = [q for q in ALL_QUESTIONS_MAP.values() if q.id.startswith("apt_")]
    assert len(aptitude) == 4
    correct_positions = set()
    for q in aptitude:
        assert len(q.options) == 4
        assert [opt.id for opt in q.options] == ["a", "b", "c", "d"]
        assert q.correct_option_id in ["a", "b", "c", "d"]
        correct_positions.add(q.correct_option_id)
    assert correct_positions == {"a", "b", "c", "d"}

    # Check values questions
    values = [q for q in ALL_QUESTIONS_MAP.values() if q.id.startswith("val_")]
    assert len(values) == 5
    for q in values:
        assert q.min == 0 and q.max == 10

    # Check free text
    ft = ALL_QUESTIONS_MAP["free_text_1"]
    assert ft.required is False
    assert ft.max_length == 600

    # Check localized strings
    for q in ALL_QUESTIONS_MAP.values():
        assert len(q.prompt_en.strip()) > 0
        assert len(q.prompt_hi.strip()) > 0
        for opt in q.options:
            assert len(opt.label_en.strip()) > 0
            assert len(opt.label_hi.strip()) > 0


def test_no_leaks_in_questions_endpoint():
    code, student_token, _ = create_linked_family()

    res = client.get(
        f"/families/{code}/assessment/questions",
        headers={"X-Member-Token": student_token},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["version"] == "starter-1"

    forbidden_substrings = ["correct", "answer", "key", "dimension", "score", "riasec"]

    def inspect_object(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                for forbidden in forbidden_substrings:
                    assert forbidden not in k.lower(), f"Forbidden key found: {k}"
                inspect_object(v)
        elif isinstance(obj, list):
            for item in obj:
                inspect_object(item)

    inspect_object(data)

    # Check every question and option in response conforms strictly to contract
    for sec in data["sections"]:
        assert sec["id"] in ["background", "interests", "aptitude", "values", "free_text"]
        assert "en" in sec["title"] and "hi" in sec["title"]
        for q in sec["questions"]:
            assert set(q.keys()).issubset(PUBLIC_QUESTION_ALLOWED_KEYS)
            if "options" in q:
                for opt in q["options"]:
                    assert set(opt.keys()) == {"id", "label"}
                    assert set(opt["label"].keys()) == {"en", "hi"}


def test_auth_and_role_errors_on_all_endpoints():
    code, student_token, parent_token = create_linked_family()

    endpoints = [
        ("GET", f"/families/{code}/assessment/questions", None),
        ("GET", f"/families/{code}/assessment/progress", None),
        ("PUT", f"/families/{code}/assessment/answers", {"answers": {}}),
        ("POST", f"/families/{code}/assessment/submit", None),
    ]

    for method, url, payload in endpoints:
        # 1. Missing token -> 401
        res1 = client.request(method, url, json=payload)
        assert res1.status_code == 401
        assert res1.json()["error"]["code"] == "invalid_token"

        # 2. Invalid token -> 401
        res2 = client.request(method, url, headers={"X-Member-Token": "bad_token"}, json=payload)
        assert res2.status_code == 401
        assert res2.json()["error"]["code"] == "invalid_token"

        # 3. Family not found -> 404
        fake_url = url.replace(code, "NONEX1")
        res3 = client.request(method, fake_url, headers={"X-Member-Token": student_token}, json=payload)
        assert res3.status_code == 404
        assert res3.json()["error"]["code"] == "family_not_found"

        # 4. Parent caller -> 403 wrong_role
        res4 = client.request(method, url, headers={"X-Member-Token": parent_token}, json=payload)
        assert res4.status_code == 403
        assert res4.json()["error"]["code"] == "wrong_role"


def test_put_answers_resume_merge_and_clear():
    code, student_token, _ = create_linked_family()

    # Empty put returns 200 and changes nothing (Assumption c)
    res0 = client.put(
        f"/families/{code}/assessment/answers",
        headers={"X-Member-Token": student_token},
        json={"answers": {}},
    )
    assert res0.status_code == 200
    assert res0.json() == {"answered": 0, "total": 26}

    # 1. Partial answers
    res1 = client.put(
        f"/families/{code}/assessment/answers",
        headers={"X-Member-Token": student_token},
        json={
            "answers": {
                "bg_stream": "science_maths",
                "bg_district": "Jaipur",
                "int_01": 5,
            }
        },
    )
    assert res1.status_code == 200
    assert res1.json() == {"answered": 3, "total": 26}

    # GET progress
    prog1 = client.get(
        f"/families/{code}/assessment/progress",
        headers={"X-Member-Token": student_token},
    )
    assert prog1.status_code == 200
    assert prog1.json()["answers"] == {
        "bg_stream": "science_maths",
        "bg_district": "Jaipur",
        "int_01": 5,
    }
    assert prog1.json()["submitted"] is False

    # 2. Merge and overwrite
    res2 = client.put(
        f"/families/{code}/assessment/answers",
        headers={"X-Member-Token": student_token},
        json={
            "answers": {
                "int_01": 2,
                "int_02": 4,
            }
        },
    )
    assert res2.status_code == 200
    assert res2.json() == {"answered": 4, "total": 26}

    prog2 = client.get(
        f"/families/{code}/assessment/progress",
        headers={"X-Member-Token": student_token},
    )
    assert prog2.json()["answers"]["int_01"] == 2
    assert prog2.json()["answers"]["int_02"] == 4

    # 3. Clearing answers via empty string and empty list (Assumption b)
    res3 = client.put(
        f"/families/{code}/assessment/answers",
        headers={"X-Member-Token": student_token},
        json={
            "answers": {
                "bg_district": "   ",  # clears text
                "int_01": None,  # clears int
            }
        },
    )
    assert res3.status_code == 200
    assert res3.json() == {"answered": 2, "total": 26}

    prog3 = client.get(
        f"/families/{code}/assessment/progress",
        headers={"X-Member-Token": student_token},
    )
    assert "bg_district" not in prog3.json()["answers"]
    assert "int_01" not in prog3.json()["answers"]
    assert "bg_stream" in prog3.json()["answers"]


def test_put_answers_validation_all_or_nothing():
    code, student_token, _ = create_linked_family()

    # Save 1 answer first
    client.put(
        f"/families/{code}/assessment/answers",
        headers={"X-Member-Token": student_token},
        json={"answers": {"bg_stream": "commerce"}},
    )

    invalid_cases = [
        {"unknown_question_id": "val"},
        {"bg_stream": "invalid_option"},
        {"bg_languages": ["english", "invalid_lang"]},
        {"bg_languages": "not_a_list"},
        {"bg_district": "First Line\nSecond Line"},  # Line break in text
        {"bg_district": "A" * 61},  # Exceeds max_length
        {"int_01": 6},  # Scale out of range
        {"int_01": 0},  # Scale out of range
        {"int_01": True},  # Boolean rejected for int (Assumption c)
        {"int_01": 3.0},  # Float rejected for int (even 3.0, Assumption c)
        {"val_security": 11},  # Slider out of range
        {"free_text_1": "B" * 601},  # Long text exceeds max_length
    ]

    for bad_answers in invalid_cases:
        # Mix a valid update with the bad update
        payload = {"answers": {"int_02": 5, **bad_answers}}
        res = client.put(
            f"/families/{code}/assessment/answers",
            headers={"X-Member-Token": student_token},
            json=payload,
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "validation_error"
        assert "missing" not in res.json()["error"]

        # Ensure all-or-nothing: int_02 was NOT saved
        prog = client.get(
            f"/families/{code}/assessment/progress",
            headers={"X-Member-Token": student_token},
        )
        assert "int_02" not in prog.json()["answers"]
        assert prog.json()["answers"] == {"bg_stream": "commerce"}


def test_submit_flow_incomplete_idempotent_and_status_done():
    code, student_token, parent_token = create_linked_family()

    # 1. Submit before answering required questions -> 422 assessment_incomplete
    submit_res1 = client.post(
        f"/families/{code}/assessment/submit",
        headers={"X-Member-Token": student_token},
    )
    assert submit_res1.status_code == 422
    err_body = submit_res1.json()
    assert err_body["error"]["code"] == "assessment_incomplete"
    assert "missing" in err_body["error"]
    assert err_body["error"]["missing"] == REQUIRED_QUESTION_IDS  # Bank order (Assumption f)

    # 2. Answer all required questions
    full_answers = {
        "bg_stream": "science_bio",
        "bg_marks_band": "75_90",
        "bg_district": "Lucknow",
        "bg_languages": ["hindi", "english"],
        "int_01": 4,
        "int_02": 3,
        "int_03": 5,
        "int_04": 2,
        "int_05": 4,
        "int_06": 3,
        "int_07": 4,
        "int_08": 5,
        "int_09": 3,
        "int_10": 4,
        "int_11": 2,
        "int_12": 1,
        "apt_spatial": "a",
        "apt_numerical": "b",
        "apt_verbal": "c",
        "apt_logical": "d",
        "val_security": 8,
        "val_independence": 9,
        "val_helping": 7,
        "val_income": 9,
        "val_creativity": 6,
    }
    # Note: free_text_1 is optional, leaving it unanswered

    put_res = client.put(
        f"/families/{code}/assessment/answers",
        headers={"X-Member-Token": student_token},
        json={"answers": full_answers},
    )
    assert put_res.status_code == 200
    assert put_res.json() == {"answered": 25, "total": 26}

    # Verify status done is False before submit
    status_student_before = client.get(
        f"/families/{code}/status",
        headers={"X-Member-Token": student_token},
    ).json()
    assert status_student_before["you"]["done"] is False
    assert status_student_before["partner"]["done"] is False

    # 3. Successful submit
    submit_res2 = client.post(
        f"/families/{code}/assessment/submit",
        headers={"X-Member-Token": student_token},
    )
    assert submit_res2.status_code == 200
    assert submit_res2.json() == {"submitted": True}

    # 4. Idempotent submit
    submit_res3 = client.post(
        f"/families/{code}/assessment/submit",
        headers={"X-Member-Token": student_token},
    )
    assert submit_res3.status_code == 200
    assert submit_res3.json() == {"submitted": True}

    # 5. After submit: PUT returns 409 already_submitted
    put_after_submit = client.put(
        f"/families/{code}/assessment/answers",
        headers={"X-Member-Token": student_token},
        json={"answers": {"int_01": 1}},
    )
    assert put_after_submit.status_code == 409
    assert put_after_submit.json()["error"]["code"] == "already_submitted"

    # Stored answers unchanged
    prog = client.get(
        f"/families/{code}/assessment/progress",
        headers={"X-Member-Token": student_token},
    ).json()
    assert prog["submitted"] is True
    assert prog["answers"]["int_01"] == 4

    # 6. Verify GET /status reflections
    student_status = client.get(
        f"/families/{code}/status",
        headers={"X-Member-Token": student_token},
    ).json()
    assert student_status["you"]["done"] is True
    assert student_status["partner"]["done"] is False

    parent_status = client.get(
        f"/families/{code}/status",
        headers={"X-Member-Token": parent_token},
    ).json()
    assert parent_status["you"]["done"] is False
    assert parent_status["partner"]["done"] is True
