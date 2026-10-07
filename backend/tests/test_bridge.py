"""Tests for PRISM Engine Bridge and cross-bank parity requirements."""

from engine.parent.models import ParentProfile
from engine.student_fit.models import Student
from engine.domains import CANONICAL_DOMAINS

from app.assessment.bank import (
    ALL_QUESTIONS_MAP as ALL_STUDENT_MAP,
    SECTIONS_ORDER as STUDENT_SECTIONS,
)
from app.intake.bank import (
    ALL_INTAKE_QUESTIONS_MAP as ALL_PARENT_MAP,
    SECTIONS_ORDER as PARENT_SECTIONS,
)
from app.engine_bridge import build_engine_profiles
from app.schemas.families import RoleEnum
from app.store.families import FamilyRecord, MemberRecord, now_utc


def test_bank_cross_integrity_and_shared_definitions():
    # 1. Total counts
    assert len(ALL_STUDENT_MAP) == 32
    assert len(ALL_PARENT_MAP) == 16

    # 2. Section order
    student_section_ids = [s.id for s in STUDENT_SECTIONS]
    assert student_section_ids == [
        "background", "interests", "aptitude", "values", "preferences", "free_text"
    ]
    parent_section_ids = [s.id for s in PARENT_SECTIONS]
    assert parent_section_ids == ["money", "risk", "plans", "hopes", "perception"]

    # 3. Unique IDs
    assert len(ALL_STUDENT_MAP) == len(set(ALL_STUDENT_MAP.keys()))
    assert len(ALL_PARENT_MAP) == len(set(ALL_PARENT_MAP.keys()))

    # 4. Bilingual non-empty strings
    for q in ALL_STUDENT_MAP.values():
        assert q.prompt_en.strip()
        assert q.prompt_hi.strip()
        for opt in q.options:
            assert opt.label_en.strip()
            assert opt.label_hi.strip()

    for q in ALL_PARENT_MAP.values():
        assert q.prompt_en.strip()
        assert q.prompt_hi.strip()
        for opt in q.options:
            assert opt.label_en.strip()
            assert opt.label_hi.strip()

    # 5. Risk tasks: pref_risk_1..3 identical in amounts, option ids, and wording to risk_1..3
    for s_id, p_id in [("pref_risk_1", "risk_1"), ("pref_risk_2", "risk_2"), ("pref_risk_3", "risk_3")]:
        s_q = ALL_STUDENT_MAP[s_id]
        p_q = ALL_PARENT_MAP[p_id]
        assert s_q.tag == "risk"
        assert p_q.tag == "risk"
        assert len(s_q.options) == len(p_q.options) == 2
        for s_opt, p_opt in zip(s_q.options, p_q.options):
            assert s_opt.id == p_opt.id
            assert s_opt.label_en == p_opt.label_en
            assert s_opt.label_hi == p_opt.label_hi

    # 6. Relocation options identical across both banks
    s_reloc = ALL_STUDENT_MAP["pref_relocation"]
    p_reloc = ALL_PARENT_MAP["relocation"]
    assert s_reloc.tag == "relocation"
    assert p_reloc.tag == "relocation"
    assert len(s_reloc.options) == len(p_reloc.options) == 4
    for s_opt, p_opt in zip(s_reloc.options, p_reloc.options):
        assert s_opt.id == p_opt.id
        assert s_opt.label_en == p_opt.label_en
        assert s_opt.label_hi == p_opt.label_hi

    # 7. Time-to-earn options identical across both banks
    s_time = ALL_STUDENT_MAP["pref_time_to_earn"]
    p_time = ALL_PARENT_MAP["time_to_earn"]
    assert s_time.tag == "time_to_earn"
    assert p_time.tag == "time_to_earn"
    assert len(s_time.options) == len(p_time.options) == 3
    for s_opt, p_opt in zip(s_time.options, p_time.options):
        assert s_opt.id == p_opt.id
        assert s_opt.label_en == p_opt.label_en
        assert s_opt.label_hi == p_opt.label_hi

    # 8. Domain options equal engine/domains.py
    canonical_ids = [d.id for d in CANONICAL_DOMAINS]
    s_dom = ALL_STUDENT_MAP["pref_domain_wish"]
    p_dom = ALL_PARENT_MAP["domain_wish"]
    assert [opt.id for opt in s_dom.options] == canonical_ids
    assert [opt.id for opt in p_dom.options] == canonical_ids
    assert s_dom.max_select == 3
    assert p_dom.max_select == 3
    assert s_dom.tag == "domain_wish"
    assert p_dom.tag == "domain_wish"


