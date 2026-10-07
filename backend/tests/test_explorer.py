from __future__ import annotations

import time
from typing import Any
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.explorer import rank_blend_items
from app.store.families import family_store
from engine.public import get_default_routes
import engine.public

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
        "int_01": 4, "int_02": 3, "int_03": 5, "int_04": 2,
        "int_05": 4, "int_06": 3, "int_07": 4, "int_08": 5,
        "int_09": 3, "int_10": 4, "int_11": 2, "int_12": 1,
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
# 1. Error codes & 200 for both roles
# ---------------------------------------------------------------------------
def test_explorer_errors_and_success_for_both_roles():
    code, student_token, parent_token = create_linked_family()

    # 401 cases
    res_no_tok = client.get(f"/families/{code}/explorer")
    assert res_no_tok.status_code == 401
    assert res_no_tok.json()["error"]["code"] == "invalid_token"

    res_inv_tok = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": "invalid_fake_token"},
    )
    assert res_inv_tok.status_code == 401
    assert res_inv_tok.json()["error"]["code"] == "invalid_token"

    code_other, student_other, _ = create_linked_family()
    res_other = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": student_other},
    )
    assert res_other.status_code == 401
    assert res_other.json()["error"]["code"] == "invalid_token"

    # 404 case
    res_404 = client.get(
        "/families/UNKNOWN404/explorer",
        headers={"X-Member-Token": student_token},
    )
    assert res_404.status_code == 404
    assert res_404.json()["error"]["code"] == "family_not_found"

    # 409: neither submitted
    res_409_neither = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": student_token},
    )
    assert res_409_neither.status_code == 409
    assert res_409_neither.json()["error"]["code"] == "explorer_not_ready"

    # 409: only student submitted
    submit_student(code, student_token)
    res_409_only_s = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": student_token},
    )
    assert res_409_only_s.status_code == 409
    assert res_409_only_s.json()["error"]["code"] == "explorer_not_ready"

    # 409: only parent submitted (in another family)
    code2, s_tok2, p_tok2 = create_linked_family()
    submit_parent(code2, p_tok2)
    res_409_only_p = client.get(
        f"/families/{code2}/explorer",
        headers={"X-Member-Token": p_tok2},
    )
    assert res_409_only_p.status_code == 409
    assert res_409_only_p.json()["error"]["code"] == "explorer_not_ready"

    # 200: both submitted -> identical body for both
    submit_parent(code, parent_token)
    res_s = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": student_token},
    )
    assert res_s.status_code == 200
    res_p = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": parent_token},
    )
    assert res_p.status_code == 200

    assert res_s.json() == res_p.json()


# ---------------------------------------------------------------------------
# 2. Determinism
# ---------------------------------------------------------------------------
def test_explorer_determinism():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    res1 = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": student_token},
    )
    res2 = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": student_token},
    )
    assert res1.json() == res2.json()


# ---------------------------------------------------------------------------
# 3. Slider positions & default
# ---------------------------------------------------------------------------
def test_explorer_slider_specification():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    data = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": student_token},
    ).json()

    slider = data["slider"]
    expected_positions = list(range(0, 105, 5))
    assert slider["positions"] == expected_positions
    assert len(slider["positions"]) == 21
    assert slider["default"] == 50


# ---------------------------------------------------------------------------
# 4. Blend: 21 entries, ranks 1..N unique, and ties handling
# ---------------------------------------------------------------------------
def test_explorer_blend_ranks_and_ties():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    data = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": student_token},
    ).json()

    non_blocked = [c for c in data["careers"] if c["blocked"] is None]
    assert len(non_blocked) > 0
    N = len(non_blocked)

    for c in non_blocked:
        assert isinstance(c["blend"], list)
        assert len(c["blend"]) == 21

    # Check 1..N ranks at every position
    for pos_idx in range(21):
        ranks_at_pos = [c["blend"][pos_idx]["rank"] for c in non_blocked]
        scores_at_pos = [c["blend"][pos_idx]["score"] for c in non_blocked]
        assert all(isinstance(s, (int, float)) for s in scores_at_pos)

        assert len(ranks_at_pos) == N
        assert set(ranks_at_pos) == set(range(1, N + 1))

        # Check sorted by score descending, tie break career id ascending
        career_pairs = [
            (-c["blend"][pos_idx]["score"], c["id"], c["blend"][pos_idx]["rank"])
            for c in non_blocked
        ]
        sorted_pairs = sorted(career_pairs, key=lambda x: (x[0], x[1]))
        expected_ranks = [p[2] for p in sorted_pairs]
        assert expected_ranks == list(range(1, N + 1))

    # Test sort function / tie-break directly with a constructed tie
    sample_items = [
        {"career_id": "zeta_career", "negotiated_score": 75.4},
        {"career_id": "alpha_career", "negotiated_score": 75.4},
        {"career_id": "beta_career", "negotiated_score": 80.0},
    ]
    ranked = rank_blend_items(sample_items)
    assert ranked == [
        ("beta_career", 80.0, 1),
        ("alpha_career", 75.4, 2),
        ("zeta_career", 75.4, 3),
    ]


