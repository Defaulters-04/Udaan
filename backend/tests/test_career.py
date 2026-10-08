from __future__ import annotations

import logging
import time
from typing import Any
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.career import get_all_known_career_ids
from app.store.families import family_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_store():
    family_store.clear()
    yield
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


def default_student_answers(**overrides):
    base = {
        "bg_stream": "science_maths",
        "bg_marks_band": "75_90",
        "bg_district": "Lucknow",
        "bg_languages": ["hindi", "english"],
        "int_01": 4, "int_02": 3, "int_03": 5, "int_04": 2,
        "int_05": 4, "int_06": 3, "int_07": 4, "int_08": 5,
        "int_09": 3, "int_10": 4, "int_11": 2, "int_12": 1,
        "apt_spatial": "a",
        "apt_numerical": "c",
        "apt_verbal": "c",
        "apt_logical": "d",
        "val_security": 8,
        "val_independence": 9,
        "val_helping": 7,
        "val_income": 9,
        "val_creativity": 6,
        "pref_risk_1": "safe",
        "pref_risk_2": "gamble",
        "pref_risk_3": "gamble",
        "pref_relocation": "anywhere_india",
        "pref_time_to_earn": "within_4y",
        "pref_domain_wish": ["tech_engineering", "business_management"],
        "free_text_1": "Focused on AI and open source",
    }
    base.update(overrides)
    return base


def default_parent_answers(**overrides):
    base = {
        "income_band": "6_12l",
        "savings_band": "3_8l",
        "loan_band": "up_to_3l",
        "surplus_band": "5k_15k",
        "emi_band": "under_5k",
        "risk_1": "safe",
        "risk_2": "safe",
        "risk_3": "safe",
        "relocation": "same_state",
        "time_to_earn": "five_six",
        "domain_wish": ["business_management", "tech_engineering"],
        "guess_domain": "tech_engineering",
        "guess_relocation": "same_state",
        "guess_risk": "medium",
        "hope_text": "I hope my child finds happiness and success",
    }
    base.update(overrides)
    return base


def submit_student(code: str, token: str, answers: dict[str, Any] | None = None):
    ans = answers if answers is not None else default_student_answers()
    put_res = client.put(
        f"/families/{code}/assessment/answers",
        headers={"X-Member-Token": token},
        json={"answers": ans},
    )
    assert put_res.status_code == 200
    sub_res = client.post(
        f"/families/{code}/assessment/submit",
        headers={"X-Member-Token": token},
    )
    assert sub_res.status_code == 200


def submit_parent(code: str, token: str, answers: dict[str, Any] | None = None):
    ans = answers if answers is not None else default_parent_answers()
    put_res = client.put(
        f"/families/{code}/intake/answers",
        headers={"X-Member-Token": token},
        json={"answers": ans},
    )
    assert put_res.status_code == 200
    sub_res = client.post(
        f"/families/{code}/intake/submit",
        headers={"X-Member-Token": token},
    )
    assert sub_res.status_code == 200


