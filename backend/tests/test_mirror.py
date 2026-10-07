from typing import Any
import pytest
from fastapi.testclient import TestClient

from app.assessment.bank import ALL_QUESTIONS_MAP as ALL_STUDENT_MAP
from app.intake.bank import ALL_INTAKE_QUESTIONS_MAP as ALL_PARENT_MAP
from app.main import app
from app.schemas.families import RoleEnum
from app.store.families import family_store
from engine.domains import CANONICAL_DOMAINS
from app.engine_bridge import build_engine_profiles

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
        "pref_risk_1": "safe",
        "pref_risk_2": "gamble",
        "pref_risk_3": "gamble",
        "pref_relocation": "anywhere_india",
        "pref_time_to_earn": "within_4y",
        "pref_domain_wish": ["tech_engineering", "business_management"],
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
# 1. Wording Tests
# ---------------------------------------------------------------------------
def test_wording_fixes_in_both_banks_and_languages():
    # Student pref_risk_3 prompt
    s_risk_3 = ALL_STUDENT_MAP["pref_risk_3"]
    assert s_risk_3.prompt_en == "Imagine one more pair of starting job offers. Which would you choose?"
    assert s_risk_3.prompt_hi == "एक और बार, मान लें कि आपके सामने नौकरी के ये दो विकल्प हैं। आप किसे चुनेंगे?"

    # Parent risk_3 prompt
    p_risk_3 = ALL_PARENT_MAP["risk_3"]
    assert p_risk_3.prompt_en == "Imagine one more pair of starting job offers. Which would you choose?"
    assert p_risk_3.prompt_hi == "एक और बार, मान लें कि आपके सामने नौकरी के ये दो विकल्प हैं। आप किसे चुनेंगे?"

    # time_to_earn options in student bank
    s_time = ALL_STUDENT_MAP["pref_time_to_earn"]
    s_options_by_id = {opt.id: opt for opt in s_time.options}

    assert s_options_by_id["within_4y"].label_en == "About 4 years (e.g., a regular degree, B.Tech or a diploma)"
    assert s_options_by_id["within_4y"].label_hi == "लगभग 4 साल (जैसे सामान्य डिग्री, बी.टेक या डिप्लोमा)"
    assert s_options_by_id["five_six"].label_en == "About 5 to 6 years (e.g., MBBS, 5-year law, or a degree plus a Master's)"
    assert s_options_by_id["five_six"].label_hi == "लगभग 5 से 6 साल (जैसे एमबीबीएस, 5 साल का लॉ, या डिग्री के बाद मास्टर्स)"
    assert s_options_by_id["seven_plus"].label_en == "7 years or more is fine (e.g., MD/MS or a PhD)"
    assert s_options_by_id["seven_plus"].label_hi == "7 साल या उससे ज़्यादा भी चलेगा (जैसे एमडी/एमएस या पीएचडी)"

    # time_to_earn options in parent bank
    p_time = ALL_PARENT_MAP["time_to_earn"]
    p_options_by_id = {opt.id: opt for opt in p_time.options}

    assert p_options_by_id["within_4y"].label_en == "About 4 years (e.g., a regular degree, B.Tech or a diploma)"
    assert p_options_by_id["within_4y"].label_hi == "लगभग 4 साल (जैसे सामान्य डिग्री, बी.टेक या डिप्लोमा)"
    assert p_options_by_id["five_six"].label_en == "About 5 to 6 years (e.g., MBBS, 5-year law, or a degree plus a Master's)"
    assert p_options_by_id["five_six"].label_hi == "लगभग 5 से 6 साल (जैसे एमबीबीएस, 5 साल का लॉ, या डिग्री के बाद मास्टर्स)"
    assert p_options_by_id["seven_plus"].label_en == "7 years or more is fine (e.g., MD/MS or a PhD)"
    assert p_options_by_id["seven_plus"].label_hi == "7 साल या उससे ज़्यादा भी चलेगा (जैसे एमडी/एमएस या पीएचडी)"


