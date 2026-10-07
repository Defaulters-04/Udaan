import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.intake.bank import (
    ALL_INTAKE_QUESTIONS_MAP,
    CAREER_DOMAINS,
    PUBLIC_QUESTION_ALLOWED_KEYS,
    REQUIRED_QUESTION_IDS,
    SECTIONS_ORDER,
)
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
    code = create_res.json()["family_code"]
    student_token = create_res.json()["member_token"]

    join_res = client.post(
        f"/families/{code}/join",
        json={"role": "parent", "name": "Sunita", "lang": "hi"},
    )
    assert join_res.status_code == 200
    parent_token = join_res.json()["member_token"]

    return code, student_token, parent_token


def test_bank_integrity():
    assert len(ALL_INTAKE_QUESTIONS_MAP) == 14
    section_counts = [len(s.questions) for s in SECTIONS_ORDER]
    assert section_counts == [3, 3, 2, 3, 3]

    # Unique IDs
    ids = list(ALL_INTAKE_QUESTIONS_MAP.keys())
    assert len(ids) == len(set(ids))

    # Required / optional checks
    optional_ids = {q.id for q in ALL_INTAKE_QUESTIONS_MAP.values() if not q.required}
    assert optional_ids == {"non_negotiables", "hope_text"}

    # domain_wish and max_select
    for q in ALL_INTAKE_QUESTIONS_MAP.values():
        if q.id == "domain_wish":
            assert q.max_select == 3
        else:
            assert q.max_select is None

    # guess_domain options
    domain_ids = [d.id for d in CAREER_DOMAINS]
    assert len(domain_ids) == 8
    guess_domain_opts = [opt.id for opt in ALL_INTAKE_QUESTIONS_MAP["guess_domain"].options]
    assert guess_domain_opts == [*domain_ids, "not_sure"]

    # risk questions
    for r_id in ["risk_1", "risk_2", "risk_3"]:
        opt_ids = [opt.id for opt in ALL_INTAKE_QUESTIONS_MAP[r_id].options]
        assert opt_ids == ["safe", "gamble"]

    # hope_text max_length
    assert ALL_INTAKE_QUESTIONS_MAP["hope_text"].max_length == 600

    # Localized strings
    for q in ALL_INTAKE_QUESTIONS_MAP.values():
        assert len(q.prompt_en.strip()) > 0
        assert len(q.prompt_hi.strip()) > 0
        for opt in q.options:
            assert len(opt.label_en.strip()) > 0
            assert len(opt.label_hi.strip()) > 0
        if q.placeholder_en is not None:
            assert len(q.placeholder_en.strip()) > 0
            assert len(q.placeholder_hi.strip()) > 0