# ---------------------------------------------------------------------------
# 1. Error Codes & Check Order
# ---------------------------------------------------------------------------
def test_career_error_codes_and_check_order():
    code, student_token, parent_token = create_linked_family()

    # 401 cases: no token, empty token, junk token
    res_no_tok = client.get(f"/families/{code}/careers/software_developer")
    assert res_no_tok.status_code == 401
    assert res_no_tok.json()["error"]["code"] == "invalid_token"

    res_empty_tok = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": "   "},
    )
    assert res_empty_tok.status_code == 401
    assert res_empty_tok.json()["error"]["code"] == "invalid_token"

    res_inv_tok = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": "invalid_fake_token_123"},
    )
    assert res_inv_tok.status_code == 401
    assert res_inv_tok.json()["error"]["code"] == "invalid_token"

    # Token belonging to another family: returns 401 invalid_token
    code_other, student_other, _ = create_linked_family()
    res_other = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": student_other},
    )
    assert res_other.status_code == 401
    assert res_other.json()["error"]["code"] == "invalid_token"

    # 404 family_not_found
    res_404_fam = client.get(
        "/families/UNKNOWN404/careers/software_developer",
        headers={"X-Member-Token": student_token},
    )
    assert res_404_fam.status_code == 404
    assert res_404_fam.json()["error"]["code"] == "family_not_found"

    # Check order: missing token on unknown family -> 401 invalid_token (token checked first)
    res_no_tok_unknown_fam = client.get("/families/UNKNOWN404/careers/software_developer")
    assert res_no_tok_unknown_fam.status_code == 401
    assert res_no_tok_unknown_fam.json()["error"]["code"] == "invalid_token"

    # Check order: token provided, but family unknown -> 404 family_not_found (family checked second)
    res_tok_unknown_fam = client.get(
        "/families/UNKNOWN404/careers/software_developer",
        headers={"X-Member-Token": "some_token"},
    )
    assert res_tok_unknown_fam.status_code == 404
    assert res_tok_unknown_fam.json()["error"]["code"] == "family_not_found"

    # Check order: unknown career id checked BEFORE readiness (neither submitted)
    res_career_404_before_ready = client.get(
        f"/families/{code}/careers/non_existent_career_id",
        headers={"X-Member-Token": student_token},
    )
    assert res_career_404_before_ready.status_code == 404
    assert res_career_404_before_ready.json()["error"]["code"] == "career_not_found"

    # 409 explorer_not_ready: neither submitted (known career id)
    res_409_neither = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": student_token},
    )
    assert res_409_neither.status_code == 409
    assert res_409_neither.json()["error"]["code"] == "explorer_not_ready"

    # 409 explorer_not_ready: only student submitted
    submit_student(code, student_token)
    res_409_only_s = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": student_token},
    )
    assert res_409_only_s.status_code == 409
    assert res_409_only_s.json()["error"]["code"] == "explorer_not_ready"

    # 409 explorer_not_ready: only parent submitted (in separate family)
    code_p_only, s_p_only, p_p_only = create_linked_family()
    submit_parent(code_p_only, p_p_only)
    res_409_only_p = client.get(
        f"/families/{code_p_only}/careers/software_developer",
        headers={"X-Member-Token": p_p_only},
    )
    assert res_409_only_p.status_code == 409
    assert res_409_only_p.json()["error"]["code"] == "explorer_not_ready"

    # 200: both submitted -> success for both roles
    submit_parent(code, parent_token)
    res_s = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": student_token},
    )
    assert res_s.status_code == 200
    res_p = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": parent_token},
    )
    assert res_p.status_code == 200


# ---------------------------------------------------------------------------
# 2. Role Nulls & Information Hiding
# ---------------------------------------------------------------------------
def test_career_role_nulls_and_information_hiding():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    data_s = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": student_token},
    ).json()

    data_p = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": parent_token},
    ).json()

    # Student view: growth_areas is non-empty list of items, family_money is None
    assert isinstance(data_s["growth_areas"], list)
    assert len(data_s["growth_areas"]) > 0
    assert data_s["growth_areas"][0]["id"].startswith("gap_")
    assert data_s["growth_areas"][0]["text"]["en"] is not None
    assert data_s["growth_areas"][0]["text"]["hi"] is None
    assert data_s["family_money"] is None

    # Parent view: family_money is dict with loan_need and monthly_emi, growth_areas is None
    assert data_p["growth_areas"] is None
    assert isinstance(data_p["family_money"], dict)
    assert data_p["family_money"]["loan_need"] is not None
    assert data_p["family_money"]["monthly_emi"] is not None

    # All other fields identical
    common_keys = [
        "id", "name", "domain", "fit", "viability", "market", "years_to_income",
        "conflict", "in_compromise", "blocked", "routes", "entry_salary",
        "demand", "exams", "scholarships", "data_gaps",
    ]
    for k in common_keys:
        assert data_s[k] == data_p[k], f"Mismatch on common key: {k}"


# ---------------------------------------------------------------------------
# 3. Match with Explorer
# ---------------------------------------------------------------------------
def test_career_matches_explorer_values():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    exp_data = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": student_token},
    ).json()

    # Find careers with diverse statuses in Explorer
    careers_by_id = {c["id"]: c for c in exp_data["careers"]}

    # Pick a viable/compromise career, a blocked by cost or other, and a no_route_data
    test_cids = ["software_developer", "electronics_engineer"]
    # Add compromise career if one exists
    compromise_cids = [c["id"] for c in exp_data["careers"] if c["in_compromise"]]
    if compromise_cids:
        test_cids.append(compromise_cids[0])
    # Add a blocked career if not already included
    blocked_cids = [c["id"] for c in exp_data["careers"] if c["blocked"] is not None]
    if blocked_cids:
        test_cids.append(blocked_cids[0])

    for cid in set(test_cids):
        exp_c = careers_by_id[cid]
        detail = client.get(
            f"/families/{code}/careers/{cid}",
            headers={"X-Member-Token": student_token},
        ).json()

        assert detail["id"] == exp_c["id"]
        assert detail["fit"] == exp_c["fit"]
        assert detail["viability"] == exp_c["viability"]
        assert detail["market"] == exp_c["market"]
        assert detail["years_to_income"] == exp_c["years_to_income"]
        assert detail["conflict"] == exp_c["conflict"]
        assert detail["in_compromise"] == exp_c["in_compromise"]
        assert detail["blocked"] == exp_c["blocked"]
        assert detail["data_gaps"] == exp_c["data_gaps"]