# ---------------------------------------------------------------------------
# 2. Readiness 409 Tests
# ---------------------------------------------------------------------------
def test_mirror_not_ready_when_neither_or_only_one_submitted():
    code, student_token, parent_token = create_linked_family()

    # Case 1: Neither submitted
    res_neither_s = client.get(
        f"/families/{code}/mirror",
        headers={"X-Member-Token": student_token},
    )
    assert res_neither_s.status_code == 409
    assert res_neither_s.json() == {
        "error": {
            "code": "mirror_not_ready",
            "message": "Both student and parent must submit before accessing the mirror",
        }
    }

    res_neither_p = client.get(
        f"/families/{code}/mirror",
        headers={"X-Member-Token": parent_token},
    )
    assert res_neither_p.status_code == 409
    assert res_neither_p.json()["error"]["code"] == "mirror_not_ready"

    # Case 2: Only student submitted
    submit_student(code, student_token)
    res_only_s = client.get(
        f"/families/{code}/mirror",
        headers={"X-Member-Token": student_token},
    )
    assert res_only_s.status_code == 409
    assert res_only_s.json()["error"]["code"] == "mirror_not_ready"

    # Case 3: Only parent submitted (in new family)
    code2, student_token2, parent_token2 = create_linked_family()
    submit_parent(code2, parent_token2)
    res_only_p = client.get(
        f"/families/{code2}/mirror",
        headers={"X-Member-Token": parent_token2},
    )
    assert res_only_p.status_code == 409
    assert res_only_p.json()["error"]["code"] == "mirror_not_ready"


# ---------------------------------------------------------------------------
# 3. Auth Tests: 401 & 404
# ---------------------------------------------------------------------------
def test_mirror_auth_401_and_404():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    # 401: Missing token
    res_no_tok = client.get(f"/families/{code}/mirror")
    assert res_no_tok.status_code == 401
    assert res_no_tok.json()["error"]["code"] == "invalid_token"

    # 401: Invalid token string
    res_inv_tok = client.get(
        f"/families/{code}/mirror",
        headers={"X-Member-Token": "bogus_random_token_123"},
    )
    assert res_inv_tok.status_code == 401
    assert res_inv_tok.json()["error"]["code"] == "invalid_token"

    # 401: Token from another family
    code_other, student_other, _ = create_linked_family()
    res_other_tok = client.get(
        f"/families/{code}/mirror",
        headers={"X-Member-Token": student_other},
    )
    assert res_other_tok.status_code == 401
    assert res_other_tok.json()["error"]["code"] == "invalid_token"

    # 404: Non-existent family
    res_404 = client.get(
        "/families/NONEXISTENT99/mirror",
        headers={"X-Member-Token": student_token},
    )
    assert res_404.status_code == 404
    assert res_404.json()["error"]["code"] == "family_not_found"


# ---------------------------------------------------------------------------
# 4. Success 200 & Identical Payload for Both Roles
# ---------------------------------------------------------------------------
def test_mirror_success_identical_for_both_roles():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    res_s = client.get(
        f"/families/{code}/mirror",
        headers={"X-Member-Token": student_token},
    )
    assert res_s.status_code == 200
    data_s = res_s.json()

    res_p = client.get(
        f"/families/{code}/mirror",
        headers={"X-Member-Token": parent_token},
    )
    assert res_p.status_code == 200
    data_p = res_p.json()

    # Both tokens receive strictly identical payload
    assert data_s == data_p


# ---------------------------------------------------------------------------
# 5. Exact Key Allowlist & No Leaks
# ---------------------------------------------------------------------------
def test_mirror_exact_key_allowlist_and_no_data_leakage():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    res = client.get(
        f"/families/{code}/mirror",
        headers={"X-Member-Token": student_token},
    )
    assert res.status_code == 200
    data = res.json()

    # Allowed keys specifications
    TOP_LEVEL_KEYS = {"conflict_index", "dimensions"}
    SCALE_DIM_KEYS = {"id", "gap", "weight", "kind", "steps", "student_step", "parent_step"}
    PICKS_DIM_KEYS = {"id", "gap", "weight", "kind", "options", "student_picks", "parent_picks", "parent_guess"}
    STEP_KEYS = {"id", "label"}
    LOCALIZED_KEYS = {"en", "hi"}

    assert set(data.keys()) == TOP_LEVEL_KEYS
    assert isinstance(data["conflict_index"], (int, float))
    assert isinstance(data["dimensions"], list)
    assert len(data["dimensions"]) == 4

    for dim in data["dimensions"]:
        kind = dim.get("kind")
        if kind == "scale":
            assert set(dim.keys()) == SCALE_DIM_KEYS
            assert dim["id"] in {"risk", "relocation", "time"}
            assert isinstance(dim["steps"], list)
            for step in dim["steps"]:
                assert set(step.keys()) == STEP_KEYS
                assert set(step["label"].keys()) == LOCALIZED_KEYS
        elif kind == "picks":
            assert set(dim.keys()) == PICKS_DIM_KEYS
            assert dim["id"] == "domain"
            assert isinstance(dim["options"], list)
            for opt in dim["options"]:
                assert set(opt.keys()) == STEP_KEYS
                assert set(opt["label"].keys()) == LOCALIZED_KEYS
        else:
            pytest.fail(f"Unexpected kind: {kind}")

    # Recursive check: no money fields, debug text, or hidden tags anywhere
    forbidden_tokens = [
        "income", "savings", "loan", "surplus", "emi",
        "is_high_conflict", "diagnosis", "explanation", "summary",
        "tag", "aptitude", "marks", "board", "stream", "riasec",
    ]

    def check_recursive(obj: Any):
        if isinstance(obj, dict):
            for k, v in obj.items():
                lower_k = str(k).lower()
                for token in forbidden_tokens:
                    assert token not in lower_k, f"Forbidden token '{token}' in key '{k}'"
                check_recursive(v)
        elif isinstance(obj, list):
            for item in obj:
                check_recursive(item)

    check_recursive(data)