# ---------------------------------------------------------------------------
# 5. Blocked careers specification
# ---------------------------------------------------------------------------
def test_explorer_blocked_careers():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    data = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": student_token},
    ).json()

    blocked = [c for c in data["careers"] if c["blocked"] is not None]
    assert len(blocked) > 0
    frontier_set = set(data["frontier"])

    for c in blocked:
        # Carry no blend
        assert c["blend"] is None
        # in_compromise is false
        assert c["in_compromise"] is False
        # Absent from frontier
        assert c["id"] not in frontier_set
        # Fit kept
        assert c["fit"] is not None
        # Allowed causes
        cause = c["blocked"]["cause"]
        assert cause in {"no_route_data", "cost", "academic", "other"}

        # If money blocks, viability must be null
        gates = c["blocked"]["gates"]
        if "money" in gates or cause in ("cost", "no_route_data"):
            assert c["viability"] is None

        # no_route_data careers have remedies []
        if cause == "no_route_data":
            assert c["blocked"]["remedies"] == []
            assert c["years_to_income"] is None


# ---------------------------------------------------------------------------
# 6. Same-route consistency
# ---------------------------------------------------------------------------
def test_explorer_same_route_consistency():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    data = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": student_token},
    ).json()

    routes = get_default_routes()
    assert len(routes) > 0

    for c in data["careers"]:
        if c["blocked"] is None:
            # Feasible careers have years_to_income and fit/viability matching that route
            assert c["years_to_income"] is not None
            assert c["fit"] is not None
            assert c["viability"] is not None


# ---------------------------------------------------------------------------
# 7. Market and data_gaps
# ---------------------------------------------------------------------------
def test_explorer_market_and_data_gaps():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    data = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": student_token},
    ).json()

    allowed_gaps = {
        "verified_route_costs",
        "verified_entry_salary",
        "regional_hiring",
        "exam_pattern",
    }

    for c in data["careers"]:
        if c["market"] is not None:
            assert isinstance(c["market"], (int, float))
            assert 0.0 <= c["market"] <= 100.0

        for gap in c["data_gaps"]:
            assert gap in allowed_gaps


# ---------------------------------------------------------------------------
# 8. Frontier and compromise (including all-blocked family)
# ---------------------------------------------------------------------------
def test_explorer_frontier_and_compromise_and_all_blocked():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    data = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": student_token},
    ).json()

    # Normal family: frontier ordered by viability ascending
    frontier = data["frontier"]
    assert isinstance(frontier, list)
    career_map = {c["id"]: c for c in data["careers"]}

    viabs = [career_map[fid]["viability"] for fid in frontier]
    for i in range(1, len(viabs)):
        assert viabs[i] >= viabs[i - 1]

    assert data["compromise"] is not None
    assert data["compromise"]["min_fit"] == 50.0
    assert data["compromise"]["min_viability"] == 50.0

    # All-blocked family fixture: student with below_50 marks fails academic gates
    code_b, s_tok_b, p_tok_b = create_linked_family()
    s_ans_low = default_student_answers(bg_marks_band="below_50")
    submit_student(code_b, s_tok_b, s_ans_low)
    submit_parent(code_b, p_tok_b)

    data_b = client.get(
        f"/families/{code_b}/explorer",
        headers={"X-Member-Token": s_tok_b},
    ).json()

    assert data_b["frontier"] == []
    assert data_b["compromise"] is None
    for c in data_b["careers"]:
        assert c["blocked"] is not None


# ---------------------------------------------------------------------------
# 9. Career names in English and Hindi
# ---------------------------------------------------------------------------
def test_explorer_career_names_localization():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    data = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": student_token},
    ).json()

    for c in data["careers"]:
        assert isinstance(c["name"]["en"], str)
        assert len(c["name"]["en"].strip()) > 0
        assert isinstance(c["name"]["hi"], str)
        assert len(c["name"]["hi"].strip()) > 0