def test_no_leaks_in_intake_endpoints():
    code, _, parent_token = create_linked_family()

    res = client.get(
        f"/families/{code}/intake/questions",
        headers={"X-Member-Token": parent_token},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["version"] == "starter-1"

    forbidden_substrings = ["correct", "answer", "key", "dimension", "score", "tag"]

    def inspect_object(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                for forbidden in forbidden_substrings:
                    assert forbidden not in k.lower(), f"Forbidden key found: {k}"
                # Check internal tag string perception_domain is not present
                if isinstance(v, str):
                    assert v != "perception_domain", "Internal tag leaked in value"
                inspect_object(v)
        elif isinstance(obj, list):
            for item in obj:
                inspect_object(item)

    inspect_object(data)

    for sec in data["sections"]:
        assert sec["id"] in ["money", "risk", "plans", "hopes", "perception"]
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
        ("GET", f"/families/{code}/intake/questions", None),
        ("GET", f"/families/{code}/intake/progress", None),
        ("PUT", f"/families/{code}/intake/answers", {"answers": {}}),
        ("POST", f"/families/{code}/intake/submit", None),
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
        res3 = client.request(method, fake_url, headers={"X-Member-Token": parent_token}, json=payload)
        assert res3.status_code == 404
        assert res3.json()["error"]["code"] == "family_not_found"

        # 4. Student caller -> 403 wrong_role
        res4 = client.request(method, url, headers={"X-Member-Token": student_token}, json=payload)
        assert res4.status_code == 403
        assert res4.json()["error"]["code"] == "wrong_role"


def test_put_answers_resume_merge_and_clear():
    code, _, parent_token = create_linked_family()

    # Empty put returns 200 and changes nothing (Assumption c)
    res0 = client.put(
        f"/families/{code}/intake/answers",
        headers={"X-Member-Token": parent_token},
        json={"answers": {}},
    )
    assert res0.status_code == 200
    assert res0.json() == {"answered": 0, "total": 14}

    # 1. Partial answers
    res1 = client.put(
        f"/families/{code}/intake/answers",
        headers={"X-Member-Token": parent_token},
        json={
            "answers": {
                "income_band": "6_12l",
                "risk_1": "safe",
                "domain_wish": ["eng_tech", "science_research"],
            }
        },
    )
    assert res1.status_code == 200
    assert res1.json() == {"answered": 3, "total": 14}

    # GET progress
    prog1 = client.get(
        f"/families/{code}/intake/progress",
        headers={"X-Member-Token": parent_token},
    )
    assert prog1.status_code == 200
    assert prog1.json()["answers"] == {
        "income_band": "6_12l",
        "risk_1": "safe",
        "domain_wish": ["eng_tech", "science_research"],
    }
    assert prog1.json()["submitted"] is False

    # 2. Merge and overwrite
    res2 = client.put(
        f"/families/{code}/intake/answers",
        headers={"X-Member-Token": parent_token},
        json={
            "answers": {
                "income_band": "12_25l",
                "savings_band": "3_8l",
            }
        },
    )
    assert res2.status_code == 200
    assert res2.json() == {"answered": 4, "total": 14}

    prog2 = client.get(
        f"/families/{code}/intake/progress",
        headers={"X-Member-Token": parent_token},
    )
    assert prog2.json()["answers"]["income_band"] == "12_25l"
    assert prog2.json()["answers"]["savings_band"] == "3_8l"

    # 3. Clearing answers via empty string, whitespace, empty list, and None
    res3 = client.put(
        f"/families/{code}/intake/answers",
        headers={"X-Member-Token": parent_token},
        json={
            "answers": {
                "income_band": "   ",  # clears
                "domain_wish": [],     # clears
                "risk_1": None,        # clears
            }
        },
    )
    assert res3.status_code == 200
    assert res3.json() == {"answered": 1, "total": 14}

    prog3 = client.get(
        f"/families/{code}/intake/progress",
        headers={"X-Member-Token": parent_token},
    )
    assert "income_band" not in prog3.json()["answers"]
    assert "domain_wish" not in prog3.json()["answers"]
    assert "risk_1" not in prog3.json()["answers"]
    assert prog3.json()["answers"] == {"savings_band": "3_8l"}


def test_max_select_validation():
    code, _, parent_token = create_linked_family()

    # 3 selected passes
    res_ok = client.put(
        f"/families/{code}/intake/answers",
        headers={"X-Member-Token": parent_token},
        json={"answers": {"domain_wish": ["eng_tech", "medicine_health", "business_finance"]}},
    )
    assert res_ok.status_code == 200

    # 4 selected fails (422)
    res_err = client.put(
        f"/families/{code}/intake/answers",
        headers={"X-Member-Token": parent_token},
        json={
            "answers": {
                "domain_wish": [
                    "eng_tech",
                    "medicine_health",
                    "business_finance",
                    "design_creative",
                ]
            }
        },
    )
    assert res_err.status_code == 422
    assert res_err.json()["error"]["code"] == "validation_error"

    # Verify nothing was saved on 422
    prog = client.get(
        f"/families/{code}/intake/progress",
        headers={"X-Member-Token": parent_token},
    )
    assert prog.json()["answers"]["domain_wish"] == [
        "eng_tech",
        "medicine_health",
        "business_finance",
    ]


def test_put_answers_validation_all_or_nothing_and_no_value_echo():
    code, _, parent_token = create_linked_family()

    # Save 1 answer first
    client.put(
        f"/families/{code}/intake/answers",
        headers={"X-Member-Token": parent_token},
        json={"answers": {"income_band": "6_12l"}},
    )

    sensitive_string = "SUPER_SECRET_VALUE_99999"

    invalid_cases = [
        {"unknown_question_id": sensitive_string},
        {"income_band": sensitive_string},
        {"loan_band": 123},
        {"risk_1": "not_an_option"},
        {"domain_wish": ["eng_tech", sensitive_string]},
        {"domain_wish": "not_a_list"},
        {"hope_text": "C" * 601},
        {"hope_text": 123},
    ]

    for bad_answers in invalid_cases:
        # Mix a valid update with the bad update
        payload = {"answers": {"savings_band": "1_3l", **bad_answers}}
        res = client.put(
            f"/families/{code}/intake/answers",
            headers={"X-Member-Token": parent_token},
            json=payload,
        )
        assert res.status_code == 422
        body_text = res.text
        assert res.json()["error"]["code"] == "validation_error"
        assert "missing" not in res.json()["error"]

        # Sensitive value must NEVER be echoed anywhere in the response!
        assert sensitive_string not in body_text

        # Ensure all-or-nothing: savings_band was NOT saved
        prog = client.get(
            f"/families/{code}/intake/progress",
            headers={"X-Member-Token": parent_token},
        )
        assert "savings_band" not in prog.json()["answers"]
        assert prog.json()["answers"] == {"income_band": "6_12l"}


def test_submit_flow_incomplete_idempotent_and_status_done():
    code, student_token, parent_token = create_linked_family()

    # 1. Submit before answering required questions -> 422 intake_incomplete
    submit_res1 = client.post(
        f"/families/{code}/intake/submit",
        headers={"X-Member-Token": parent_token},
    )
    assert submit_res1.status_code == 422
    err_body = submit_res1.json()
    assert err_body["error"]["code"] == "intake_incomplete"
    assert "missing" in err_body["error"]
    assert err_body["error"]["missing"] == REQUIRED_QUESTION_IDS  # Bank order

    # 2. Answer all required questions (leave optional non_negotiables and hope_text empty)
    full_answers = {
        "income_band": "6_12l",
        "savings_band": "3_8l",
        "loan_band": "up_to_3l",
        "risk_1": "safe",
        "risk_2": "gamble",
        "risk_3": "safe",
        "relocation": "same_state",
        "time_to_earn": "five_six",
        "domain_wish": ["eng_tech", "business_finance"],
        "guess_domain": "eng_tech",
        "guess_relocation": "same_state",
        "guess_risk": "medium",
    }

    put_res = client.put(
        f"/families/{code}/intake/answers",
        headers={"X-Member-Token": parent_token},
        json={"answers": full_answers},
    )
    assert put_res.status_code == 200
    assert put_res.json() == {"answered": 12, "total": 14}

    # Verify status done is False before submit
    status_parent_before = client.get(
        f"/families/{code}/status",
        headers={"X-Member-Token": parent_token},
    ).json()
    assert status_parent_before["you"]["done"] is False
    assert status_parent_before["partner"]["done"] is False

    # 3. Successful submit
    submit_res2 = client.post(
        f"/families/{code}/intake/submit",
        headers={"X-Member-Token": parent_token},
    )
    assert submit_res2.status_code == 200
    assert submit_res2.json() == {"submitted": True}

    # 4. Idempotent submit
    submit_res3 = client.post(
        f"/families/{code}/intake/submit",
        headers={"X-Member-Token": parent_token},
    )
    assert submit_res3.status_code == 200
    assert submit_res3.json() == {"submitted": True}

    # 5. After submit: PUT returns 409 already_submitted
    put_after_submit = client.put(
        f"/families/{code}/intake/answers",
        headers={"X-Member-Token": parent_token},
        json={"answers": {"income_band": "over_25l"}},
    )
    assert put_after_submit.status_code == 409
    assert put_after_submit.json()["error"]["code"] == "already_submitted"

    # Stored answers unchanged
    prog = client.get(
        f"/families/{code}/intake/progress",
        headers={"X-Member-Token": parent_token},
    ).json()
    assert prog["submitted"] is True
    assert prog["answers"]["income_band"] == "6_12l"

    # 6. Verify GET /status reflections
    parent_status = client.get(
        f"/families/{code}/status",
        headers={"X-Member-Token": parent_token},
    ).json()
    assert parent_status["you"]["done"] is True
    assert parent_status["partner"]["done"] is False

    student_status = client.get(
        f"/families/{code}/status",
        headers={"X-Member-Token": student_token},
    ).json()
    assert student_status["you"]["done"] is False
    assert student_status["partner"]["done"] is True


def test_privacy_and_cross_member_isolation():
    code, student_token, parent_token = create_linked_family()

    # Student puts assessment answers
    client.put(
        f"/families/{code}/assessment/answers",
        headers={"X-Member-Token": student_token},
        json={"answers": {"bg_stream": "arts"}},
    )

    # Parent puts intake answers
    client.put(
        f"/families/{code}/intake/answers",
        headers={"X-Member-Token": parent_token},
        json={"answers": {"income_band": "under_3l", "hope_text": "I hope they find peace."}},
    )

    # 1. Student progress never contains intake answers
    student_prog = client.get(
        f"/families/{code}/assessment/progress",
        headers={"X-Member-Token": student_token},
    ).json()
    assert "income_band" not in student_prog["answers"]
    assert "hope_text" not in student_prog["answers"]
    assert student_prog["answers"] == {"bg_stream": "arts"}

    # 2. Parent progress never contains student assessment answers
    parent_prog = client.get(
        f"/families/{code}/intake/progress",
        headers={"X-Member-Token": parent_token},
    ).json()
    assert "bg_stream" not in parent_prog["answers"]
    assert parent_prog["answers"]["income_band"] == "under_3l"
    assert parent_prog["answers"]["hope_text"] == "I hope they find peace."

    # 3. Student /status contains NO intake answer values
    student_status = client.get(
        f"/families/{code}/status",
        headers={"X-Member-Token": student_token},
    ).json()
    status_str = str(student_status)
    assert "under_3l" not in status_str
    assert "I hope they find peace." not in status_str