# ---------------------------------------------------------------------------
# 6. Dimension Order
# ---------------------------------------------------------------------------
def test_mirror_dimension_order():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    res = client.get(
        f"/families/{code}/mirror",
        headers={"X-Member-Token": student_token},
    )
    assert res.status_code == 200
    dims = res.json()["dimensions"]
    assert [d["id"] for d in dims] == ["risk", "domain", "relocation", "time"]


# ---------------------------------------------------------------------------
# 7. Consistency Guard: Display Positions vs Engine Profiles
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "student_overrides,parent_overrides",
    [
        (
            {"pref_risk_1": "safe", "pref_risk_2": "safe", "pref_risk_3": "safe", "pref_relocation": "home_city", "pref_time_to_earn": "within_4y"},
            {"risk_1": "safe", "risk_2": "safe", "risk_3": "safe", "relocation": "home_city", "time_to_earn": "within_4y"},
        ),
        (
            {"pref_risk_1": "gamble", "pref_risk_2": "safe", "pref_risk_3": "safe", "pref_relocation": "same_state", "pref_time_to_earn": "five_six"},
            {"risk_1": "gamble", "risk_2": "gamble", "risk_3": "safe", "relocation": "anywhere_india", "time_to_earn": "seven_plus"},
        ),
        (
            {"pref_risk_1": "gamble", "pref_risk_2": "gamble", "pref_risk_3": "gamble", "pref_relocation": "abroad_ok", "pref_time_to_earn": "seven_plus"},
            {"risk_1": "safe", "risk_2": "gamble", "risk_3": "safe", "relocation": "home_city", "time_to_earn": "within_4y"},
        ),
    ],
)
def test_consistency_guard_display_never_drifts_from_engine(student_overrides, parent_overrides):
    code, student_token, parent_token = create_linked_family()
    s_ans = default_student_answers(**student_overrides)
    p_ans = default_parent_answers(**parent_overrides)

    submit_student(code, student_token, s_ans)
    submit_parent(code, parent_token, p_ans)

    # Call mirror
    res = client.get(
        f"/families/{code}/mirror",
        headers={"X-Member-Token": student_token},
    )
    assert res.status_code == 200
    data = res.json()

    # Re-build profiles to verify engine values
    fam = family_store.get_family_for_preview(code)
    assert fam is not None
    student_profile, parent_profile = build_engine_profiles(fam)

    dim_map = {d["id"]: d for d in data["dimensions"]}

    # 1. Risk consistency: step / (len(steps) - 1) within 0.02 of engine
    risk_dim = dim_map["risk"]
    num_steps_risk = len(risk_dim["steps"])
    assert num_steps_risk == 4
    student_risk_norm = risk_dim["student_step"] / (num_steps_risk - 1)
    parent_risk_norm = risk_dim["parent_step"] / (num_steps_risk - 1)

    assert abs(student_risk_norm - student_profile.risk_appetite) <= 0.02
    assert abs(parent_risk_norm - parent_profile.risk) <= 0.02

    # 2. Relocation consistency: step / (len(steps) - 1) within 0.02 of engine
    reloc_dim = dim_map["relocation"]
    num_steps_reloc = len(reloc_dim["steps"])
    assert num_steps_reloc == 4
    student_reloc_norm = reloc_dim["student_step"] / (num_steps_reloc - 1)
    parent_reloc_norm = reloc_dim["parent_step"] / (num_steps_reloc - 1)

    assert abs(student_reloc_norm - student_profile.relocation_willingness) <= 0.02
    assert abs(parent_reloc_norm - parent_profile.relocation_willingness) <= 0.02

    # 3. Time consistency: order of steps matches order of max_years_to_income
    time_dim = dim_map["time"]
    time_step_years = [4.0, 6.0, 8.0]
    expected_s_step = time_step_years.index(student_profile.max_years_to_income)
    expected_p_step = time_step_years.index(parent_profile.max_years_to_income)
    assert time_dim["student_step"] == expected_s_step
    assert time_dim["parent_step"] == expected_p_step