# ---------------------------------------------------------------------------
# 4. Career with No Route Data
# ---------------------------------------------------------------------------
def test_career_no_route_data():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    # electronics_engineer has no route in route_costs.csv
    detail = client.get(
        f"/families/{code}/careers/electronics_engineer",
        headers={"X-Member-Token": student_token},
    ).json()

    assert detail["routes"] == []
    assert detail["blocked"] is not None
    assert detail["blocked"]["cause"] == "no_route_data"
    assert detail["blocked"]["remedies"] == []
    assert detail["family_money"] is None


# ---------------------------------------------------------------------------
# 5. cost_status Pass-through
# ---------------------------------------------------------------------------
def test_career_cost_status_passthrough():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    # software_developer has verified COMPLETE routes (e.g. route_sw_iitm)
    data_sw = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": student_token},
    ).json()
    assert len(data_sw["routes"]) > 0
    route_statuses = [r["cost_status"] for r in data_sw["routes"]]
    assert "COMPLETE" in route_statuses

    # doctor_mbbs has PARTIAL routes (e.g. route_med_aiims)
    data_med = client.get(
        f"/families/{code}/careers/doctor_mbbs",
        headers={"X-Member-Token": student_token},
    ).json()
    assert len(data_med["routes"]) > 0
    med_statuses = [r["cost_status"] for r in data_med["routes"]]
    assert "PARTIAL" in med_statuses


# ---------------------------------------------------------------------------
# 6. Forbidden-Field Scan & Strict Contract Allowlist
# ---------------------------------------------------------------------------
CONTRACT_ALLOWED_KEYS = {
    "root": {
        "id", "name", "domain", "fit", "viability", "market", "years_to_income",
        "conflict", "in_compromise", "blocked", "routes", "entry_salary",
        "demand", "exams", "scholarships", "growth_areas", "family_money", "data_gaps",
    },
    "name": {"en", "hi"},
    "blocked": {"gates", "cause", "remedies"},
    "remedy": {"id", "text"},
    "text": {"en", "hi"},
    "route": {"id", "label", "years", "total_cost", "cost_parts", "cost_status", "is_best"},
    "cost_parts": {"tuition", "living", "entrance"},
    "entry_salary": {"min", "median", "max", "unit", "source"},
    "demand": {"signal", "source"},
    "growth_area": {"id", "text"},
    "family_money": {"loan_need", "monthly_emi"},
}


def test_career_forbidden_field_scan():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    data_s = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": student_token},
    ).json()

    data_p = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": parent_token},
    ).json()

    # Top-level key set equals contract allowlist exactly
    assert set(data_s.keys()) == CONTRACT_ALLOWED_KEYS["root"]
    assert set(data_p.keys()) == CONTRACT_ALLOWED_KEYS["root"]

    # Student forbidden fields scan
    # family_money must be null
    assert data_s["family_money"] is None
    # Scan all keys and values in student response
    student_json_str = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": student_token},
    ).text.lower()

    # The student response must be free of parent financial answers and family_money details
    for forbidden in ["\"savings\":", "\"surplus\":", "\"emi\":", "\"income_band\":",
                      "\"loan_band\":", "\"loan_need\":", "\"monthly_emi\":"]:
        assert forbidden not in student_json_str, f"Forbidden term {forbidden} found in student response"

    # Parent forbidden fields scan
    # growth_areas must be null
    assert data_p["growth_areas"] is None
    parent_json_str = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": parent_token},
    ).text.lower()

    # Must contain no raw assessment question IDs or student free text
    for forbidden in ["\"bg_stream\":", "\"bg_marks_band\":", "\"int_01\":", "\"apt_spatial\":",
                      "\"val_security\":", "\"pref_risk_1\":", "software architect", "open source"]:
        assert forbidden not in parent_json_str, f"Forbidden term {forbidden} found in parent response"