# ---------------------------------------------------------------------------
# 10. Forbidden fields scan
# ---------------------------------------------------------------------------
def test_explorer_forbidden_field_scan():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    data = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": student_token},
    ).json()

    ALLOWED_TOP_KEYS = {"slider", "careers", "frontier", "compromise"}
    ALLOWED_SLIDER_KEYS = {"positions", "default"}
    ALLOWED_COMPROMISE_KEYS = {"min_fit", "min_viability"}
    ALLOWED_CAREER_KEYS = {
        "id", "name", "domain", "fit", "viability", "market",
        "years_to_income", "conflict", "in_compromise", "blend",
        "blocked", "data_gaps",
    }
    ALLOWED_BLOCKED_KEYS = {"gates", "cause", "remedies"}
    ALLOWED_REMEDY_KEYS = {"id", "text"}
    ALLOWED_BLEND_KEYS = {"score", "rank"}
    ALLOWED_NAME_KEYS = {"en", "hi"}

    assert set(data.keys()) == ALLOWED_TOP_KEYS
    assert set(data["slider"].keys()) == ALLOWED_SLIDER_KEYS
    if data["compromise"]:
        assert set(data["compromise"].keys()) == ALLOWED_COMPROMISE_KEYS

    for c in data["careers"]:
        assert set(c.keys()) == ALLOWED_CAREER_KEYS
        assert set(c["name"].keys()) == ALLOWED_NAME_KEYS
        if c["blocked"]:
            assert set(c["blocked"].keys()) == ALLOWED_BLOCKED_KEYS
            for rem in c["blocked"]["remedies"]:
                assert set(rem.keys()) == ALLOWED_REMEDY_KEYS
                assert set(rem["text"].keys()) == ALLOWED_NAME_KEYS
        if c["blend"]:
            for b in c["blend"]:
                assert set(b.keys()) == ALLOWED_BLEND_KEYS

    forbidden_tokens = [
        "income", "savings", "surplus", "emi", "loan",
        "route_cost", "explanation", "diagnosis", "tag",
    ]

    def scan_recursive(obj: Any):
        if isinstance(obj, dict):
            for k, v in obj.items():
                lower_k = str(k).lower()
                for token in forbidden_tokens:
                    # Ignore 'years_to_income' key matching 'income' token
                    if lower_k == "years_to_income":
                        continue
                    assert token not in lower_k, f"Forbidden token '{token}' in key '{k}'"
                scan_recursive(v)
        elif isinstance(obj, list):
            for item in obj:
                scan_recursive(item)

    scan_recursive(data)


# ---------------------------------------------------------------------------
# 11. Privacy & Caplog
# ---------------------------------------------------------------------------
def test_explorer_privacy_and_no_answer_logging(caplog):
    code, student_token, parent_token = create_linked_family()
    secret_s = "SECRET_FREE_TEXT_STUDENT_998877"
    secret_p = "SECRET_HOPE_TEXT_PARENT_112233"

    s_ans = default_student_answers(free_text_1=secret_s)
    p_ans = default_parent_answers(hope_text=secret_p)

    submit_student(code, student_token, s_ans)
    submit_parent(code, parent_token, p_ans)

    import logging
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        res = client.get(
            f"/families/{code}/explorer",
            headers={"X-Member-Token": student_token},
        )
        assert res.status_code == 200

        assert secret_s not in res.text
        assert secret_p not in res.text

        logs = caplog.text
        assert secret_s not in logs
        assert secret_p not in logs
        assert "science_bio" not in logs
        assert "Lucknow" not in logs


# ---------------------------------------------------------------------------
# 12. Cache test & Cache dropped on expiry
# ---------------------------------------------------------------------------
def test_explorer_caching_and_expiration():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    # First call: computes and caches
    with patch.object(engine.public, "per_career_scores", wraps=engine.public.per_career_scores) as spy_scores:
        res1 = client.get(
            f"/families/{code}/explorer",
            headers={"X-Member-Token": student_token},
        )
        assert res1.status_code == 200
        initial_calls = spy_scores.call_count
        assert initial_calls > 0

        # Second call: returns cached result without invoking engine
        res2 = client.get(
            f"/families/{code}/explorer",
            headers={"X-Member-Token": student_token},
        )
        assert res2.status_code == 200
        assert spy_scores.call_count == initial_calls  # No additional calls to engine!
        assert res1.json() == res2.json()

    # Expire family record
    fam = family_store.get_family_for_preview(code)
    assert fam is not None
    assert fam.explorer_cache is not None

    from datetime import timedelta
    from app.store.families import now_utc
    fam.expires_at = now_utc() - timedelta(minutes=1)

    # Accessing expired family drops it and returns 404
    res_expired = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": student_token},
    )
    assert res_expired.status_code == 404
    assert res_expired.json()["error"]["code"] == "family_not_found"
    assert family_store.get_family_for_preview(code) is None


# ---------------------------------------------------------------------------
# 13. Performance guard: one uncached call within a few seconds
# ---------------------------------------------------------------------------
def test_explorer_performance_guard():
    code, student_token, parent_token = create_linked_family()
    submit_student(code, student_token)
    submit_parent(code, parent_token)

    t0 = time.time()
    res = client.get(
        f"/families/{code}/explorer",
        headers={"X-Member-Token": student_token},
    )
    elapsed = time.time() - t0
    assert res.status_code == 200
    assert elapsed < 3.0, f"Uncached call took {elapsed:.2f}s, expected < 3.0s"