# ---------------------------------------------------------------------------
# 8. Domain Options, Canonical Order, and Guess Domain Handling
# ---------------------------------------------------------------------------
def test_domain_options_canonical_order_and_guesses():
    canonical_ids = [d.id for d in CANONICAL_DOMAINS]

    # Test case 1: normal guess
    code, s_tok, p_tok = create_linked_family()
    submit_student(
        code, s_tok,
        default_student_answers(pref_domain_wish=["design_creative", "tech_engineering"]),
    )
    submit_parent(
        code, p_tok,
        default_parent_answers(
            domain_wish=["sciences", "tech_engineering"],
            guess_domain="design_creative",
        ),
    )

    res = client.get(f"/families/{code}/mirror", headers={"X-Member-Token": s_tok})
    assert res.status_code == 200
    dim_map = {d["id"]: d for d in res.json()["dimensions"]}
    dom_dim = dim_map["domain"]

    # Options match CANONICAL_DOMAINS exactly in order
    assert [opt["id"] for opt in dom_dim["options"]] == canonical_ids
    for opt, expected in zip(dom_dim["options"], CANONICAL_DOMAINS):
        assert opt["label"]["en"] == expected.en
        assert opt["label"]["hi"] == expected.hi

    # Picks are strictly in canonical order
    assert dom_dim["student_picks"] == ["tech_engineering", "design_creative"]
    assert dom_dim["parent_picks"] == ["tech_engineering", "sciences"]
    assert dom_dim["parent_guess"] == "design_creative"

    # Test case 2: guess_domain is "not_sure" -> null
    code2, s_tok2, p_tok2 = create_linked_family()
    submit_student(code2, s_tok2)
    submit_parent(code2, p_tok2, default_parent_answers(guess_domain="not_sure"))

    res2 = client.get(f"/families/{code2}/mirror", headers={"X-Member-Token": s_tok2})
    assert res2.status_code == 200
    dom_dim2 = next(d for d in res2.json()["dimensions"] if d["id"] == "domain")
    assert dom_dim2["parent_guess"] is None

    # Test case 3: guess_domain omitted from stored answers -> null
    code3, s_tok3, p_tok3 = create_linked_family()
    submit_student(code3, s_tok3)
    submit_parent(code3, p_tok3)
    fam3 = family_store.get_family_for_preview(code3)
    assert fam3 is not None
    p_mem3 = fam3.get_member_by_role(RoleEnum.PARENT)
    assert p_mem3 is not None
    p_mem3.intake_answers.pop("guess_domain", None)

    res3 = client.get(f"/families/{code3}/mirror", headers={"X-Member-Token": s_tok3})
    assert res3.status_code == 200
    dom_dim3 = next(d for d in res3.json()["dimensions"] if d["id"] == "domain")
    assert dom_dim3["parent_guess"] is None


# ---------------------------------------------------------------------------
# 9. Privacy & Caplog: No Free-Text Leaking & No Answer Logging
# ---------------------------------------------------------------------------
def test_privacy_free_text_absent_and_no_logging(caplog):
    code, student_token, parent_token = create_linked_family()

    distinctive_student_secret = "DISTINCTIVE_STUDENT_ASPIRATION_SECRET_987654"
    distinctive_parent_secret = "DISTINCTIVE_PARENT_HOPE_SECRET_123456"

    s_ans = default_student_answers(free_text_1=distinctive_student_secret)
    p_ans = default_parent_answers(hope_text=distinctive_parent_secret)

    submit_student(code, student_token, s_ans)
    submit_parent(code, parent_token, p_ans)

    import logging
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        res = client.get(
            f"/families/{code}/mirror",
            headers={"X-Member-Token": student_token},
        )
        assert res.status_code == 200

        # Assert secret strings do not appear in response
        assert distinctive_student_secret not in res.text
        assert distinctive_parent_secret not in res.text

        # Assert no answer values or secret strings appear in any log record
        all_logs = caplog.text
        assert distinctive_student_secret not in all_logs
        assert distinctive_parent_secret not in all_logs
        assert "science_math" not in all_logs
        assert "under_5k" not in all_logs
        assert "6_12l" not in all_logs