def test_bridge_with_realistic_answers():
    # Build realistic student answers
    student_answers = {
        "bg_stream": "science_maths",
        "bg_marks_band": "75_90",
        "bg_district": "Jaipur, Rajasthan",
        "bg_languages": ["hindi", "english"],
        "int_01": 5,
        "int_02": 4,
        "int_03": 2,
        "int_04": 3,
        "int_05": 4,
        "int_06": 3,
        "int_07": 4,
        "int_08": 5,
        "int_09": 2,
        "int_10": 3,
        "int_11": 4,
        "int_12": 2,
        "apt_spatial": "a",
        "apt_numerical": "b",
        "apt_verbal": "c",
        "apt_logical": "d",
        "val_security": 8,
        "val_independence": 7,
        "val_helping": 6,
        "val_income": 9,
        "val_creativity": 8,
        "pref_risk_1": "gamble",
        "pref_risk_2": "gamble",
        "pref_risk_3": "safe",
        "pref_relocation": "anywhere_india",
        "pref_time_to_earn": "five_six",
        "pref_domain_wish": ["tech_engineering", "sciences"],
        "free_text_1": "Passionate about robotics and space science.",
    }

    # Build realistic parent answers
    parent_answers = {
        "income_band": "6_12l",
        "savings_band": "3_8l",
        "loan_band": "3_8l",
        "surplus_band": "15k_30k",
        "emi_band": "under_5k",
        "risk_1": "safe",
        "risk_2": "safe",
        "risk_3": "safe",
        "relocation": "same_state",
        "time_to_earn": "within_4y",
        "domain_wish": ["tech_engineering", "business_management"],
        "guess_domain": "tech_engineering",
        "guess_relocation": "same_state",
        "guess_risk": "medium",
        "non_negotiables": ["job_security"],
        "hope_text": "We hope our child gets a stable and respected career.",
    }

    # Create dummy FamilyRecord
    student_member = MemberRecord(
        token="tok_student_123",
        role=RoleEnum.STUDENT,
        name="Aarav",
        lang="en",
        joined_at=now_utc(),
        answers=dict(student_answers),
        submitted=True,
    )
    parent_member = MemberRecord(
        token="tok_parent_456",
        role=RoleEnum.PARENT,
        name="Sunita",
        lang="hi",
        joined_at=now_utc(),
        intake_answers=dict(parent_answers),
        intake_submitted=True,
    )
    family = FamilyRecord(
        family_code="F12345",
        created_at=now_utc(),
        expires_at=now_utc(),
        members=[student_member, parent_member],
    )

    # Call bridge with FamilyRecord
    student_model, parent_model = build_engine_profiles(family)

    # 1. Returned types are engine models
    assert isinstance(student_model, Student)
    assert isinstance(parent_model, ParentProfile)

    # 2. Check student dimensions populated
    # Risk: 2 gambles out of 3 = 0.67
    assert student_model.risk_appetite == 0.67
    # Relocation: anywhere_india = 0.67
    assert student_model.relocation_willingness == 0.67
    # Time to income: five_six = 6.0
    assert student_model.max_years_to_income == 6.0
    # RIASEC interest scores in [0, 1]
    assert set(student_model.I_s.keys()) == {"R", "I", "A", "S", "E", "C"}
    for v in student_model.I_s.values():
        assert 0.0 <= v <= 1.0
    # Aptitude all correct -> all 1.0
    assert student_model.a_j == {"numerical": 1.0, "verbal": 1.0, "spatial": 1.0, "logical": 1.0}
    # Domain ratings: picked domains = 5.0, unpicked = 1.0
    assert student_model.domain_preference["tech_engineering"] == 5.0
    assert student_model.domain_preference["sciences"] == 5.0
    assert student_model.domain_preference["business_management"] == 1.0

    # 3. Check parent dimensions populated
    # Balance sheet: 6-12L -> 900,000 / 12 = 75,000 monthly
    assert parent_model.household_income == 75000.0
    # Savings: 3-8L midpoint = 550,000
    assert parent_model.savings == 550000.0
    # Loan capacity: 3-8L midpoint = 550,000
    assert parent_model.loan_max == 550000.0
    # Surplus: 15k-30k midpoint = 22,500
    assert parent_model.monthly_surplus == 22500.0
    # EMI: under_5k midpoint = 2,500
    assert parent_model.existing_emis == 2500.0
    # Risk: 0 gambles = 0.0
    assert parent_model.risk == 0.0
    # Relocation: same_state = 0.33
    assert parent_model.relocation_willingness == 0.33
    # Time to income: within_4y = 4.0
    assert parent_model.max_years_to_income == 4.0
    # Domain ratings: tech_engineering = 5.0, business_management = 5.0, sciences = 1.0
    assert parent_model.domain_ratings["tech_engineering"] == 5.0
    assert parent_model.domain_ratings["business_management"] == 5.0
    assert parent_model.domain_ratings["sciences"] == 1.0

    # 4. Verify family record was not mutated
    assert student_member.answers == student_answers
    assert parent_member.intake_answers == parent_answers

    # 5. Also verify calling with direct dicts works identically
    s2, p2 = build_engine_profiles(student_answers, parent_answers)
    assert s2.risk_appetite == student_model.risk_appetite
    assert p2.household_income == parent_model.household_income