# ---------------------------------------------------------------------------
# 7. Privacy & No Answer Logging
# ---------------------------------------------------------------------------
def test_career_privacy_and_no_logging(caplog):
    code, student_token, parent_token = create_linked_family()
    hope_secret = "DISTINCTIVE_HOPE_SECRET_987654"
    free_secret = "DISTINCTIVE_FREE_SECRET_123456"

    submit_student(
        code,
        student_token,
        default_student_answers(free_text_1=free_secret),
    )
    submit_parent(
        code,
        parent_token,
        default_parent_answers(hope_text=hope_secret),
    )

    caplog.set_level(logging.DEBUG)
    caplog.clear()

    res_s = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": student_token},
    )
    assert res_s.status_code == 200
    assert hope_secret not in res_s.text
    assert free_secret not in res_s.text

    res_p = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": parent_token},
    )
    assert res_p.status_code == 200
    assert hope_secret not in res_p.text
    assert free_secret not in res_p.text

    # Verify no log records leak private answers
    for record in caplog.records:
        msg = record.getMessage()
        assert hope_secret not in msg
        assert free_secret not in msg


# ---------------------------------------------------------------------------
# 8. Determinism
# ---------------------------------------------------------------------------
def test_career_determinism():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    res1 = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": student_token},
    )
    res2 = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": student_token},
    )
    assert res1.json() == res2.json()


# ---------------------------------------------------------------------------
# 9. Performance
# ---------------------------------------------------------------------------
def test_career_performance():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    # First call: computes explorer cache and career details
    t0 = time.perf_counter()
    res1 = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": student_token},
    )
    t1 = time.perf_counter()
    first_duration = t1 - t0
    assert res1.status_code == 200
    assert first_duration < 1.5, f"First call took {first_duration:.3f}s"

    # Repeat call: should hit cached explorer and return very quickly
    t2 = time.perf_counter()
    res2 = client.get(
        f"/families/{code}/careers/software_developer",
        headers={"X-Member-Token": student_token},
    )
    t3 = time.perf_counter()
    repeat_duration = t3 - t2
    assert res2.status_code == 200
    assert repeat_duration < 0.2, f"Repeat call took {repeat_duration:.3f}s"


# ---------------------------------------------------------------------------
# 10. Coverage Report Over All Careers (Step 7)
# ---------------------------------------------------------------------------
def test_career_coverage_report():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    all_cids = sorted(list(get_all_known_career_ids()))
    print(f"\n--- Coverage Report Across All {len(all_cids)} Careers ---")

    student_records = []
    parent_records = []

    for cid in all_cids:
        s_res = client.get(
            f"/families/{code}/careers/{cid}",
            headers={"X-Member-Token": student_token},
        ).json()
        student_records.append(s_res)

        p_res = client.get(
            f"/families/{code}/careers/{cid}",
            headers={"X-Member-Token": parent_token},
        ).json()
        parent_records.append(p_res)

    fields = [
        "id", "name", "domain", "fit", "viability", "market", "years_to_income",
        "conflict", "in_compromise", "blocked", "routes", "entry_salary",
        "demand", "exams", "scholarships", "growth_areas", "family_money", "data_gaps",
    ]

    print("\nField Coverage Summary (Across careers):")
    print(f"{'Field':<18} | {'Role':<8} | {'Filled':<8} | {'Null':<8} | {'Empty List':<10}")
    print("-" * 62)

    for field in fields:
        if field in ("growth_areas", "family_money"):
            # Role dependent
            for role_name, recs in [("student", student_records), ("parent", parent_records)]:
                filled = sum(1 for r in recs if r[field] not in (None, []))
                null_cnt = sum(1 for r in recs if r[field] is None)
                empty_list = sum(1 for r in recs if r[field] == [])
                print(f"{field:<18} | {role_name:<8} | {filled:<8} | {null_cnt:<8} | {empty_list:<10}")
        else:
            recs = student_records
            filled = sum(1 for r in recs if r[field] not in (None, []))
            null_cnt = sum(1 for r in recs if r[field] is None)
            empty_list = sum(1 for r in recs if r[field] == [])
            print(f"{field:<18} | {'both':<8} | {filled:<8} | {null_cnt:<8} | {empty_list:<10}")

    blocked_by_cause: dict[str, list[str]] = {}
    for r in student_records:
        if r["blocked"]:
            cause = r["blocked"]["cause"]
            blocked_by_cause.setdefault(cause, []).append(r["id"])

    print("\nBlocked Careers by Cause:")
    for cause, c_list in sorted(blocked_by_cause.items()):
        print(f"  Cause '{cause}' ({len(c_list)} careers): {', '.join(c_list)}")

    assert len(all_cids) >= 55
